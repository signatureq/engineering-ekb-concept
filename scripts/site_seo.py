"""Search metadata shared by every public page, including CMS publications."""
from html import escape
import json


def canonical_url(origin, route):
    return origin.rstrip('/') + ('/' if route == 'index.html' else '/' + route)


def metadata(route, title, description, origin, site, image='', social_type='website', service=None):
    origin = origin.rstrip('/')
    canonical = canonical_url(origin, route)
    company = site['company_name']
    page_title = title if company.casefold() in title.casefold() else f'{title} — {company}'
    image_url = origin + '/' + (image or 'assets/brand/orion-512.png').lstrip('/')
    organization = {
        '@type': 'Organization', '@id': origin + '/#organization',
        'name': company, 'url': origin + '/', 'telephone': site['phone'],
        'logo': {'@type': 'ImageObject', 'url': origin + '/assets/brand/orion-512.png', 'width': 512, 'height': 512},
        'areaServed': site.get('region', 'Екатеринбург и Свердловская область'),
    }
    webpage = {
        '@type': 'WebPage', '@id': canonical + '#webpage', 'url': canonical,
        'name': page_title, 'description': description, 'inLanguage': 'ru-RU',
        'isPartOf': {'@id': origin + '/#website'},
        'about': {'@id': origin + '/#organization'},
    }
    graph = [organization, {
        '@type': 'WebSite', '@id': origin + '/#website', 'url': origin + '/',
        'name': company, 'inLanguage': 'ru-RU', 'publisher': {'@id': organization['@id']},
    }, webpage]
    if route != 'index.html':
        crumbs = [('Главная', origin + '/')]
        parent = {'services': ('Услуги', 'services.html'), 'works': ('Наши работы', 'works.html'), 'articles': ('Статьи', 'articles.html')}.get(route.split('/')[0])
        if parent:
            crumbs.append((parent[0], origin + '/' + parent[1]))
        crumbs.append((title, canonical))
        graph.append({
            '@type': 'BreadcrumbList', '@id': canonical + '#breadcrumbs',
            'itemListElement': [{'@type': 'ListItem', 'position': index, 'name': name, 'item': url} for index, (name, url) in enumerate(crumbs, 1)],
        })
        webpage['breadcrumb'] = {'@id': canonical + '#breadcrumbs'}
    if service:
        graph.append({
            '@type': 'Service', '@id': canonical + '#service', 'url': canonical,
            'name': service['title'], 'description': service['summary'],
            'provider': {'@id': organization['@id']}, 'areaServed': organization['areaServed'],
        })
        webpage['mainEntity'] = {'@id': canonical + '#service'}
    tags = [
        ('property', 'og:type', social_type), ('property', 'og:locale', 'ru_RU'),
        ('property', 'og:site_name', company), ('property', 'og:title', page_title),
        ('property', 'og:description', description), ('property', 'og:url', canonical),
        ('property', 'og:image', image_url), ('property', 'og:image:alt', title),
        ('name', 'twitter:card', 'summary_large_image'), ('name', 'twitter:title', page_title),
        ('name', 'twitter:description', description), ('name', 'twitter:image', image_url),
    ]
    head = '\n  '.join(f'<meta {attribute}="{key}" content="{escape(value, quote=True)}" />' for attribute, key, value in tags)
    head += '\n  <script type="application/ld+json">' + json.dumps({'@context': 'https://schema.org', '@graph': graph}, ensure_ascii=False).replace('<', '\\u003c') + '</script>'
    return page_title, canonical, head
