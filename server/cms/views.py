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
