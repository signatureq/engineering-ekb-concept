from django.db import migrations


def preserve_article_import(apps, schema_editor):
    if apps.get_model('cms', 'Article').objects.exists() or apps.get_model('cms', 'SiteSettings').objects.exists():
        apps.get_model('cms', 'ContentImport').objects.get_or_create(key='articles')


class Migration(migrations.Migration):
    dependencies = [('cms', '0006_contentimport')]
    operations = [migrations.RunPython(preserve_article_import, migrations.RunPython.noop)]
