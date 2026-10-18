#!/usr/bin/env python3
"""Build the public website. Run: python3 scripts/build_site.py.
Edit content/projects.json for project names, addresses, descriptions and photos.
No runtime, dependencies or routing server required.
"""
from pathlib import Path
from string import Template
from html import escape
import json
import argparse
import shutil
import sys
from xml.sax.saxutils import escape as xml_escape

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
from article_content import load_articles, render_markdown, reading_minutes, display_date, article_schema, json_ld, SITE_URL, SITE_NOINDEX
from site_seo import metadata

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = json.loads((ROOT / 'content/projects.json').read_text())
OUTPUT_ROOT = ROOT
ARTICLE_SOURCE = ROOT / 'content/articles.json'
SITE = json.loads((ROOT / 'content/site.json').read_text())
BASE = Template((ROOT / 'templates/base.html').read_text())
VERSION = '20261013-pages'
PHONE = '+7 (902) 445-30-01'
SVG = '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true">{}</svg>'
ARROW = SVG.format('<path d="M5 12h14m-6-6 6 6-6 6"/>')
PHONE_ICON = SVG.format('<path d="m7 3 3 5-2.5 2.5a15 15 0 0 0 6 6L16 14l5 3v3a1 1 0 0 1-1 1C10.6 21 3 13.4 3 4a1 1 0 0 1 1-1h3Z"/>')
EXPAND = SVG.format('<path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5"/>')
NAV = [('services.html','Услуги'),('works.html','Наши работы'),('about.html','О компании'),('process.html','Как работаем'),('articles.html','Статьи'),('contacts.html','Контакты')]
CATEGORIES = {'outside':'Наружные сети','inside':'Внутренние системы','insulation':'Теплоизоляция'}
SERVICES = json.loads((ROOT / 'content/services.json').read_text())
PAGES = json.loads((ROOT / 'content/pages.json').read_text())

def prose(text):
    return render_markdown(text or '')[0]

def page_data(route):
    return next((p for p in PAGES if p['route'] == route), {})

def section_data(route, key):
    return next((p for p in page_data(route).get('sections', []) if p['key'] == key), {'title': '', 'body': '', 'image': ''})

def heading(route):
    page = page_data(route)
    return page_head(page['title'], page['intro'])

def e(text): return escape(str(text), quote=True)
def button(text, href, light=False):
    return f'<a class="button {"button-light" if light else "button-primary"}" href="{e(href)}">{e(text)} {ARROW}</a>'
def image(photo, prefix='', eager=False, card=False):
    sizes = '(max-width: 650px) 100vw, (max-width: 1000px) 50vw, 33vw' if card else '(max-width: 850px) 100vw, 55vw'
    priority = 'fetchpriority="high"' if eager else ''
    return f'<img src="{prefix}{photo["src"]}" srcset="{prefix}{photo["small"]} {photo["small_width"]}w, {prefix}{photo["src"]} {photo["width"]}w" sizes="{sizes}" width="{photo["width"]}" height="{photo["height"]}" alt="{e(photo["caption"])}" loading="{"eager" if eager else "lazy"}" decoding="async" {priority} />'
def breadcrumb(label, prefix='', parent=None):
    middle = f'<a href="{prefix}{parent[0]}">{parent[1]}</a><span aria-hidden="true">/</span>' if parent else ''
    return f'<nav class="breadcrumb" aria-label="Хлебные крошки"><a href="{prefix}index.html">Главная</a><span aria-hidden="true">/</span>{middle}<span aria-current="page">{e(label)}</span></nav>'
def page_head(title, text, prefix='', parent=None):
    return f'<div class="section-shell">{breadcrumb(title,prefix,parent)}<div class="page-heading"><h1>{e(title)}</h1><p>{e(text)}</p></div></div>'
def callout(prefix='', title='Обсудим ваш объект', text='Расскажите, какие работы нужны и где находится объект.', service=''):
    target = f'{prefix}request.html' + (f'?service={service}' if service else '') + '#request'
    return f'<section class="inquiry-band section-shell"><div><h2>{e(title)}</h2><p>{e(text)}</p></div><div class="inquiry-actions">{button("Оставить заявку",target,True)}<a class="band-phone" href="tel:+79024453001">{PHONE}</a></div></section>'
