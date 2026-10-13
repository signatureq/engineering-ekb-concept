#!/usr/bin/env python3
"""Build the static Pages site. Run: python3 scripts/build_site.py.
Edit content/projects.json for project names, addresses, descriptions and photos.
No runtime, dependencies or routing server required.
"""
from pathlib import Path
from string import Template
from html import escape
import json

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = json.loads((ROOT / 'content/projects.json').read_text())
BASE = Template((ROOT / 'templates/base.html').read_text())
VERSION = '20261013-pages'
PHONE = '+7 (902) 445-30-01'
SVG = '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true">{}</svg>'
ARROW = SVG.format('<path d="M5 12h14m-6-6 6 6-6 6"/>')
PHONE_ICON = SVG.format('<path d="m7 3 3 5-2.5 2.5a15 15 0 0 0 6 6L16 14l5 3v3a1 1 0 0 1-1 1C10.6 21 3 13.4 3 4a1 1 0 0 1 1-1h3Z"/>')
EXPAND = SVG.format('<path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5"/>')
NAV = [('services.html','Услуги'),('works.html','Наши работы'),('about.html','О компании'),('process.html','Как работаем'),('contacts.html','Контакты')]
CATEGORIES = {'outside':'Наружные сети','inside':'Внутренние системы','insulation':'Теплоизоляция'}
SERVICES = [
 {'slug':'pipeline-installation','title':'Монтаж трубопроводов','summary':'Новые сети, замена участков и соединение труб обычного и большого диаметра.','image':'assets/client/pipeline-installation.jpg','width':1200,'height':1600,'alt':'Сварщик соединяет трубопровод в траншее','intro':'Прокладываем наружные сети и монтируем трубопроводы внутри зданий. Работаем на новых и действующих объектах в Екатеринбурге и Свердловской области.','scope':['Монтаж и замена участков трубопровода','Сварные соединения труб обычного и большого диаметра','Разводка трубопроводов в технических помещениях','Сборка участков с запорной арматурой'], 'prepare':'Для обсуждения понадобятся назначение системы, диаметр и материал труб, протяжённость участка и условия доступа. Если есть проект или фотографии — подготовьте их к разговору.','works':['naruzhnye-seti','svarka-truboprovodov','nasosnyy-uzel']},
 {'slug':'insulation','title':'Теплоизоляция инженерных систем','summary':'Изоляция трубопроводов и оборудования с учётом условий на объекте.','image':'assets/client/pipe-insulation.jpg','width':1600,'height':1200,'alt':'Изолированные трубопроводы и манометры в тепловом пункте','intro':'Выполняем теплоизоляцию трубопроводов и оборудования в технических помещениях и на открытом воздухе. Материал и конструкцию покрытия согласовываем под конкретную систему.','scope':['Теплоизоляция прямых участков трубопровода','Изоляция поворотов, отводов и соединений','Работы с трубопроводами в тепловых пунктах','Восстановление изоляции отдельных участков'], 'prepare':'Сообщите, где проходит трубопровод, его диаметр, протяжённость и состояние существующей изоляции. Фотографии помогут понять доступ к прямым участкам, поворотам и оборудованию.','works':['teploizolyaciya-naruzhnyh-setey','teplovoy-punkt']},
 {'slug':'metering','title':'Монтаж и сборка коммерческих узлов учёта','summary':'Сборка узла, трубопроводной обвязки и арматуры под задачу на объекте.','image':'assets/client/repair-team.jpg','width':1600,'height':1200,'alt':'Рабочие собирают узел с красными трубопроводами и насосным оборудованием','intro':'Монтируем и собираем коммерческие узлы учёта. Состав оборудования, схему и объём работ согласовываем по документации и условиям технического помещения.','scope':['Сборка трубопроводной части узла','Монтаж арматуры и предусмотренного оборудования','Подключение к существующим трубопроводам','Работы в техническом помещении объекта'], 'prepare':'Подготовьте проект или схему узла, перечень оборудования и фотографии помещения. Если документации пока нет, расскажите, какая система и какие работы требуются.','works':['kommercheskiy-uzel-ucheta']},
 {'slug':'emergency','title':'Аварийные работы 24/7','summary':'Устранение повреждений и восстановление работы инженерных систем.','image':'assets/client/heat-network-chamber.jpg','width':1200,'height':1600,'alt':'Трубопровод с запорной арматурой в бетонной камере','intro':'Принимаем аварийные обращения круглосуточно в Екатеринбурге и Свердловской области. Позвоните, опишите повреждение и назовите адрес — уточним ситуацию и согласуем дальнейшие действия.','scope':['Обращения по повреждениям трубопроводов','Ремонт и замена повреждённых участков','Восстановление соединений инженерных сетей','Работы на действующих объектах'], 'prepare':'При звонке сообщите адрес, тип системы, характер повреждения и возможность доступа. Сроки и порядок работ определяем после уточнения ситуации.','works':[]}
]

