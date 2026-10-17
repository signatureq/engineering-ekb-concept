from datetime import datetime, time, timezone as dt_timezone
import json
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.conf import settings
from django.db import transaction
from scripts.article_content import load_articles
from cms.models import Article, SiteSettings
from cms.publishing import change_and_build


class Command(BaseCommand):
    help = 'Import initial articles once without overwriting later editor changes, then build public pages.'
    def handle(self, *args, **options):
        rows = load_articles(settings.SITE_ROOT / 'content/articles.json')
        profile_data = json.loads((settings.SITE_ROOT / 'content/site.json').read_text())
        count = 0
        with transaction.atomic():
            SiteSettings.objects.get_or_create(pk=1, defaults={**profile_data, 'published_payload': profile_data})
            for row in rows:
                timestamp = datetime.combine(datetime.fromisoformat(row['published_at']).date(), time(9), tzinfo=dt_timezone.utc)
                defaults = {key: row.get(key, '') for key in ('title', 'category', 'summary', 'body', 'cover', 'cover_alt', 'seo_title', 'seo_description', 'service')}
                defaults.update(cover_width=row['cover_width'], cover_height=row['cover_height'], featured=row.get('featured', False), published_payload=row, first_published_at=timestamp, last_published_at=timestamp)
                _, created = Article.objects.get_or_create(slug=row['slug'], defaults=defaults)
                count += int(created)
            group, _ = Group.objects.get_or_create(name='Редакторы')
            permissions = Permission.objects.filter(content_type__app_label='cms', codename__in=['view_article', 'add_article', 'change_article', 'delete_article', 'view_sitesettings', 'change_sitesettings'])
            group.permissions.set(permissions)
        change_and_build()
        self.stdout.write(self.style.SUCCESS(f'Imported {count} new articles; existing entries preserved. Public site built.'))
