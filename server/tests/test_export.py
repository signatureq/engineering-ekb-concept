import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from django.core.management import call_command
from django.test import TestCase
from cms.models import Article, SitePage, Service, Project


class PublishedExportTests(TestCase):
    def test_all_content_types_export_snapshots_without_drafts(self):
        models = ((SitePage, {'route': 'about.html', 'label': 'О компании'}),
                  (Service, {'slug': 'montazh'}),
                  (Project, {'slug': 'obekt'}),
                  (Article, {'slug': 'statya'}))
        for model, fields in models:
            model.objects.create(**fields, title='PRIVATE_UNPUBLISHED_TITLE',
                                 published_payload={'title': 'Опубликованный текст'})
        Service.objects.create(slug='private-draft', title='PRIVATE_UNPUBLISHED_SERVICE')
        Article.objects.create(slug='private-article', title='PRIVATE_UNPUBLISHED_ARTICLE')
        with TemporaryDirectory() as temporary:
            output = Path(temporary)
            call_command('export_content', output=output, stdout=StringIO())
            self.assertEqual({p.name for p in output.iterdir()},
                             {'articles.json', 'site.json', 'pages.json', 'services.json', 'projects.json'})
            for filename in ('articles.json', 'pages.json', 'services.json', 'projects.json'):
                data = json.loads((output / filename).read_text())
                self.assertEqual(data, [{'title': 'Опубликованный текст'}])
            self.assertNotIn('PRIVATE_UNPUBLISHED', ''.join(p.read_text() for p in output.iterdir()))