def e(text): return escape(str(text), quote=True)
def button(text, href, light=False):
    return f'<a class="button {"button-light" if light else "button-primary"}" href="{e(href)}">{e(text)} {ARROW}</a>'
def image(photo, prefix='', eager=False, card=False):
    sizes = '(max-width: 650px) 100vw, (max-width: 1000px) 50vw, 33vw' if card else '(max-width: 850px) 100vw, 55vw'
    return f'<img src="{prefix}{photo["src"]}" srcset="{prefix}{photo["small"]} {photo["small_width"]}w, {prefix}{photo["src"]} {photo["width"]}w" sizes="{sizes}" width="{photo["width"]}" height="{photo["height"]}" alt="{e(photo["caption"])}" loading="{"eager" if eager else "lazy"}" decoding="async" {"fetchpriority=\"high\"" if eager else ""} />'
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
def related(slugs,prefix='../',title='Работы по этому направлению'):
    ps = [p for slug in slugs for p in PROJECTS if p['slug']==slug]
    return f'<section class="portfolio-section section-shell"><div class="split-heading"><h2>{title}</h2><a class="text-link" href="{prefix}works.html">Все работы {ARROW}</a></div>{project_grid(ps,prefix)}</section>' if ps else ''
def render(route,title,description,content,active='',dialog='',body_class='',preload=''):
    prefix = '../' * route.count('/')
    navigation = ''.join(f'<a href="{prefix}{path}"' + (' aria-current="page"' if active==path else '') + f'>{name}</a>' for path,name in NAV)
    text = BASE.substitute(title=e(title),description=e(description),route=route,prefix=prefix,navigation=navigation,phone_icon=PHONE_ICON,arrow=ARROW,content=content,dialog=dialog,body_class=body_class,preload=preload,extra_script=f'<script src="{prefix}works.js?v={VERSION}" defer></script>' if route=='works.html' or route.startswith('works/') else '')
    if route == 'index.html':
        text = text.replace('request.html#request', '#contact')
    target=ROOT / route
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text('\n'.join(line.rstrip() for line in text.splitlines()) + '\n')

def read_template(name): return (ROOT/'templates'/name).read_text()

# Home retains the existing visual identity and introduces the new page routes.
hero=read_template('home-hero.html').replace('href="#contact"','href="request.html#request"')
intro=read_template('home-intro.html').replace('</div>\n      </section>','<a class="text-link intro-link" href="about.html">Подробнее о компании '+ARROW+'</a></div>\n      </section>')
services=read_template('home-services.html')
for service in SERVICES[:3]:
    services=services.replace('href="#contact">Обсудить работы',f'href="services/{service["slug"]}.html">Подробнее об услуге',1)
services=services.replace('</section>','<a class="text-link section-tail" href="services.html">Все услуги '+ARROW+'</a></section>')
preview = related(['seti-zhilogo-kompleksa','teplovoy-punkt','truboprovody-parkinga'],'','Наши работы').replace('<section class=','<section id="projects" class=',1)
contact=f'<section class="request-layout home-request section-shell" id="contact"><div class="request-guidance"><h2>Оставьте заявку</h2><p>Расскажите, какие работы нужны и где находится объект. Можно приложить фотографии, чертежи или техническое задание.</p><div class="request-phone"><span>Связаться напрямую</span><a href="tel:+79024453001">{PHONE}</a><p>Екатеринбург и Свердловская область.<br />Аварийные обращения — 24/7.</p></div></div>{read_template("request-form.html")}</section>'

