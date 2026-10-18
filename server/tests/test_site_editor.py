from io import BytesIO, StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import subprocess
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from PIL import Image
from cms.models import Article, SiteSettings, SitePage, PageSection, Service, Project, ProjectPhoto
from cms.forms import ArticleForm, ServiceForm, ProjectForm, PhotoForm, SectionForm
from cms.publishing import publish_content, unpublish_content, change_and_build, PublicationError


class SiteEditorTests(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.data = Path(self.temp.name)
        override = override_settings(DATA_DIR=self.data, MEDIA_ROOT=self.data/'media', CMS_PUBLIC_ROOT=self.data/'public', SECURE_SSL_REDIRECT=False, ALLOWED_HOSTS=['testserver'])
        override.enable()
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(override.disable)

    def seed(self):
        call_command('seed_content', stdout=StringIO())

    def text(self, route):
        return (self.data/'public'/route).read_text()

    def test_upgrade_keeps_live_and_draft_versions_and_does_not_restore_deleted_content(self):
        SiteSettings.objects.create(company_name='СК Орион & Партнёры', phone='+7 (999) 123-45-67', hero_description='Черновик первого экрана', published_payload={'company_name':'СК Орион & Партнёры','phone':'+7 (999) 123-45-67','hero_description':'Опубликованный первый экран'})
        self.seed()
        home = SitePage.objects.get(route='index.html')
        self.assertEqual(home.intro, 'Черновик первого экрана')
        self.assertEqual(home.published_payload['intro'], 'Опубликованный первый экран')
        self.assertIn('Опубликованный первый экран', self.text('index.html'))
        self.assertNotIn('Черновик первого экрана', self.text('index.html'))
        self.assertIn('СК Орион &amp; Партнёры', self.text('about.html'))
        self.assertNotIn('&amp;amp;', self.text('about.html'))
        home.sections.first().delete()
        Article.objects.first().delete()
        Project.objects.first().delete()
        Service.objects.first().delete()
        counts = (Article.objects.count(), Project.objects.count(), Service.objects.count(), PageSection.objects.count())
        self.seed()
        self.assertEqual(counts, (Article.objects.count(), Project.objects.count(), Service.objects.count(), PageSection.objects.count()))
        home.refresh_from_db()
        self.assertEqual(home.intro, 'Черновик первого экрана')

    def test_page_and_service_drafts_and_order_stay_private_until_their_own_publication(self):
        self.seed()
        home = SitePage.objects.get(route='index.html')
        home.intro = 'Новый частный текст'
        home.save()
        block = home.sections.get(key='intro')
        block.body = 'Только в черновике'
        block.save()
        first, second = list(Service.objects.all())[:2]
        first.position = 999
        first.title = 'Черновое название услуги'
        first.save()
        second.title = 'Опубликованная услуга'
        second.save()
        publish_content(Service, second.pk)
        self.assertNotIn('Новый частный текст', self.text('index.html'))
        self.assertNotIn('Только в черновике', self.text('index.html'))
        services = self.text('services.html')
        self.assertNotIn('Черновое название услуги', services)
        self.assertLess(services.index(first.published_payload['title']), services.index('Опубликованная услуга'))
        home.seo_title = 'Главная — ручной поиск'
        home.save()
        publish_content(SitePage, home.pk)
        self.assertIn('Новый частный текст', self.text('index.html'))
        self.assertIn('Только в черновике', self.text('index.html'))
        self.assertIn('Главная — ручной поиск', self.text('index.html'))
        self.assertNotIn('Черновое название услуги', self.text('index.html'))

    def test_gallery_upload_preview_publication_and_hiding(self):
        self.seed()
        form = ProjectForm(data={'title':'Работа на объекте','summary':'Кратко о работе','description':'Описание **работы** без кода.','details':'Сборка\nМонтаж','category':'inside','position':10})
        self.assertTrue(form.is_valid(), form.errors)
        project = form.save()
        stable_slug = project.slug
        with self.assertRaises(PublicationError):
            publish_content(Project, project.pk)
        invalid = PhotoForm(data={'caption':'','position':1}, files={'image_upload':SimpleUploadedFile('bad.svg',b'<svg/>',content_type='image/svg+xml')}, instance=ProjectPhoto(project=project))
        self.assertFalse(invalid.is_valid())
        data = BytesIO()
        Image.new('RGB',(2200,1000),'blue').save(data,'PNG')
        photo_form = PhotoForm(data={'caption':'Монтаж оборудования','position':1}, files={'image_upload':SimpleUploadedFile('photo.png',data.getvalue(),content_type='image/png')}, instance=ProjectPhoto(project=project))
        self.assertTrue(photo_form.is_valid(),photo_form.errors)
        photo = photo_form.save()
        with Image.open(photo.image_upload.path) as actual:
            self.assertEqual(actual.format,'WEBP')
            self.assertEqual(actual.width,1800)
        upload_name = Path(photo.image_upload.name).name
        change_and_build()
        self.assertFalse((self.data/'public'/'assets/uploads'/upload_name).exists())
        preview_url=f'/cms-preview/project/{project.pk}/'
        self.assertEqual(self.client.get(preview_url).status_code,302)
        editor = get_user_model().objects.create_user('client',password='test-pass-local-only',is_staff=True)
        editor.groups.add(Group.objects.get(name='Редакторы'))
        self.client.force_login(editor)
        preview = self.client.get(preview_url)
        self.assertContains(preview,'Предпросмотр сохранённой версии')
        self.assertContains(preview,'/admin/content-upload/'+upload_name)
        self.assertEqual(self.client.get('/admin/content-upload/'+upload_name).status_code,200)
        self.assertFalse((self.data/'public'/'assets/uploads'/upload_name).exists())
        publish_content(Project, project.pk)
        self.assertIn('<strong>работы</strong>',self.text('works/'+stable_slug+'.html'))
        self.assertTrue((self.data/'public'/'assets/uploads'/upload_name).exists())
        project.refresh_from_db()
        project.title = 'Другое название'
        project.save()
        publish_content(Project,project.pk)
        self.assertEqual(project.slug,stable_slug)
        self.assertIn(stable_slug+'.html',self.text('sitemap.xml'))
        unpublish_content(Project,project.pk)
        self.assertFalse((self.data/'public/works'/(stable_slug+'.html')).exists())
        self.assertNotIn(stable_slug+'.html',self.text('sitemap.xml'))

    def test_editor_navigation_permissions_and_failed_publication(self):
        self.seed()
        editor = get_user_model().objects.create_user('editor',password='test-pass-local-only',is_staff=True)
        editor.groups.add(Group.objects.get(name='Редакторы'))
        self.client.force_login(editor)
        for kind in ('sitepage','service','project','article','sitesettings'):
            self.assertContains(self.client.get('/admin/'),'/admin/cms/'+kind+'/')
            self.assertEqual(self.client.get('/admin/cms/'+kind+'/').status_code,302 if kind=='sitesettings' else 200)
        self.assertEqual(self.client.get('/admin/auth/user/').status_code,403)
        page=SitePage.objects.get(route='about.html')
        response=self.client.get(f'/admin/cms/sitepage/{page.pk}/change/')
        self.assertEqual(response.status_code,200)
        for field in ('route','key','published_payload','slug'):
            self.assertNotContains(response,'name="'+field+'"')
        self.assertContains(response,'Дополнительно — вид в поиске')
        with self.captureOnCommitCallbacks(execute=True):
            created = self.client.post('/admin/cms/service/add/', {'title':'Новое направление','summary':'Краткое описание','intro':'Описание услуги','scope':'Первая задача\nВторая задача','prepare':'Подготовьте фотографии','position':20,'_publish':'1'})
        self.assertEqual(created.status_code,302)
        new_service = Service.objects.get(title='Новое направление')
        self.assertEqual(new_service.slug,'novoe-napravlenie')
        self.assertTrue((self.data/'public/services/novoe-napravlenie.html').is_file())
        old = (self.data/'public').resolve()
        page.title='Неудачная публикация'
        page.save()
        with patch('cms.publishing.subprocess.run',return_value=subprocess.CompletedProcess([],1,'','failure')):
            with self.assertRaises(PublicationError):
                publish_content(SitePage,page.pk)
        page.refresh_from_db()
        self.assertNotEqual(page.published_payload['title'],page.title)
        self.assertEqual((self.data/'public').resolve(),old)
        with self.assertRaises(PublicationError):
            unpublish_content(SitePage,page.pk)

    def test_fresh_seed_statuses_and_editor_space_normalization(self):
        from django.contrib import admin
        self.seed()
        for model in (SitePage, Service, Project):
            for item in model.objects.all():
                self.assertEqual(admin.site._registry[model].publication_status(item), 'Опубликовано', str(item))
        section = PageSection.objects.filter(key='intro').first()
        form = SectionForm(data={'title':'Заголовок', 'body':'Слова\u00a0должны\u00a0переноситься.'},instance=section)
        self.assertTrue(form.is_valid(),form.errors)
        self.assertEqual(form.save().body, 'Слова должны переноситься.')
        article = ArticleForm(data={'title':'Новая статья','body':'Слова\u00a0в\u00a0статье.','cover':'assets/client/pipeline-installation.jpg'})
        self.assertTrue(article.is_valid(),article.errors)
        self.assertEqual(article.save().body, 'Слова в статье.')


    def test_deleting_every_work_and_service_keeps_empty_collections_after_restart(self):
        from cms.publishing import published_collection
        self.seed()
        Project.objects.all().delete()
        Service.objects.all().delete()
        self.seed()
        self.assertEqual(Project.objects.count(), 0)
        self.assertEqual(Service.objects.count(), 0)
        self.assertEqual(published_collection(Project, 'projects.json'), [])
        self.assertEqual(published_collection(Service, 'services.json'), [])
        self.assertNotIn('works/naruzhnye-seti.html', self.text('works.html'))
        self.assertNotIn('services/pipeline-installation.html', self.text('services.html'))
        self.assertFalse((self.data/'public/works/naruzhnye-seti.html').exists())
        self.assertFalse((self.data/'public/services/pipeline-installation.html').exists())
        self.assertNotIn('services/emergency.html', self.text('index.html'))
