from datetime import datetime, time, timezone as dt_timezone
import json
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.conf import settings
from django.db import transaction
from scripts.article_content import load_articles
from cms.models import Article, SiteSettings, SitePage, PageSection, Service, Project, ProjectPhoto, ContentImport
from cms.publishing import change_and_build


class Command(BaseCommand):
    help = 'Import initial website content once without replacing editor changes or deleted entries, then build public pages.'
    def handle(self, *args, **options):
        rows = load_articles(settings.SITE_ROOT / 'content/articles.json')
        profile_data = json.loads((settings.SITE_ROOT / 'content/site.json').read_text())
        count = 0
        with transaction.atomic():
            SiteSettings.objects.get_or_create(pk=1, defaults={**profile_data, 'published_payload': profile_data})
            if not ContentImport.objects.filter(key='articles').exists():
                for row in rows:
                    timestamp = datetime.combine(datetime.fromisoformat(row['published_at']).date(), time(9), tzinfo=dt_timezone.utc)
                    defaults = {key: row.get(key, '') for key in ('title', 'category', 'summary', 'body', 'cover', 'cover_alt', 'seo_title', 'seo_description', 'service')}
                    defaults.update(cover_width=row['cover_width'], cover_height=row['cover_height'], featured=row.get('featured', False), published_payload=row, first_published_at=timestamp, last_published_at=timestamp)
                    _, created = Article.objects.get_or_create(slug=row['slug'], defaults=defaults)
                    count += int(created)
                ContentImport.objects.create(key='articles')
            self.seed_sections()
            group, _ = Group.objects.get_or_create(name='Редакторы')
            permissions = Permission.objects.filter(content_type__app_label='cms')
            group.permissions.set(permissions)
        change_and_build()
        self.stdout.write(self.style.SUCCESS(f'Imported {count} new articles; existing entries preserved. Public site built.'))

    def seed_sections(self):
        if ContentImport.objects.filter(key='site-sections').exists():
            return
        services = json.loads((settings.SITE_ROOT / 'content/services.json').read_text())
        for position, row in enumerate(services):
            Service.objects.get_or_create(slug=row['slug'], defaults={
                'title': row['title'], 'summary': row['summary'], 'intro': row['intro'],
                'scope': '\n'.join(row['scope']), 'prepare': row['prepare'], 'image': row['image'],
                'position': position, 'published_payload': {**row, 'position': position, 'seo_title': '', 'seo_description': ''},
                'first_published_at': datetime.now(dt_timezone.utc)})
        projects = json.loads((settings.SITE_ROOT / 'content/projects.json').read_text())
        for position, row in enumerate(projects):
            description = row['description'] if isinstance(row['description'], str) else '\n\n'.join(row['description'])
            payload = {**row, 'position': position, 'description': description, 'seo_title': '', 'seo_description': ''}
            project, created = Project.objects.get_or_create(slug=row['slug'], defaults={
                'title': row['title'], 'summary': row['summary'], 'description': description,
                'details': '\n'.join(row['details']), 'location': row.get('location') or '', 'category': row['category'],
                'service': Service.objects.filter(slug=row['service']).first(), 'position': position,
                'published_payload': payload, 'first_published_at': datetime.now(dt_timezone.utc)})
            if created:
                for index, photo in enumerate(row['photos']):
                    ProjectPhoto.objects.create(project=project, source=photo, caption=photo['caption'], position=index)
        pages = json.loads((settings.SITE_ROOT / 'content/pages.json').read_text())
        profile = SiteSettings.objects.first()
        for row in pages:
            published = {**row, 'seo_title': '', 'seo_description': ''}
            intro = row['intro']
            if row['route'] == 'index.html' and profile:
                # Preserve the old homepage editor's draft and live text separately.
                intro = profile.hero_description
                published['intro'] = (profile.published_payload or {}).get('hero_description', row['intro'])
            page, created = SitePage.objects.get_or_create(route=row['route'], defaults={
                'label': row['label'], 'title': row['title'], 'intro': intro, 'image': row['image'],
                'published_payload': published, 'first_published_at': datetime.now(dt_timezone.utc)})
            if created:
                for index, section in enumerate(row['sections']):
                    PageSection.objects.create(page=page, key=section['key'], title=section['title'], body=section['body'], image=section['image'], position=index)

        ContentImport.objects.create(key='site-sections')