def project_card(p,prefix='',eager=False):
    return f'''<article class="portfolio-card" data-category="{p['category']}"><a href="{prefix}works/{p['slug']}.html" class="portfolio-link"><div class="portfolio-cover" style="--photo-position:{p['cover_position']}">{image(p['photos'][0],prefix,eager,True)}<span class="photo-count">{len(p['photos'])} фото</span></div><div class="portfolio-copy"><p class="portfolio-category">{CATEGORIES[p['category']]}</p><h2>{e(p['title'])}</h2><p>{e(p['summary'])}</p><span class="portfolio-open">Смотреть работу {ARROW}</span></div></a></article>'''
def project_grid(projects,prefix='',eager=False):
    return '<div class="portfolio-grid">' + ''.join(project_card(p,prefix,eager and i<3) for i,p in enumerate(projects)) + '</div>'
def related(slugs,prefix='../',title='Работы по этому направлению',text=''):
    ps = [p for slug in slugs for p in PROJECTS if p['slug']==slug]
    return f'<section class="portfolio-section section-shell"><div class="split-heading"><h2>{e(title)}</h2><a class="text-link" href="{prefix}works.html">Все работы {ARROW}</a></div>{prose(text)}{project_grid(ps,prefix)}</section>' if ps else ''
def document(route,title,description,content,active='',dialog='',body_class='',preload='',extra_head='',profile=None,share_image='',social_type='website'):
    prefix = '../' * route.count('/')
    site = profile or SITE
    navigation = ''.join(f'<a href="{prefix}{path}"' + (' aria-current="page"' if active==path else '') + f'>{name}</a>' for path,name in NAV)
    phone = site.get('phone', '+7 (902) 445-30-01')
    phone_href = 'tel:+' + ''.join(c for c in phone if c.isdigit())
    def brand_text(value, replacement):
        marker = '\x00company\x00'
        return value.replace(replacement, marker).replace('СК Орион', replacement).replace(marker, replacement)
    content = brand_text(content, e(site['company_name']))
    title = brand_text(title, site['company_name'])
    description = brand_text(description, site['company_name'])
    content = content.replace('+7 (902) 445-30-01', e(phone)).replace('tel:+79024453001', e(phone_href))
    region = site.get('region', 'Екатеринбург и Свердловская область')
    notice = site.get('emergency_notice', 'Аварийные обращения — 24/7')
    content = content.replace('Екатеринбург и Свердловская область', e(region)).replace('Екатеринбург · Свердловская область', e(region))
    content = content.replace('Аварийные обращения — 24/7', e(notice))
    if SITE_NOINDEX:
        extra_head += '<meta name="robots" content="noindex,nofollow" />'
    service = next((s for s in SERVICES if route == 'services/' + s['slug'] + '.html'), None)
    project = next((p for p in PROJECTS if route == 'works/' + p['slug'] + '.html'), None)
    share_image = share_image or (service['image'] if service else project['photos'][0]['src'] if project else page_data(route).get('image', ''))
    page_title, canonical, seo_head = metadata(route,title,description,SITE_URL,site,share_image,social_type,service)
    text = BASE.substitute(page_title=e(page_title),canonical=e(canonical),seo_head=seo_head,title=e(title),description=e(description),site_url=e(SITE_URL),route=route,prefix=prefix,navigation=navigation,phone_icon=PHONE_ICON,arrow=ARROW,content=content,dialog=dialog,body_class=body_class,preload=preload,extra_head=extra_head,company=e(site['company_name']),company_subtitle=e(site.get('company_subtitle', 'строительная компания')),region=e(region),region_short=e('Екатеринбург и область' if region == 'Екатеринбург и Свердловская область' else region),footer_description=e(site.get('footer_description', 'Монтаж, теплоизоляция и аварийные работы.')),emergency_notice=e(notice),company_upper=e(site['company_name'].upper()),phone=e(phone),phone_href=e(phone_href),extra_script=f'<script src="{prefix}works.js?v={VERSION}" defer></script>' if route=='works.html' or route.startswith('works/') else '')
    if not any(service['slug'] == 'emergency' for service in SERVICES):
        text = text.replace(prefix + 'services/emergency.html', prefix + 'contacts.html')
    if route == 'index.html':
        text = text.replace('request.html#request', '#contact')
    return '\n'.join(line.rstrip() for line in text.splitlines()) + '\n'

