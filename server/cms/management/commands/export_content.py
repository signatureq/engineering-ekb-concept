from pathlib import Path
import json
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from cms.models import Article
from cms.publishing import current_profile
class Command(BaseCommand):
    help = 'Export published content only, for a static build or migration. Does not include users or draft revisions.'
    def add_arguments(self, parser):
        parser.add_argument('--output', type=Path, required=True)
    def handle(self, *args, **options):
        output = options['output'].resolve()
        if output == settings.SITE_ROOT:
            raise CommandError('Choose a dedicated export directory.')
        output.mkdir(parents=True, exist_ok=True)
        articles = list(Article.objects.filter(published_payload__isnull=False).values_list('published_payload', flat=True))
        (output / 'articles.json').write_text(json.dumps(articles, ensure_ascii=False, indent=2))
        (output / 'site.json').write_text(json.dumps(current_profile(), ensure_ascii=False, indent=2))
        self.stdout.write(self.style.SUCCESS(f'Exported {len(articles)} published articles. Copy public assets/uploads as well when moving photographs.'))