render('index.html','Монтаж и ремонт инженерных сетей','СК Орион: монтаж трубопроводов, теплоизоляция, узлы учёта и аварийные работы в Екатеринбурге и Свердловской области.',hero+intro+services+preview+read_template('home-emergency.html')+contact,preload='<link rel="preload" href="assets/client/pipeline-welding.jpg" as="image" fetchpriority="high" />')

# Portfolio index: each card opens a complete document, not a single photo.
filters=''.join(f'<button type="button" data-filter="{key}" aria-pressed="{str(key=="all").lower()}">{label}</button>' for key,label in [('all','Все работы'),*CATEGORIES.items()])
works = page_head('Наши работы','Наружные сети, технические помещения и детали монтажа. Откройте работу, чтобы посмотреть описание и все фотографии.')
works += f'<section class="portfolio-section portfolio-index section-shell" aria-label="Каталог работ"><div class="portfolio-tools"><div class="portfolio-filters" role="group" aria-label="Направление работ" hidden>{filters}</div><p class="portfolio-total" aria-live="polite">9 работ · 30 фото</p></div>{project_grid(PROJECTS,eager=True)}</section>'+callout()
render('works.html','Наши работы','Фотографии работ СК Орион: наружные сети, трубопроводы, теплоизоляция, насосные узлы и коммерческие узлы учёта.',works,'works.html')

for i,p in enumerate(PROJECTS):
    first=p['photos'][0]
    location=f'<p class="case-location">{e(p["location"])}</p>' if p.get('location') else ''
    main=f'''<div class="section-shell">{breadcrumb(p['title'],'../',('works.html','Наши работы'))}<section class="case-hero"><div class="case-intro"><h1>{e(p['title'])}</h1><p class="case-summary">{e(p['summary'])}</p>{location}<div class="case-meta"><span>{CATEGORIES[p['category']]}</span><a href="#gallery">{len(p['photos'])} фото в галерее</a></div>{button('Обсудить похожую задачу','../request.html?service='+p['service']+'#request')}</div><a class="case-cover" href="#gallery" aria-label="Перейти к фотографиям работы" style="--photo-position:{p['cover_position']}">{image(first,'../',True)}<span>Смотреть все фото {ARROW}</span></a></section></div>'''
    main+='<section class="case-story section-shell"><h2>О работе</h2><div class="case-description">'+''.join(f'<p>{e(t)}</p>' for t in p['description'])+'</div><ul class="case-details">'+''.join(f'<li>{e(t)}</li>' for t in p['details'])+'</ul></section>'
    main+=f'<section class="case-gallery section-shell" id="gallery"><div class="split-heading"><h2>Фотографии работы</h2><p>Нажмите на фото, чтобы рассмотреть детали.</p></div><div class="case-photos">'
    for n,photo in enumerate(p['photos']):
        main+=f'<figure class="case-photo"><a class="work-photo" href="../{photo["src"]}" data-photo-caption="{e(photo["caption"])}" aria-label="Увеличить фото: {e(photo["caption"])}">{image(photo,"../")}<span class="work-photo-open">{EXPAND}</span></a><figcaption><span>{n+1:02d}</span>{e(photo["caption"])}</figcaption></figure>'
    main+='</div></section>'
    same=[q['slug'] for q in PROJECTS if q!=p and q['category']==p['category']][:2]
    if len(same)<2: same += [q['slug'] for q in PROJECTS if q!=p and q['slug'] not in same][:2-len(same)]
    main+=callout('../',service=p['service'])+related(same,'../','Другие работы')
    dialog=f'''<dialog class="photo-viewer" aria-labelledby="viewer-title"><div class="viewer-toolbar"><h2 id="viewer-title">{e(first['caption'])}</h2><button class="viewer-control viewer-close" type="button" aria-label="Закрыть фото" autofocus>{SVG.format('<path d="m6 6 12 12M6 18 18 6"/>')}</button></div><div class="viewer-image-wrap"><img class="viewer-image" src="../{first['small']}" alt="{e(first['caption'])}" width="{first['width']}" height="{first['height']}" loading="lazy"/><p class="viewer-error" role="status" hidden>Фото не загрузилось. Закройте просмотр и попробуйте ещё раз.</p></div><div class="viewer-bottom"><span class="viewer-count" aria-live="polite"></span><div class="viewer-navigation"><button class="viewer-control viewer-previous" type="button" aria-label="Предыдущее фото">{SVG.format('<path d="m14 5-7 7 7 7"/>')}</button><button class="viewer-control viewer-next" type="button" aria-label="Следующее фото">{SVG.format('<path d="m10 5 7 7-7 7"/>')}</button></div></div></dialog>'''
    render('works/'+p['slug']+'.html',p['title'],p['summary']+' Фотографии работы СК Орион.',main,'works.html',dialog)

