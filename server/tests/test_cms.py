from io import BytesIO, StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import os
import subprocess
import sqlite3
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from PIL import Image
from cms.forms import ArticleForm
from cms.models import Article, SiteSettings
from cms.publishing import publish_article, unpublish_article, publish_settings, change_and_build, PublicationError
from scripts.article_content import render_markdown


class CMSTests(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.data = Path(self.temp.name)
        self.overrides = override_settings(DATA_DIR=self.data, MEDIA_ROOT=self.data / 'media', CMS_PUBLIC_ROOT=self.data / 'public', SECURE_SSL_REDIRECT=False, ALLOWED_HOSTS=['testserver'])
        self.overrides.enable()
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(self.overrides.disable)
        self.user = get_user_model().objects.create_superuser('test-editor', password='local-test-password-only')
        self.article = Article.objects.create(title='Подготовка трубопровода', slug='test-pipeline', category='Монтаж трубопроводов', summary='Описание работ перед монтажом.', body='## Осмотр\n\nСначала уточните задачу.', cover='assets/client/pipeline-installation.jpg', cover_alt='Трубопровод')

    def public_text(self, path):
        return (self.data / 'public' / path).read_text()

    def test_server_origin_is_used_for_all_search_metadata(self):
        output = self.data / 'new-domain'
        environment = {**os.environ, 'PUBLIC_SITE_URL': 'https://new-example.ru', 'PUBLIC_SITE_NOINDEX': '1'}
        subprocess.run([__import__('sys').executable, str(settings.SITE_ROOT / 'scripts/build_site.py'), '--output-dir', str(output)], env=environment, capture_output=True, text=True, check=True)
        home = (output / 'index.html').read_text()
        article = (output / 'articles/podgotovka-k-montazhu-truboprovoda.html').read_text()
        self.assertIn('href="https://new-example.ru/index.html"', home)
        self.assertIn('content="noindex,nofollow"', home)
        self.assertNotIn('https://stroy-ekb.ru', article)
        self.assertIn('https://new-example.ru/', (output / 'sitemap.xml').read_text())
        self.assertIn('https://new-example.ru/sitemap.xml', (output / 'robots.txt').read_text())

    def form_data(self):
        a = self.article
        return {name: getattr(a, name) for name in ('title', 'slug', 'category', 'summary', 'body', 'cover', 'cover_alt', 'seo_title', 'seo_description', 'service')}

    def test_draft_publish_edit_and_unpublish(self):
        change_and_build()
        self.assertFalse((self.data / 'public/articles/test-pipeline.html').exists())
        publish_article(self.article.pk)
        self.article.refresh_from_db()
        self.assertIn('Сначала уточните задачу.', self.public_text('articles/test-pipeline.html'))
        self.assertIn('test-pipeline.html', self.public_text('sitemap.xml'))
        self.article.body = 'Сохранённый новый черновик.'
        self.article.save()
        change_and_build()
        self.assertNotIn('новый черновик', self.public_text('articles/test-pipeline.html'))
        publish_article(self.article.pk)
        self.assertIn('новый черновик', self.public_text('articles/test-pipeline.html'))
        unpublish_article(self.article.pk)
        self.assertFalse((self.data / 'public/articles/test-pipeline.html').exists())
        self.assertNotIn('test-pipeline.html', self.public_text('sitemap.xml'))
        self.assertTrue(Article.objects.filter(pk=self.article.pk).exists())

    def test_failed_build_preserves_live_site_and_snapshot(self):
        publish_article(self.article.pk)
        self.article.refresh_from_db()
        old_target = (self.data / 'public').resolve()
        self.article.body = 'Непубликуемое изменение.'
        self.article.save()
        with patch('cms.publishing.subprocess.run', return_value=subprocess.CompletedProcess([], 1, '', 'test failure')):
            with self.assertRaises(PublicationError):
                publish_article(self.article.pk)
        self.assertEqual((self.data / 'public').resolve(), old_target)
        self.article.refresh_from_db()
        self.assertNotIn('Непубликуемое', self.article.published_payload['body'])
        self.assertIn('Непубликуемое', self.article.body)

    def test_access_csrf_and_private_files(self):
        for path in ('/admin/', f'/cms-preview/{self.article.pk}/', f'/admin/article-cover/{self.article.pk}/'):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/admin/login/', response.url)
        self.assertEqual(Client(enforce_csrf_checks=True).post('/admin/login/', {'username': 'x', 'password': 'x'}).status_code, 403)
        change_and_build()
        for path in ('/server/manage.py', '/content/articles.json', '/.env', '/.local/cms-data/cms.sqlite3', '/private-media/articles/test.webp'):
            self.assertEqual(self.client.get(path).status_code, 404, path)
        self.client.force_login(self.user)
        preview = self.client.get(f'/cms-preview/{self.article.pk}/')
        self.assertEqual(preview.status_code, 200)
        self.assertIn('noindex', preview['X-Robots-Tag'])
        self.assertIn('no-store', preview['Cache-Control'])
        self.assertContains(preview, 'Предпросмотр сохранённой версии')

    def test_admin_save_and_publish_buttons(self):
        self.client.force_login(self.user)
        url = f'/admin/cms/article/{self.article.pk}/change/'
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url, {**self.form_data(), '_continue': '1'})
        self.assertEqual(response.status_code, 302)
        self.article.refresh_from_db()
        self.assertIsNone(self.article.published_payload)
        self.assertContains(self.client.get('/admin/cms/article/?published=no'), self.article.title)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url, {**self.form_data(), '_publish': '1'})
        self.assertEqual(response.status_code, 302)
        self.article.refresh_from_db()
        self.assertIsNotNone(self.article.published_payload)
        self.assertTrue((self.data / 'public/articles/test-pipeline.html').exists())

    def test_safe_markdown(self):
        rendered, _ = render_markdown('<script>alert(1)</script>\n\n[x](javascript:alert(1))\n\n![x](https://tracker.invalid/image.png)')
        self.assertNotIn('<script>', rendered)
        self.assertNotIn('href="javascript:', rendered)
        self.assertNotIn('<img', rendered)

    def test_upload_validation_and_publication(self):
        invalid = SimpleUploadedFile('bad.svg', b'<svg onload="alert(1)"/>', content_type='image/svg+xml')
        self.assertFalse(ArticleForm(data=self.form_data(), files={'cover_upload': invalid}, instance=self.article).is_valid())
        image = BytesIO()
        Image.new('RGB', (40, 30), 'blue').save(image, 'PNG')
        upload = SimpleUploadedFile('cover.png', image.getvalue(), content_type='image/png')
        form = ArticleForm(data=self.form_data(), files={'cover_upload': upload}, instance=self.article)
        self.assertTrue(form.is_valid(), form.errors)
        saved = form.save()
        with Image.open(saved.cover_upload.path) as result:
            self.assertEqual(result.format, 'WEBP')
        public_name = Path(saved.cover_upload.name).name
        change_and_build()
        self.assertFalse((self.data / 'public/assets/uploads' / public_name).exists())
        self.client.force_login(self.user)
        self.assertContains(self.client.get(f'/cms-preview/{saved.pk}/'), f'src="/admin/article-cover/{saved.pk}/"')
        publish_article(saved.pk)
        self.assertTrue((self.data / 'public/assets/uploads' / public_name).exists())
        self.assertIn(public_name, self.public_text('articles/test-pipeline.html'))

    def test_slug_is_stable_after_publication(self):
        publish_article(self.article.pk)
        self.article.refresh_from_db()
        self.article.slug = 'another-address'
        with self.assertRaises(ValidationError):
            self.article.full_clean()

    def test_profile_rebuilds_shared_contacts(self):
        profile = SiteSettings.objects.create(company_name='СК Проверка', phone='+7 (999) 123-45-67', hero_description='Новый текст первого экрана.')
        publish_settings(profile.pk)
        home = self.public_text('index.html')
        self.assertIn('Новый текст первого экрана.', home)
        self.assertIn('tel:+79991234567', home)
        self.assertNotIn('tel:+79024453001', home)
        self.assertIn('СК ПРОВЕРКА', self.public_text('services.html'))
        self.assertFalse((self.data / 'public/server').exists())
        self.assertFalse((self.data / 'public/content').exists())

    def test_seed_does_not_overwrite_editor_changes(self):
        call_command('seed_content', stdout=StringIO())
        first = Article.objects.exclude(pk=self.article.pk).first()
        first.body = 'Редакторская правка'
        first.save()
        count = Article.objects.count()
        call_command('seed_content', stdout=StringIO())
        self.assertEqual(Article.objects.count(), count)
        first.refresh_from_db()
        self.assertEqual(first.body, 'Редакторская правка')

    def test_private_backup_keeps_drafts_and_media(self):
        photo = self.data / 'media/articles/photo.webp'
        photo.parent.mkdir(parents=True)
        photo.write_bytes(b'private test fixture')
        target = self.data / 'backup'
        source = self.data / 'fixture.sqlite3'
        with sqlite3.connect(source) as db:
            db.execute('CREATE TABLE content (body TEXT)')
            db.execute('INSERT INTO content VALUES (?)', ('private draft',))
        with patch.dict(settings.DATABASES['default'], {'NAME': source}):
            call_command('backup_cms', output=str(target), stdout=StringIO())
        self.assertTrue((target / 'cms.sqlite3').is_file())
        with sqlite3.connect(target / 'cms.sqlite3') as db:
            self.assertEqual(db.execute('SELECT body FROM content').fetchone()[0], 'private draft')
        self.assertEqual((target / 'media/articles/photo.webp').read_bytes(), b'private test fixture')

    def test_client_enters_only_article_content(self):
        data = {'title': 'Монтаж труб в помещении', 'body': 'Текст статьи без технических настроек.', 'cover': 'assets/client/pipeline-installation.jpg'}
        form = ArticleForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)
        first = form.save()
        self.assertEqual(first.slug, 'montazh-trub-v-pomeschenii')
        self.assertEqual(first.cover_alt, data['title'])
        self.assertEqual(first.seo_title, '')
        self.assertEqual(first.summary, data['body'])
        duplicate = ArticleForm(data=data)
        self.assertTrue(duplicate.is_valid(), duplicate.errors)
        self.assertEqual(duplicate.save().slug, first.slug + '-2')
        self.client.force_login(self.user)
        response = self.client.get('/admin/cms/article/add/')
        self.assertNotContains(response, 'name="slug"')
        self.assertContains(response, 'Дополнительно — вид в поиске')
        self.assertNotContains(response, 'name="category"')
        self.assertNotContains(response, 'name="cover_alt"')
