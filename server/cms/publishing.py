"""Publish complete builds, never partial HTML or unsaved draft contents."""
from contextlib import contextmanager
from pathlib import Path
import fcntl
import json
import logging
import os
import shutil
import subprocess
import sys
import uuid
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from PIL import Image
from .models import Article, SiteSettings

logger = logging.getLogger(__name__)


class PublicationError(Exception):
    pass


@contextmanager
def publication_lock():
    lock_path = settings.DATA_DIR / 'publication.lock'
    with lock_path.open('a') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def current_profile():
    profile = SiteSettings.objects.first()
    return profile.published_payload if profile and profile.published_payload else json.loads((settings.SITE_ROOT / 'content/site.json').read_text())


def article_payload(article):
    if article.cover_upload:
        file = Path(article.cover_upload.path)
        cover = 'assets/uploads/' + file.name
    else:
        cover = article.cover
        file = (settings.SITE_ROOT / cover).resolve()
        if not file.is_relative_to(settings.SITE_ROOT / 'assets'):
            raise PublicationError('Недопустимый путь фотографии.')
    if not file.is_file():
        raise PublicationError('Обложка не найдена. Загрузите фотографию снова или выберите изображение из портфолио.')
    with Image.open(file) as image:
        width, height = image.size
    now = timezone.localdate().isoformat()
    first = timezone.localdate(article.first_published_at).isoformat() if article.first_published_at else now
    return {'slug': article.slug, 'title': article.title, 'category': article.category, 'summary': article.summary, 'body': article.body, 'seo_title': article.seo_title, 'seo_description': article.seo_description, 'cover': cover, 'cover_alt': article.cover_alt, 'cover_width': width, 'cover_height': height, 'service': article.service, 'featured': article.featured, 'published_at': first, 'updated_at': now}


def prepare_build(build, overrides=None):
    public = build / 'public'
    public.mkdir(parents=True)
    articles = [a.published_payload for a in Article.objects.filter(published_payload__isnull=False)]
    # Retain images that were already public so cached pages remain usable.
    old_uploads = settings.CMS_PUBLIC_ROOT / 'assets/uploads'
    if old_uploads.is_dir():
        shutil.copytree(old_uploads, public / 'assets/uploads', dirs_exist_ok=True)
    pages = published_collection(SitePage, 'pages.json')
    services = published_collection(Service, 'services.json')
    projects = published_collection(Project, 'projects.json')
    collections = {'sitepage': pages, 'service': services, 'project': projects}
    for kind, payload in (overrides or {}).items():
        identity = 'route' if kind == 'sitepage' else 'slug'
        collections[kind][:] = [row for row in collections[kind] if row[identity] != payload[identity]] + [payload]
    def collect_uploads(value):
        if isinstance(value, dict):
            for child in value.values():
                yield from collect_uploads(child)
        elif isinstance(value, list):
            for child in value:
                yield from collect_uploads(child)
        elif isinstance(value, str) and value.startswith('assets/uploads/'):
            yield value
    for cover in set(collect_uploads([articles, pages, services, projects])):
        name = Path(cover).name
        original = next((settings.MEDIA_ROOT / folder / name for folder in ('articles', 'content') if (settings.MEDIA_ROOT / folder / name).is_file()), None)
        if original is None:
            raise PublicationError('Не найдена опубликованная фотография. Восстановите её из резервной копии.')
        dest = public / cover
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, dest)
    content_files = []
    for name, payload in [('pages', pages), ('services', services), ('projects', projects)]:
        target = build / (name + '.json')
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        content_files += ['--' + name + '-file', str(target)]
    article_file = build / 'articles.json'
    site_file = build / 'site.json'
    article_file.write_text(json.dumps(articles, ensure_ascii=False, indent=2))
    site_file.write_text(json.dumps(current_profile(), ensure_ascii=False, indent=2))
    try:
        result = subprocess.run([sys.executable, str(settings.SITE_ROOT / 'scripts/build_site.py'), '--output-dir', str(public), '--articles-file', str(article_file), '--site-file', str(site_file), *content_files], capture_output=True, text=True, timeout=90)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise PublicationError('Сборка сайта не завершилась. Сохранённые черновики доступны; повторите публикацию.') from error
    if result.returncode:
        logger.error('Static build failed: %s', result.stderr[-3000:])
        raise PublicationError('Не удалось собрать страницы. Опубликованная версия сохранена; проверьте журнал сервера и повторите публикацию.')
    if not (public / 'index.html').is_file() or not (public / 'sitemap.xml').is_file():
        raise PublicationError('Сборка не создала обязательные страницы.')
    return build


def activate(build):
    link = settings.DATA_DIR / ('.public-next-' + uuid.uuid4().hex)
    try:
        link.symlink_to(build / 'public', target_is_directory=True)
        os.replace(link, settings.CMS_PUBLIC_ROOT)
    finally:
        link.unlink(missing_ok=True)


def restore_target(previous):
    if previous:
        link = settings.DATA_DIR / ('.public-restore-' + uuid.uuid4().hex)
        link.symlink_to(previous, target_is_directory=True)
        os.replace(link, settings.CMS_PUBLIC_ROOT)
    elif settings.CMS_PUBLIC_ROOT.is_symlink():
        settings.CMS_PUBLIC_ROOT.unlink()