# Service routes offer real scope and a route into related photography.
services_content=page_head('Услуги','От наружной трассы до оборудования внутри здания. Выберите направление, чтобы узнать о работах и посмотреть фотографии.')+'<div class="service-directory section-shell">'
for s in SERVICES:
    services_content+=f'''<article class="service-row"><a class="service-row-image" href="services/{s['slug']}.html" tabindex="-1" aria-hidden="true"><img src="{s['image']}" alt="" width="{s['width']}" height="{s['height']}" loading="lazy" /></a><div><h2><a href="services/{s['slug']}.html">{s['title']}</a></h2><p>{s['summary']}</p><a class="text-link" href="services/{s['slug']}.html">Подробнее об услуге {ARROW}</a></div></article>'''
services_content+='</div>'+callout()
render('services.html','Услуги','Монтаж трубопроводов, теплоизоляция, коммерческие узлы учёта и аварийные работы 24/7. СК Орион, Екатеринбург.',services_content,'services.html')
for s in SERVICES:
    main=f'''<div class="section-shell">{breadcrumb(s['title'],'../',('services.html','Услуги'))}<section class="service-hero case-hero"><div class="case-intro"><h1>{s['title']}</h1><p class="case-summary">{s['intro']}</p>{button('Позвонить '+PHONE,'tel:+79024453001') if s['slug']=='emergency' else button('Обсудить работы','../request.html?service='+s['slug']+'#request')}</div><div class="case-cover"><img src="../{s['image']}" alt="{s['alt']}" width="{s['width']}" height="{s['height']}" fetchpriority="high" /></div></section></div>'''
    main+='<section class="service-scope section-shell"><h2>Какие задачи решаем</h2><ul>'+''.join(f'<li>{e(t)}</li>' for t in s['scope'])+'</ul></section>'
    main+=f'<section class="reading-section section-shell"><h2>С чего начать</h2><div><p>{s["prepare"]}</p><p>Объём, стоимость и сроки согласуем до начала работ.</p><a class="text-link" href="../process.html">Как строится работа {ARROW}</a></div></section>'
    main+=related(s['works'])+callout('../',service=s['slug'])
    render('services/'+s['slug']+'.html',s['title'],s['summary']+' СК Орион — Екатеринбург и Свердловская область.',main,'services.html')

about=page_head('О компании','СК Орион — команда по монтажу, теплоизоляции и ремонту инженерных систем в Екатеринбурге и Свердловской области.')
about+=f'''<section class="about-story section-shell"><div class="about-photo"><img src="assets/projects/seti-zhilogo-kompleksa/01.webp" alt="Монтажники работают с трубопроводами между жилыми зданиями" width="900" height="1600" fetchpriority="high" /></div><div><h2>Работаем с сетью целиком — и с отдельным участком.</h2><p>Прокладываем трубопроводы, собираем узлы, изолируем трубы и оборудование. Берём задачи на новых и действующих объектах.</p><p>Состав работ определяем по задаче и условиям объекта. До начала обсуждаем доступ, материалы и оборудование, объём и порядок выполнения.</p><a class="text-link" href="works.html">Посмотреть наши работы {ARROW}</a></div></section>'''
about+='<section class="reading-section section-shell"><h2>Где и с чем работаем</h2><div><p>Екатеринбург и Свердловская область. Наружные инженерные сети, технические помещения, тепловые пункты и трубопроводы внутри зданий.</p><p>Для плановых работ свяжитесь с нами и расскажите о задаче. Аварийные обращения принимаем круглосуточно.</p></div></section>'+callout()
render('about.html','О компании','СК Орион — монтаж, изоляция и ремонт инженерных сетей в Екатеринбурге и Свердловской области.',about,'about.html')

