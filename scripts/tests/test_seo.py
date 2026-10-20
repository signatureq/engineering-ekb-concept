"""Crawl a complete generated site to check search metadata and local resources."""
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import urljoin, urlsplit, unquote
from urllib.robotparser import RobotFileParser
import xml.etree.ElementTree as ET

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from article_content import SITE_URL, article_schema, load_articles, render_markdown
from site_seo import metadata


class Document(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.tags = []
        self.schemas = []
        self.title = ''
        self.reading_title = False
        self.reading_schema = False
        self.schema_text = ''
        self.feed(source)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        self.tags.append((tag, attrs))
        self.reading_title = tag == 'title' or self.reading_title
        if tag == 'script' and attrs.get('type') == 'application/ld+json':
            self.reading_schema = True
            self.schema_text = ''

    def handle_data(self, text):
        if self.reading_title:
            self.title += text
        if self.reading_schema:
            self.schema_text += text

    def handle_endtag(self, tag):
        if tag == 'title':
            self.reading_title = False
        if tag == 'script' and self.reading_schema:
            self.schemas.append(json.loads(self.schema_text))
            self.reading_schema = False


class ArticleHeadings(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.in_article = False
        self.in_h2 = False
        self.headings = []
        self.text = ''
        self.feed(source)

    def handle_starttag(self, tag, attributes):
        if tag == 'article' and 'article-prose' in dict(attributes).get('class', '').split():
            self.in_article = True
        if tag == 'h2':
            self.in_h2 = True
            self.text = ''

    def handle_data(self, text):
        if self.in_h2:
            self.text += text

    def handle_endtag(self, tag):
        if tag == 'h2':
            self.headings.append((self.text, self.in_article))
            self.in_h2 = False
        if tag == 'article':
            self.in_article = False


class SearchReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.output = Path(cls.temp.name)
        subprocess.run([sys.executable, str(ROOT / 'scripts/build_site.py'), '--output-dir', str(cls.output)], check=True, capture_output=True)
        cls.documents = {p.relative_to(cls.output).as_posix(): Document(p.read_text()) for p in cls.output.rglob('*.html')}

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_every_public_page_has_unique_metadata_and_is_in_sitemap(self):
        namespace = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        sitemap = ET.parse(self.output / 'sitemap.xml')
        urls = [item.text for item in sitemap.findall('s:url/s:loc', namespace)]
        canonical_urls, titles, descriptions = [], [], []
        self.assertGreaterEqual(len(self.documents), 27)
        for route, document in self.documents.items():
            with self.subTest(route=route):
                canonical = [a['href'] for t, a in document.tags if t == 'link' and a.get('rel') == 'canonical']
                expected = SITE_URL + ('/' if route == 'index.html' else '/' + route)
                self.assertEqual(canonical, [expected])
                desc = [a['content'] for t, a in document.tags if t == 'meta' and a.get('name') == 'description']
                self.assertEqual(len(desc), 1)
                self.assertGreater(len(desc[0]), 15)
                self.assertTrue(document.title.strip())
                self.assertFalse(any(a.get('name') == 'robots' and 'noindex' in a.get('content', '') for _, a in document.tags))
                self.assertTrue(document.schemas)
                self.assertEqual([a['content'] for t, a in document.tags if t == 'meta' and a.get('property') == 'og:url'], canonical)
                canonical_urls.extend(canonical)
                titles.append(document.title)
                descriptions.extend(desc)
        self.assertEqual(set(urls), set(canonical_urls))
        self.assertEqual(len(urls), len(canonical_urls))
        self.assertEqual(len(titles), len(set(titles)))
        self.assertEqual(len(descriptions), len(set(descriptions)))

    def test_linked_local_resources_and_social_images_exist(self):
        for route, document in self.documents.items():
            for tag, attrs in document.tags:
                links = [attrs[key] for key in ('href', 'src') if key in attrs]
                if tag == 'meta' and attrs.get('property') == 'og:image':
                    links.append(attrs['content'])
                if 'srcset' in attrs:
                    links.extend(part.strip().split()[0] for part in attrs['srcset'].split(','))
                for link in links:
                    resolved = urlsplit(urljoin(SITE_URL + '/' + route, link))
                    if resolved.scheme not in ('http', 'https') or resolved.netloc != urlsplit(SITE_URL).netloc:
                        continue
                    path = unquote(resolved.path).lstrip('/') or 'index.html'
                    with self.subTest(route=route, link=link):
                        self.assertTrue((self.output / path).is_file(), path)

    def test_robots_allows_pages_icons_and_blocks_private_endpoints(self):
        robots = RobotFileParser()
        robots.parse((self.output / 'robots.txt').read_text().splitlines())
        self.assertEqual(robots.site_maps(), [SITE_URL + '/sitemap.xml'])
        for bot in ('Googlebot', 'YandexBot'):
            for path in ('/', '/favicon.ico', '/favicon.svg', '/assets/brand/orion-120.png', '/articles.html'):
                self.assertTrue(robots.can_fetch(bot, SITE_URL + path))
            for path in ('/admin', '/admin/login', '/cms-preview/article/1', '/api/inquiry/', '/livewire-7bba8181/update'):
                self.assertFalse(robots.can_fetch(bot, SITE_URL + path))

    def test_icons_are_square_and_multi_resolution(self):
        for size in (120, 180, 192, 512):
            with Image.open(self.output / f'assets/brand/orion-{size}.png') as icon:
                self.assertEqual(icon.size, (size, size))
        with Image.open(self.output / 'favicon.ico') as icon:
            self.assertEqual(icon.ico.sizes(), {(16, 16), (32, 32), (48, 48)})

    def test_article_h2_headings_come_only_from_the_unchanged_editorial_body(self):
        for article in load_articles(ROOT / 'content/articles.json'):
            with self.subTest(article=article['slug']):
                html = (self.output / 'articles' / (article['slug'] + '.html')).read_text()
                body, _ = render_markdown(article['body'])
                headings = ArticleHeadings(html).headings
                expected = ArticleHeadings('<article class="article-prose">' + body + '</article>').headings
                self.assertGreater(len(headings), 0)
                self.assertEqual(headings, expected)
                self.assertTrue(all(in_body for _, in_body in headings))
                self.assertIn(body, html)

    def test_editable_company_is_preserved_in_structured_data(self):
        site = {'company_name': 'Монтаж «Тест»', 'phone': '+7 (902) 445-30-01'}
        title, canonical, head = metadata('services/test.html', 'Монтаж', 'Описание услуги', SITE_URL, site)
        document = Document(head)
        self.assertIn(site['company_name'], title)
        self.assertEqual(canonical, SITE_URL + '/services/test.html')
        self.assertEqual(document.schemas[0]['@graph'][0]['name'], site['company_name'])
        article = {'slug': 'test', 'title': 'Статья', 'summary': 'Описание', 'cover': 'assets/test.png', 'published_at': '2026-10-19', 'updated_at': '2026-10-19'}
        self.assertEqual(article_schema(article, site['company_name'])['publisher']['name'], site['company_name'])


if __name__ == '__main__':
    unittest.main()