def render(route,title,description,content,active='',dialog='',body_class='',preload='',extra_head=''):
    data = page_data(route)
    title = data.get('seo_title') or title
    description = data.get('seo_description') or description
    target = OUTPUT_ROOT / route
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(document(route,title,description,content,active,dialog,body_class,preload,extra_head))

def read_template(name): return (ROOT/'templates'/name).read_text()


def request_form():
    import re
    template = read_template('request-form.html')
    options = '<option value="">Выберите направление</option>' + ''.join(f'<option value="{e(s["slug"])}">{e(s["title"])}</option>' for s in SERVICES)
    return re.sub(r'(<select[^>]*name="service"[^>]*>).*?(</select>)', lambda m: m[1]+options+m[2], template, flags=re.S)


def emergency_block():
    block = section_data('index.html','emergency')
    return f'<section class="emergency-section" id="emergency"><div class="emergency-content section-shell"><div class="emergency-copy"><span class="emergency-hours">24/7</span><h2>{e(block["title"])}</h2>{prose(block["body"])}{button(PHONE,"tel:+79024453001",True)}</div><div class="emergency-photo" role="img" aria-label="{e(block["title"])}" style="background-image:url(\'{e(block["image"])}\')"></div></div></section>'

def build_site():
    articles = load_articles(ARTICLE_SOURCE)
    home = page_data('index.html')
    hero = read_template('home-hero.html')
    if home['title'] != 'Монтаж и ремонт инженерных сетей':
        import re
        hero = re.sub(r'(<h1 id="hero-title">).*?(</h1>)', lambda m: m[1] + e(home['title']) + m[2], hero, flags=re.S)
    hero = hero.replace('Работаем с трубопроводами любого диаметра. Делаем теплоизоляцию инженерных систем и устраняем аварии.', e(home['intro']))
    hero = hero.replace('class="hero-photo"', 'class="hero-photo" style="background-image:url(\'' + e(home['image']) + '\')"')
    intro_data = section_data('index.html', 'intro')
    intro = '<section class="intro section-shell" id="about"><div class="section-side"><span class="section-mark"></span><span>О компании</span></div><div class="intro-main"><h2>' + e(intro_data['title']) + '</h2><div class="intro-bottom">' + prose(intro_data['body']) + '</div><a class="text-link intro-link" href="about.html">Подробнее о компании ' + ARROW + '</a></div></section>'
    service_head = section_data('index.html', 'services')
    services = '<section class="services section-shell" id="services"><div class="section-heading-row"><h2>' + e(service_head['title']) + '</h2><div class="section-heading-text">' + prose(service_head['body']) + '</div></div><div class="service-gallery">'
    for service in SERVICES[:3]:
        services += f'<article class="service-card"><div class="service-card-image"><img src="{e(service["image"])}" alt="{e(service["alt"])}" width="{service["width"]}" height="{service["height"]}" loading="lazy" decoding="async" /></div><div class="service-card-body"><h3>{e(service["title"])}</h3><p>{e(service["summary"])}</p><a class="service-card-link" href="services/{service["slug"]}.html">Подробнее об услуге {ARROW}</a></div></article>'
    services += '</div><a class="text-link section-tail" href="services.html">Все услуги ' + ARROW + '</a></section>'
    selected = ['seti-zhilogo-kompleksa', 'teplovoy-punkt', 'truboprovody-parkinga']
    selected = [slug for slug in selected if any(p['slug'] == slug for p in PROJECTS)]
    selected += [p['slug'] for p in PROJECTS if p['slug'] not in selected][:3-len(selected)]
    preview = related(selected, '', section_data('index.html','works')['title'],section_data('index.html','works')['body']).replace('<section class=', '<section id="projects" class=', 1)
    request_block = section_data('index.html','request')
    contact=f'<section class="request-layout home-request section-shell" id="contact"><div class="request-guidance"><h2>{e(request_block["title"])}</h2>{prose(request_block["body"])}<div class="request-phone"><span>Связаться напрямую</span><a href="tel:+79024453001">{PHONE}</a><p>Екатеринбург и Свердловская область.<br />Аварийные обращения — 24/7.</p></div></div>{request_form()}</section>'
    render('index.html', home['title'], home['intro'], hero+intro+services+preview+article_preview(articles)+emergency_block()+contact)

    filters=''.join(f'<button type="button" data-filter="{key}" aria-pressed="{str(key=="all").lower()}">{label}</button>' for key,label in [('all','Все работы'),*CATEGORIES.items()])
    works = heading('works.html')
    works += f'<section class="portfolio-section portfolio-index section-shell" aria-label="Каталог работ"><div class="portfolio-tools"><div class="portfolio-filters" role="group" aria-label="Направление работ" hidden>{filters}</div><p class="portfolio-total" aria-live="polite">{len(PROJECTS)} работ · {sum(len(p["photos"]) for p in PROJECTS)} фото</p></div>{project_grid(PROJECTS,eager=True)}</section>'+callout()
    render('works.html',page_data('works.html')['title'],page_data('works.html')['intro'],works,'works.html')

    for i,p in enumerate(PROJECTS):
        first=p['photos'][0]
        location=f'<p class="case-location">{e(p["location"])}</p>' if p.get('location') else ''
        main=f'''<div class="section-shell">{breadcrumb(p['title'],'../',('works.html','Наши работы'))}<section class="case-hero"><div class="case-intro"><h1>{e(p['title'])}</h1><p class="case-summary">{e(p['summary'])}</p>{location}<div class="case-meta"><span>{CATEGORIES[p['category']]}</span><a href="#gallery">{len(p['photos'])} фото в галерее</a></div>{button('Обсудить похожую задачу','../request.html?service='+p['service']+'#request')}</div><a class="case-cover" href="#gallery" aria-label="Перейти к фотографиям работы" style="--photo-position:{p['cover_position']}">{image(first,'../',True)}<span>Смотреть все фото {ARROW}</span></a></section></div>'''
        main+='<section class="case-story section-shell"><h2>О работе</h2><div class="case-description">'+prose(p['description'] if isinstance(p['description'], str) else '\n\n'.join(p['description']))+'</div><ul class="case-details">'+''.join(f'<li>{e(t)}</li>' for t in p['details'])+'</ul></section>'
        main+=f'<section class="case-gallery section-shell" id="gallery"><div class="split-heading"><h2>Фотографии работы</h2><p>Нажмите на фото, чтобы рассмотреть детали.</p></div><div class="case-photos">'
        for n,photo in enumerate(p['photos']):
            main+=f'<figure class="case-photo"><a class="work-photo" href="../{photo["src"]}" data-photo-caption="{e(photo["caption"])}" aria-label="Увеличить фото: {e(photo["caption"])}">{image(photo,"../")}<span class="work-photo-open">{EXPAND}</span></a><figcaption><span>{n+1:02d}</span>{e(photo["caption"])}</figcaption></figure>'
        main+='</div></section>'
        same=[q['slug'] for q in PROJECTS if q!=p and q['category']==p['category']][:2]
        if len(same)<2: same += [q['slug'] for q in PROJECTS if q!=p and q['slug'] not in same][:2-len(same)]
        main+=callout('../',service=p['service'])+related(same,'../','Другие работы')
        dialog=f'''<dialog class="photo-viewer" aria-labelledby="viewer-title"><div class="viewer-toolbar"><h2 id="viewer-title">{e(first['caption'])}</h2><button class="viewer-control viewer-close" type="button" aria-label="Закрыть фото" autofocus>{SVG.format('<path d="m6 6 12 12M6 18 18 6"/>')}</button></div><div class="viewer-image-wrap"><img class="viewer-image" src="../{first['small']}" alt="{e(first['caption'])}" width="{first['width']}" height="{first['height']}" loading="lazy"/><p class="viewer-error" role="status" hidden>Фото не загрузилось. Закройте просмотр и попробуйте ещё раз.</p></div><div class="viewer-bottom"><span class="viewer-count" aria-live="polite"></span><div class="viewer-navigation"><button class="viewer-control viewer-previous" type="button" aria-label="Предыдущее фото">{SVG.format('<path d="m14 5-7 7 7 7"/>')}</button><button class="viewer-control viewer-next" type="button" aria-label="Следующее фото">{SVG.format('<path d="m10 5 7 7-7 7"/>')}</button></div></div></dialog>'''
        render('works/'+p['slug']+'.html',p.get('seo_title') or p['title'],p.get('seo_description') or p['summary']+' Фотографии работы СК Орион.',main,'works.html',dialog)

    services_content = heading('services.html') + '<div class="service-directory section-shell">'
    for service in SERVICES:
        services_content += f'<article class="service-row"><a class="service-row-image" href="services/{service["slug"]}.html" tabindex="-1" aria-hidden="true"><img src="{e(service["image"])}" alt="" width="{service["width"]}" height="{service["height"]}" loading="lazy" /></a><div><h2><a href="services/{service["slug"]}.html">{e(service["title"])}</a></h2><p>{e(service["summary"])}</p><a class="text-link" href="services/{service["slug"]}.html">Подробнее об услуге {ARROW}</a></div></article>'
    services_content += '</div>' + callout()
    render('services.html',page_data('services.html')['title'],page_data('services.html')['intro'],services_content,'services.html')
    for service in SERVICES:
        main=f'<div class="section-shell">{breadcrumb(service["title"],"../",("services.html","Услуги"))}<section class="service-hero case-hero"><div class="case-intro"><h1>{e(service["title"])}</h1><div class="case-summary">{prose(service["intro"])}</div>{button("Обсудить работы","../request.html?service="+service["slug"]+"#request")}</div><div class="case-cover"><img src="../{e(service["image"])}" alt="{e(service["alt"])}" width="{service["width"]}" height="{service["height"]}" fetchpriority="high" /></div></section></div>'
        main += '<section class="service-scope section-shell"><h2>Какие задачи решаем</h2><ul>'+''.join(f'<li>{e(t)}</li>' for t in service['scope'])+'</ul></section>'
        main += f'<section class="reading-section section-shell"><h2>С чего начать</h2><div>{prose(service["prepare"])}<a class="text-link" href="../process.html">Как строится работа {ARROW}</a></div></section>'
        main += related([p['slug'] for p in PROJECTS if p.get('service') == service['slug']])+callout('../',service=service['slug'])
        render('services/'+service['slug']+'.html',service.get('seo_title') or service['title'],service.get('seo_description') or service['summary'],main,'services.html')

    story = section_data('about.html','story')
    coverage = section_data('about.html','coverage')
    about = heading('about.html')+f'<section class="about-story section-shell"><div class="about-photo"><img src="{e(story["image"])}" alt="{e(story["title"])}" width="900" height="1600" fetchpriority="high" /></div><div><h2>{e(story["title"])}</h2>{prose(story["body"])}<a class="text-link" href="works.html">Посмотреть наши работы {ARROW}</a></div></section>'
    about += f'<section class="reading-section section-shell"><h2>{e(coverage["title"])}</h2><div>{prose(coverage["body"])}</div></section>'+callout()
    render('about.html',page_data('about.html')['title'],page_data('about.html')['intro'],about,'about.html')

    process=heading('process.html')+'<section class="steps section-shell" aria-label="Этапы работы">'
    for number in range(1,5):
        block = section_data('process.html','step'+str(number))
        process += f'<article><span>{number:02d}</span><h2>{e(block["title"])}</h2><div class="step-description">{prose(block["body"])}</div></article>'
    block = section_data('process.html','prepare')
    process += f'</section><section class="reading-section section-shell"><h2>{e(block["title"])}</h2><div>{prose(block["body"])}</div></section>'+callout()
    render('process.html',page_data('process.html')['title'],page_data('process.html')['intro'],process,'process.html')

    call = section_data('contacts.html','call')
    request = section_data('contacts.html','request')
    coverage = section_data('contacts.html','coverage')
    contacts=heading('contacts.html')+f'<section class="contacts-layout section-shell"><div class="contact-primary"><h2>{e(call["title"])}</h2><a class="contact-number" href="tel:+79024453001">{PHONE}</a>{prose(call["body"])}{button("Позвонить","tel:+79024453001")}</div><div class="contact-secondary"><h2>{e(request["title"])}</h2>{prose(request["body"])}<a class="text-link" href="request.html#request">Перейти к заявке {ARROW}</a><h3>{e(coverage["title"])}</h3>{prose(coverage["body"])}</div></section>'+emergency_block()
    render('contacts.html',page_data('contacts.html')['title'],page_data('contacts.html')['intro'],contacts,'contacts.html')
    guidance = section_data('request.html','guidance')
    request = heading('request.html')+f'<section class="request-layout section-shell" id="request"><div class="request-guidance"><h2>{e(guidance["title"])}</h2>{prose(guidance["body"])}<div class="request-phone"><span>Связаться напрямую</span><a href="tel:+79024453001">{PHONE}</a><p>Аварийные обращения — 24/7.</p></div></div>{request_form()}</section>'
    render('request.html',page_data('request.html')['title'],page_data('request.html')['intro'],request)
    build_articles(articles)
    print(f'Built {8 + len(SERVICES) + len(PROJECTS) + len(articles)} static pages.')