process=page_head('Как работаем','Начинаем с вашей задачи и условий на объекте. Объём, порядок и сроки обсуждаем до начала работ.')
steps=[('Расскажите об объекте','Позвоните и сообщите, какие работы нужны и где находится объект. Если есть фотографии, чертежи или техническое задание, подготовьте их для обсуждения.'),('Уточняем объём и условия','Разбираем состав работ, состояние системы и возможность доступа. Уточняем, какие материалы и оборудование нужны, требуется ли осмотр объекта.'),('Согласуем работы','Обсуждаем стоимость, сроки, последовательность и условия выполнения. Фиксируем согласованный объём до начала.'),('Выполняем и передаём результат','Проводим согласованные работы на объекте. Порядок приёмки и необходимую документацию обсуждаем в рамках конкретной задачи.')]
process+='<section class="steps section-shell" aria-label="Этапы работы">'+''.join(f'<article><span>{i+1:02d}</span><h2>{title}</h2><p>{text}</p></article>' for i,(title,text) in enumerate(steps))+'</section>'
process+='<section class="reading-section section-shell"><h2>Что подготовить</h2><div><ul class="plain-list"><li>Адрес и контакт человека на объекте</li><li>Краткое описание задачи и желаемые сроки</li><li>Фотографии участка или оборудования</li><li>Проект, схему или техническое задание, если они есть</li></ul><p>Можно начать со звонка, даже если пока нет всех материалов.</p></div></section>'+callout()
render('process.html','Как работаем','Этапы работы с СК Орион: обращение, уточнение задачи, согласование и выполнение работ на объекте.',process,'process.html')

contacts=page_head('Контакты','Обсудим плановые работы или аварийную ситуацию. Работаем в Екатеринбурге и Свердловской области.')
contacts+=f'''<section class="contacts-layout section-shell"><div class="contact-primary"><h2>Позвоните нам</h2><a class="contact-number" href="tel:+79024453001">{PHONE}</a><p>Расскажите, какая система и какие работы нужны.<br />Аварийные обращения принимаем 24/7.</p>{button('Позвонить','tel:+79024453001')}</div><div class="contact-secondary"><h2>Подготовить заявку</h2><p>На странице заявки можно указать задачу и выбрать направление работ. Приём заявок через форму пока не подключён — сейчас свяжитесь с нами по телефону.</p><a class="text-link" href="request.html#request">Перейти к заявке {ARROW}</a><h3>Зона работы</h3><p>Екатеринбург и Свердловская область. Адрес объекта и возможность выезда уточним при обращении.</p></div></section>'''
contacts+=read_template('home-emergency.html').replace('id="emergency"','id="emergency-contact"')
render('contacts.html','Контакты',f'Телефон СК Орион: {PHONE}. Екатеринбург и Свердловская область. Аварийные обращения круглосуточно.',contacts,'contacts.html')
request=page_head('Заявка на работы','Расскажите об объекте и задаче. Для срочного обращения позвоните: +7 (902) 445-30-01.')
request+=f'''<section class="request-layout section-shell" id="request"><div class="request-guidance"><h2>Что нужно сделать?</h2><p>Укажите направление работ, адрес объекта и удобное время для связи. Фотографии и схемы помогут понять задачу.</p><div class="request-phone"><span>Связаться напрямую</span><a href="tel:+79024453001">{PHONE}</a><p>Аварийные обращения — 24/7.</p></div></div>{read_template('request-form.html')}</section>'''
render('request.html','Заявка на работы','Обсудите монтаж, ремонт, теплоизоляцию или узел учёта с СК Орион. Контактный телефон: '+PHONE+'.',request)
print('Built 20 static pages: 7 main, 4 services, 9 works.')
