"""Shared article validation and safe Markdown rendering for the site and CMS."""
from datetime import date
from html import escape
import json
from pathlib import Path
import re

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[1]
SITE_URL = 'https://stroy-ekb.ru'
SLUG = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
CATEGORIES = ('Монтаж трубопроводов', 'Теплоизоляция', 'Узлы учёта', 'Инженерные сети', 'Аварийные работы')


def load_articles(path):
    rows = json.loads(Path(path).read_text())
    result = []
    slugs = set()
    for row in rows:
        item = dict(row)
        if not SLUG.fullmatch(item.get('slug', '')) or item['slug'] in slugs:
            raise ValueError('Некорректный или повторяющийся адрес статьи')
        slugs.add(item['slug'])
        if 'body_path' in item:
            body_path = (ROOT / item['body_path']).resolve()
            if not body_path.is_relative_to(ROOT / 'content/articles'):
                raise ValueError('Недопустимый путь текста статьи')
            item['body'] = body_path.read_text()
        if not all(item.get(key) for key in ('title', 'summary', 'body', 'cover_alt')):
            raise ValueError('Не заполнены обязательные поля статьи')
        cover = Path(item['cover'])
        if cover.is_absolute() or '..' in cover.parts or not str(cover).startswith('assets/'):
            raise ValueError('Недопустимый путь обложки')
        date.fromisoformat(item['published_at'][:10])
        date.fromisoformat(item['updated_at'][:10])
        result.append(item)
    return sorted(result, key=lambda item: (item.get('featured', False), item['published_at']), reverse=True)


def render_markdown(body):
    md = MarkdownIt('commonmark', {'html': False, 'breaks': False})
    tokens = md.parse(body)
    toc = []
    for index, token in enumerate(tokens):
        if token.type != 'heading_open':
            continue
        if token.tag == 'h1':
            token.tag = 'h2'
            tokens[index + 2].tag = 'h2'
        anchor = f'section-{len(toc) + 1}'
        token.attrSet('id', anchor)
        title = re.sub(r'[*_`]', '', tokens[index + 1].content)
        toc.append((anchor, title))
    # Raw HTML is disabled; MarkdownIt's link validator rejects javascript URLs.
    # Embedded pictures are limited to the website's own image directory.
    original_image = md.renderer.rules['image']

    def image_rule(tokens, idx, options, env):
        token = tokens[idx]
        src = token.attrGet('src') or ''
        clean = src.removeprefix('../').removeprefix('/')
        if not clean.startswith('assets/') or '..' in Path(clean).parts:
            return escape(token.content)
        token.attrSet('loading', 'lazy')
        return original_image(tokens, idx, options, env)

    md.renderer.rules['image'] = image_rule
    return md.renderer.render(tokens, md.options, {}), toc


def reading_minutes(body):
    return max(1, round(len(body.split()) / 180))


def display_date(value):
    months = ('января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря')
    d = date.fromisoformat(value[:10])
    return f'{d.day} {months[d.month - 1]} {d.year}'


def article_schema(item):
    url = f'{SITE_URL}/articles/{item["slug"]}.html'
    return {
        '@context': 'https://schema.org', '@type': 'Article',
        'headline': item['title'], 'description': item.get('seo_description') or item['summary'],
        'datePublished': item['published_at'], 'dateModified': item['updated_at'],
        'image': f'{SITE_URL}/{item["cover"]}', 'mainEntityOfPage': url,
        'author': {'@type': 'Organization', 'name': 'СК Орион'},
        'publisher': {'@type': 'Organization', 'name': 'СК Орион', 'url': SITE_URL},
    }


def json_ld(data):
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False).replace('<', '\\u003c') + '</script>'