def article_card(item, prefix='', heading='h2'):
    return f'''<article class="article-card"><a href="{prefix}articles/{item['slug']}.html"><div class="article-card-image"><img src="{prefix}{item['cover']}" alt="{e(item['cover_alt'])}" width="{item['cover_width']}" height="{item['cover_height']}" loading="lazy" decoding="async" /></div><div class="article-card-copy"><{heading}>{e(item['title'])}</{heading}><p class="article-meta"><span>{e(item['category'])}</span><span>{reading_minutes(item['body'])} мин чтения</span></p><p>{e(item['summary'])}</p><span class="article-read">Читать статью {ARROW}</span></div></a></article>'''


def article_preview(items):
    if not items:
        return ''
    block = section_data('index.html', 'articles')
    return f'<section class="article-preview section-shell"><div class="split-heading"><h2>{e(block["title"])}</h2><a class="text-link" href="articles.html">Все статьи {ARROW}</a></div>{prose(block["body"])}<div class="article-preview-grid">' + ''.join(article_card(a,heading='h3') for a in items[:3]) + '</div></section>'


def article_document(item, items=(), preview=False, profile=None):
    body, toc = render_markdown(item['body'])
    title = item['title']
    main=f'<div class="section-shell">{breadcrumb(title,"../",("articles.html","Статьи"))}<header class="article-heading"><h1>{e(title)}</h1><p class="article-standfirst">{e(item["summary"])}</p><p class="article-meta"><span>{e(item["category"])}</span><time datetime="{e(item["published_at"][:10])}">{display_date(item["published_at"])}</time><span>{reading_minutes(item["body"])} мин чтения</span></p></header><figure class="article-lead-image"><img src="../{e(item["cover"])}" alt="{e(item["cover_alt"])}" width="{item["cover_width"]}" height="{item["cover_height"]}" fetchpriority="high" /><figcaption>Фотография из портфолио СК Орион</figcaption></figure></div>'
    contents=''.join(f'<a href="#{anchor}">{e(text)}</a>' for anchor,text in toc)
    main+=f'<div class="article-layout section-shell"><aside class="article-toc"><h2>В этой статье</h2><nav aria-label="Содержание статьи">{contents}</nav><a class="article-back" href="../articles.html">Все статьи {ARROW}</a></aside><article class="article-prose">{body}</article></div>'
    main+=callout('../',title='Обсудим вашу задачу',text='Расскажите об объекте, приложите фотографии или схему — уточним состав работ.',service=item.get('service',''))
    others=[a for a in items if a['slug']!=item['slug']][:2]
    if others:
        main+='<section class="article-related section-shell"><div class="split-heading"><h2>Ещё по теме</h2><a class="text-link" href="../articles.html">Все статьи '+ARROW+'</a></div><div class="article-index-grid">'+''.join(article_card(a,'../') for a in others)+'</div></section>'
    meta = '<meta name="robots" content="noindex,nofollow" />' if preview else json_ld(article_schema(item, (profile or SITE)['company_name']))
    return document('articles/'+item['slug']+'.html',item.get('seo_title') or title,item.get('seo_description') or item['summary'],main,'articles.html',body_class='article-page',extra_head=meta,profile=profile,share_image=item['cover'],social_type='article')


