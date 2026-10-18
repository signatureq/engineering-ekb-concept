"""Derive technical article fields without asking the editor to enter them."""
from html import unescape
import re
import uuid
from django.utils.html import strip_tags
from django.utils.text import slugify
from scripts.article_content import render_markdown

RUSSIAN = dict(zip('абвгдеёжзийклмнопрстуфхцчшщъыьэюя', ['a','b','v','g','d','e','e','zh','z','i','y','k','l','m','n','o','p','r','s','t','u','f','h','ts','ch','sh','sch','','y','','e','yu','ya']))


def fill_automatic_fields(article, title, body):
    from .models import Article
    article.title, article.body = title, body
    if not article.slug:
        base = slugify(''.join(RUSSIAN.get(c, c) for c in title.lower()))[:110].strip('-') or 'statya-' + uuid.uuid4().hex[:8]
        candidate, suffix = base, 2
        while Article.objects.filter(slug=candidate).exclude(pk=article.pk).exists():
            candidate = f'{base}-{suffix}'; suffix += 1
        article.slug = candidate
    html, _ = render_markdown(body)
    plain = re.sub(r'\s+', ' ', unescape(strip_tags(html))).strip()
    article.summary = plain[:260].rsplit(' ', 1)[0] + '…' if len(plain) > 260 else plain
    article.cover_alt = title[:240]
    if not article.category:
        lower = title.lower()
        category, service = 'Инженерные сети', ''
        if 'изол' in lower:
            category, service = 'Теплоизоляция', 'insulation'
        elif any(word in lower for word in ('учёт', 'учет')):
            category, service = 'Узлы учёта', 'metering'
        elif 'авар' in lower:
            category, service = 'Аварийные работы', 'emergency'
        elif any(word in lower for word in ('монтаж', 'труб', 'свар')):
            category, service = 'Монтаж трубопроводов', 'pipeline-installation'
        article.category, article.service = category, service


def automatic_slug(model, title, pk=None):
    base = slugify(''.join(RUSSIAN.get(c, c) for c in title.lower()))[:110].strip('-') or 'stranitsa-' + uuid.uuid4().hex[:8]
    candidate, suffix = base, 2
    while model.objects.filter(slug=candidate).exclude(pk=pk).exists():
        candidate = f'{base}-{suffix}'
        suffix += 1
    return candidate
