import mimetypes
from pathlib import Path
from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404
from django.utils.html import escape
from .models import Article
from .publishing import article_payload, current_profile
from scripts.build_site import article_document


def preview_article(request, pk):
    article = get_object_or_404(Article, pk=pk)
    if not request.user.has_perm('cms.view_article'):
        raise Http404
    payload = article_payload(article)
    html = article_document(payload, preview=True, profile=current_profile())
    # Draft uploads stay private, including inside an authenticated preview.
    html = html.replace('src="../' + payload['cover'] + '"', f'src="/admin/article-cover/{article.pk}/"')
    html = html.replace('<head>', '<head><base href="/articles/" />', 1)
    html = html.replace('href="#', f'href="{escape(request.path)}#')
    banner = '<div class="cms-preview-banner"><span>Предпросмотр сохранённой версии · не индексируется поиском</span><a href="/admin/cms/article/'+str(article.pk)+'/change/">Вернуться к редактированию</a></div>'
    html = html.replace('<main id="main">', '<main id="main">'+banner, 1)
    return HttpResponse(html)


def article_cover(request, pk):
    article = get_object_or_404(Article, pk=pk)
    if not request.user.has_perm('cms.view_article'):
        raise Http404
    if article.cover_upload:
        file = Path(article.cover_upload.path)
    else:
        file = (settings.SITE_ROOT / article.cover).resolve()
        if not file.is_relative_to(settings.SITE_ROOT / 'assets'):
            raise Http404
    if not file.is_file():
        raise Http404
    return FileResponse(file.open('rb'), content_type=mimetypes.guess_type(str(file))[0] or 'application/octet-stream')


def public_file(request, path=''):
    if request.method not in ('GET', 'HEAD'):
        return HttpResponseNotAllowed(['GET', 'HEAD'])
    root = settings.CMS_PUBLIC_ROOT.resolve()
    relative = path or 'index.html'
    target = (root / relative).resolve()
    if not target.is_relative_to(root) or not target.is_file() or any(p.startswith('.') for p in Path(relative).parts):
        raise Http404
    response = FileResponse(target.open('rb'), content_type=mimetypes.guess_type(str(target))[0] or 'application/octet-stream')
    response['Cache-Control'] = 'public, max-age=300' if target.suffix in ('.html', '.xml', '.txt') else 'public, max-age=86400'
    return response


from tempfile import TemporaryDirectory
from .models import SitePage, PageSection, Service, Project, ProjectPhoto
from .publishing import content_payload, prepare_build, PublicationError

CONTENT_MODELS = {'sitepage': SitePage, 'pagesection': PageSection, 'service': Service, 'project': Project, 'projectphoto': ProjectPhoto}


def preview_content(request, kind, pk):
    model = CONTENT_MODELS.get(kind)
    if model not in (SitePage, Service, Project) or not request.user.has_perm('cms.view_' + kind):
        raise Http404
    obj = get_object_or_404(model, pk=pk)
    try:
        payload = content_payload(obj)
    except PublicationError as error:
        return HttpResponse('<!doctype html><html lang="ru"><meta charset="utf-8"><title>Предпросмотр</title><main><h1>Дополните материал</h1><p>' + escape(str(error)) + '</p><a href="/admin/cms/' + kind + '/' + str(pk) + '/change/">Вернуться к редактированию</a></main></html>', status=400)
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='preview-', dir=settings.DATA_DIR) as temporary:
        build = Path(temporary) / 'build'
        prepare_build(build, {kind: payload})
        html = (build / 'public' / obj.get_absolute_url().lstrip('/')).read_text()
    import re
    html = re.sub(r'(src|srcset|href)="((?:\.\./)*)assets/uploads/([^" ]+)', lambda match: match[1] + '="/admin/content-upload/' + match[3], html)
    # Responsive srcsets may contain a second path after a comma.
    html = re.sub(r'(?:\.\./)*assets/uploads/([a-f0-9]+\.webp)', r'/admin/content-upload/\1', html)
    html = html.replace('<head>', '<head><meta name="robots" content="noindex,nofollow" /><base href="' + escape(obj.get_absolute_url()) + '" />', 1)
    html = html.replace('href="#', f'href="{escape(request.path)}#')
    banner = '<div class="cms-preview-banner"><span>Предпросмотр сохранённой версии · не индексируется поиском</span><a href="/admin/cms/' + kind + '/' + str(pk) + '/change/">Вернуться к редактированию</a></div>'
    html = html.replace('<main id="main">', '<main id="main">' + banner, 1)
    return HttpResponse(html)


def content_image(request, kind, pk):
    model = CONTENT_MODELS.get(kind)
    permission_kind = {'pagesection': 'sitepage', 'projectphoto': 'project'}.get(kind, kind)
    if not model or not request.user.has_perm('cms.view_' + permission_kind):
        raise Http404
    obj = get_object_or_404(model, pk=pk)
    if obj.image_upload:
        target = Path(obj.image_upload.path)
    else:
        source = obj.source.get('src', '') if isinstance(obj, ProjectPhoto) else obj.image
        target = (settings.SITE_ROOT / source).resolve()
        if not target.is_relative_to(settings.SITE_ROOT / 'assets'):
            raise Http404
    if not target.is_file():
        raise Http404
    return FileResponse(target.open('rb'), content_type=mimetypes.guess_type(str(target))[0] or 'application/octet-stream')


def preview_upload(request, name):
    import re
    if not re.fullmatch(r'[a-f0-9]{32}\.webp', name) or not any(request.user.has_perm('cms.view_' + kind) for kind in ('article', 'sitepage', 'project', 'service')):
        raise Http404
    target = next((settings.MEDIA_ROOT / folder / name for folder in ('articles', 'content') if (settings.MEDIA_ROOT / folder / name).is_file()), None)
    if target is None:
        raise Http404
    return FileResponse(target.open('rb'), content_type='image/webp')
