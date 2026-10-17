from pathlib import Path
import os
import shutil
import sqlite3
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from cms.publishing import publication_lock


class Command(BaseCommand):
    help = 'Create a consistent private SQLite + media backup in a new directory.'
    def add_arguments(self, parser):
        parser.add_argument('--output', required=True)
    def handle(self, *args, **options):
        target = Path(options['output']).resolve()
        database = Path(settings.DATABASES['default']['NAME'])
        if not database.is_file():
            raise CommandError('Database file not found; refusing to create an empty backup.')
        if target.is_relative_to(settings.CMS_PUBLIC_ROOT.resolve()) or target.exists():
            raise CommandError('Choose a new private directory outside the public site.')
        target.mkdir(parents=True, mode=0o700)
        with publication_lock():
            source = sqlite3.connect(database)
            destination = sqlite3.connect(target / 'cms.sqlite3')
            try:
                source.backup(destination)
            finally:
                destination.close()
                source.close()
            os.chmod(target / 'cms.sqlite3', 0o600)
            if settings.MEDIA_ROOT.exists():
                shutil.copytree(settings.MEDIA_ROOT, target / 'media')
        self.stdout.write(self.style.SUCCESS('Backup created. Store this directory privately; it includes user accounts and draft articles.'))