def change_and_build(change=None):
    with publication_lock():
        previous = settings.CMS_PUBLIC_ROOT.resolve() if settings.CMS_PUBLIC_ROOT.is_symlink() else None
        activated = False
        build = None
        try:
            with transaction.atomic():
                if change:
                    change()
                build = settings.DATA_DIR / 'builds' / uuid.uuid4().hex
                prepare_build(build)
                activate(build)
                activated = True
        except Exception:
            if activated:
                restore_target(previous)
            if build and build.is_dir():
                shutil.rmtree(build)
            raise
        # Keep the current and two preceding complete builds for a quick rollback.
        builds = sorted((settings.DATA_DIR / 'builds').iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        for obsolete in builds[3:]:
            if obsolete.is_dir() and obsolete != build:
                shutil.rmtree(obsolete)
        return build


def publish_article(pk):
    def change():
        article = Article.objects.select_for_update().get(pk=pk)
        article.full_clean()
        article.published_payload = article_payload(article)
        now = timezone.now()
        article.first_published_at = article.first_published_at or now
        article.last_published_at = now
        article.save(update_fields=['published_payload', 'first_published_at', 'last_published_at'])
    return change_and_build(change)


def unpublish_article(pk):
    def change():
        Article.objects.filter(pk=pk).update(published_payload=None, last_published_at=None)
    return change_and_build(change)


def publish_settings(pk):
    def change():
        profile = SiteSettings.objects.select_for_update().get(pk=pk)
        profile.full_clean()
        profile.published_payload = profile.as_dict()
        profile.save(update_fields=['published_payload'])
    return change_and_build(change)


from .models import SitePage, PageSection, Service, Project, ProjectPhoto, ContentImport


def image_payload(source, uploaded=None, caption='Фотография'):
    if uploaded:
        path = Path(uploaded.path)
        src = 'assets/uploads/' + path.name
    else:
        path = (settings.SITE_ROOT / source).resolve()
        if not path.is_relative_to(settings.SITE_ROOT / 'assets'):
            raise PublicationError('Выберите фотографию сайта или загрузите новый файл.')
        src = source
    if not path.is_file():
        raise PublicationError('Фотография не найдена. Загрузите её снова.')
    with Image.open(path) as im:
        width, height = im.size
    return {'src': src, 'small': src, 'width': width, 'height': height, 'small_width': width, 'caption': caption}


def content_payload(obj):
    common = {'title': obj.title, 'seo_title': obj.seo_title, 'seo_description': obj.seo_description}
    if isinstance(obj, SitePage):
        payload = {**common, 'route': obj.route, 'label': obj.label, 'intro': obj.intro, 'image': '', 'sections': []}
        if obj.image or obj.image_upload:
            payload['image'] = image_payload(obj.image, obj.image_upload, obj.title)['src']
        for section in obj.sections.all():
            image = image_payload(section.image, section.image_upload, section.title)['src'] if section.image or section.image_upload else ''
            payload['sections'].append({'key': section.key, 'title': section.title, 'body': section.body, 'image': image})
        return payload
    if isinstance(obj, Service):
        photo = image_payload(obj.image, obj.image_upload, obj.title)
        related = [p.published_payload['slug'] for p in Project.objects.filter(published_payload__isnull=False) if p.published_payload.get('service') == obj.slug]
        return {**common, 'position': obj.position, 'slug': obj.slug, 'summary': obj.summary, 'intro': obj.intro, 'scope': [line.strip() for line in obj.scope.splitlines() if line.strip()], 'prepare': obj.prepare, 'image': photo['src'], 'width': photo['width'], 'height': photo['height'], 'alt': obj.title, 'works': related}
    if isinstance(obj, Project):
        photos = []
        for photo in obj.photos.all():
            if photo.image_upload:
                item = image_payload('', photo.image_upload, photo.caption or obj.title)
            else:
                item = {**photo.source, 'caption': photo.caption or obj.title}
                # Seeded photos also pass the same safe-path and file validation.
                image_payload(item.get('src', ''), caption=item['caption'])
            photos.append(item)
        if not photos:
            raise PublicationError('Добавьте хотя бы одну фотографию работы перед публикацией.')
        return {**common, 'position': obj.position, 'slug': obj.slug, 'summary': obj.summary, 'description': obj.description, 'details': [line.strip() for line in obj.details.splitlines() if line.strip()], 'location': obj.location or None, 'category': obj.category, 'service': obj.service.slug if obj.service else '', 'cover_position': (obj.published_payload or {}).get('cover_position', '50% 50%'), 'photos': photos}
    raise PublicationError('Раздел не найден.')


def publish_content(model, pk):
    def change():
        obj = model.objects.select_for_update().get(pk=pk)
        obj.full_clean()
        obj.published_payload = content_payload(obj)
        obj.first_published_at = obj.first_published_at or timezone.now()
        obj.save(update_fields=['published_payload', 'first_published_at'])
    return change_and_build(change)


def unpublish_content(model, pk):
    if model not in (Service, Project):
        raise PublicationError('Основную страницу сайта нельзя скрыть.')
    def change():
        model.objects.filter(pk=pk).update(published_payload=None)
    return change_and_build(change)


def published_collection(model, filename):
    rows = model.objects.all()
    if not rows.exists():
        if ContentImport.objects.filter(key='site-sections').exists():
            return []
        initial = json.loads((settings.SITE_ROOT / 'content' / filename).read_text())
        if model == SitePage:
            for page in initial:
                if page['route'] == 'index.html':
                    page['intro'] = current_profile().get('hero_description', page['intro'])
        return initial
    snapshots = [row.published_payload for row in rows.order_by('pk') if row.published_payload is not None]
    return sorted(snapshots, key=lambda item: item.get('position', 0)) if model in (Service, Project) else snapshots
