from django.core.management.base import BaseCommand
from cms.publishing import change_and_build
class Command(BaseCommand):
    help = 'Rebuild from published snapshots. Draft text remains private.'
    def handle(self, *args, **options):
        build = change_and_build()
        self.stdout.write(self.style.SUCCESS(f'Published complete build: {build.name}'))