def build_articles(items):
    folder=OUTPUT_ROOT/'articles'
    folder.mkdir(parents=True,exist_ok=True)
    manifest=folder/'_routes.json'
    previous=json.loads(manifest.read_text()) if manifest.exists() else []
    current=[item['slug']+'.html' for item in items]
    for old in set(previous)-set(current):
        if Path(old).name==old and old.endswith('.html'):
            (folder/old).unlink(missing_ok=True)
    for item in items:
        (folder/(item['slug']+'.html')).write_text(article_document(item,items))
    manifest.write_text(json.dumps(current,ensure_ascii=False,indent=2)+'\n')
    main=heading('articles.html')
    if items:
        first=items[0]
        main+='<section class="articles-directory section-shell" aria-label="Статьи"><div class="article-feature">'+article_card(first)+'</div><div class="article-index-grid">'+''.join(article_card(item) for item in items[1:])+'</div></section>'
    else:
        main+='<section class="articles-empty section-shell"><h2>Готовим новые материалы</h2><p>Пока можно посмотреть наши услуги и фотографии работ.</p><a class="text-link" href="services.html">Перейти к услугам '+ARROW+'</a></section>'
    main+=callout()
    render('articles.html',page_data('articles.html')['title'],page_data('articles.html')['intro'],main,'articles.html')
    urls=[]
    for file in sorted(OUTPUT_ROOT.glob('*.html'))+sorted((OUTPUT_ROOT/'services').glob('*.html'))+sorted((OUTPUT_ROOT/'works').glob('*.html'))+sorted(folder.glob('*.html')):
        relative=file.relative_to(OUTPUT_ROOT).as_posix()
        url=SITE_URL+('/' if relative=='index.html' else '/'+relative)
        lastmod=next((a['updated_at'][:10] for a in items if relative=='articles/'+a['slug']+'.html'),None)
        urls.append('<url><loc>'+xml_escape(url)+'</loc>'+('<lastmod>'+lastmod+'</lastmod>' if lastmod else '')+'</url>')
    (OUTPUT_ROOT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+'\n'.join(urls)+'\n</urlset>\n')
    (OUTPUT_ROOT/'robots.txt').write_text('User-agent: *\nAllow: /\nDisallow: /admin\nDisallow: /cms-preview\nDisallow: /api/\nDisallow: /livewire\nSitemap: '+SITE_URL+'/sitemap.xml\n')


def main():
    global OUTPUT_ROOT, ARTICLE_SOURCE, SITE, PHONE, PROJECTS, SERVICES, PAGES
    parser=argparse.ArgumentParser(description='Build public static documents. Private CMS files are never copied.')
    parser.add_argument('--output-dir',type=Path,default=ROOT)
    parser.add_argument('--articles-file',type=Path,default=ARTICLE_SOURCE)
    parser.add_argument('--site-file',type=Path,default=ROOT/'content/site.json')
    for name in ('projects', 'services', 'pages'):
        parser.add_argument('--' + name + '-file', type=Path, default=ROOT/'content'/(name + '.json'))
    args=parser.parse_args()
    OUTPUT_ROOT=args.output_dir.resolve();OUTPUT_ROOT.mkdir(parents=True,exist_ok=True)
    ARTICLE_SOURCE=args.articles_file.resolve()
    SITE=json.loads(args.site_file.read_text())
    PHONE=SITE['phone']
    PROJECTS=json.loads(args.projects_file.read_text())
    SERVICES=json.loads(args.services_file.read_text())
    PAGES=json.loads(args.pages_file.read_text())
    if not any(p.get('route') == 'index.html' for p in PAGES):
        raise ValueError('The homepage is required.')
    if args.pages_file.resolve() == (ROOT/'content/pages.json').resolve():
        page_data('index.html')['intro'] = SITE['hero_description']
    if OUTPUT_ROOT!=ROOT:
        for asset in ('styles.css','pages.css','script.js','works.js','favicon.ico','favicon.svg'):
            shutil.copy2(ROOT/asset,OUTPUT_ROOT/asset)
        shutil.copytree(ROOT/'assets',OUTPUT_ROOT/'assets',dirs_exist_ok=True)
    build_site()


if __name__=='__main__':
    main()
