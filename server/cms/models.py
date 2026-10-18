from pathlib import Path
import uuid
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from scripts.article_content import CATEGORIES, SLUG


def upload_path(instance, filename):
    return 'articles/' + uuid.uuid4().hex + Path(filename).suffix.lower()


class Article(models.Model):
    title = models.CharField('Заголовок', max_length=200)
    slug = models.SlugField('Адрес страницы', max_length=140, unique=True, help_text='Латинские буквы, цифры и дефисы. После первой публикации адрес закрепляется.')
    category = models.CharField('Тема', max_length=60, choices=[(v, v) for v in CATEGORIES])
    summary = models.TextField('Краткое описание', max_length=400, help_text='Показывается в списке статей и перед основным текстом.')
    body = models.TextField('Текст статьи', max_length=100000, help_text='Абзацы отделяются пустой строкой. Кнопки над текстом добавляют заголовки, списки и ссылки.')
    cover = models.CharField('Обложка из портфолио', max_length=240, default='assets/client/pipeline-installation.jpg')
    cover_upload = models.ImageField('Загрузить свою обложку', upload_to=upload_path, blank=True, help_text='JPG, PNG или WebP до 5 МБ. Загруженная фотография заменит обложку из портфолио.')
    cover_alt = models.CharField('Описание изображения', max_length=240, help_text='Коротко опишите, что изображено на фотографии.')
    cover_width = models.PositiveIntegerField(default=1200, editable=False)
    cover_height = models.PositiveIntegerField(default=1600, editable=False)
    seo_title = models.CharField('Заголовок для поиска', max_length=100, blank=True, help_text='Можно оставить пустым — будет использован заголовок статьи.')
    seo_description = models.CharField('Описание для поиска', max_length=200, blank=True, help_text='Можно оставить пустым — будет использовано краткое описание.')
    service = models.CharField('Связанная услуга', max_length=40, blank=True, choices=[('pipeline-installation', 'Монтаж трубопроводов'), ('insulation', 'Теплоизоляция'), ('metering', 'Узлы учёта'), ('emergency', 'Аварийные работы')])
    featured = models.BooleanField('Показывать первой', default=False)
    published_payload = models.JSONField(null=True, blank=True, editable=False)
    first_published_at = models.DateTimeField(null=True, editable=False)
    last_published_at = models.DateTimeField('Последняя публикация', null=True, editable=False)
    updated_at = models.DateTimeField('Изменено', auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Статья'
        verbose_name_plural = 'Статьи'
        ordering = ['-updated_at']

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        if not SLUG.fullmatch(self.slug or ''):
            raise ValidationError({'slug': 'Используйте латинские буквы, цифры и одиночные дефисы между словами.'})
        if self.pk:
            previous = Article.objects.filter(pk=self.pk).values('slug', 'first_published_at').first()
            if previous and previous['first_published_at'] and previous['slug'] != self.slug:
                raise ValidationError({'slug': 'Адрес опубликованной статьи менять нельзя: на него уже могут вести ссылки.'})
        if not self.title.strip() or not self.summary.strip() or not self.body.strip():
            raise ValidationError('Заполните заголовок, краткое описание и текст статьи.')
        cover = Path(self.cover)
        if cover.is_absolute() or '..' in cover.parts or not str(cover).startswith('assets/'):
            raise ValidationError({'cover': 'Выберите изображение из библиотеки сайта.'})

    def get_absolute_url(self):
        return '/articles/' + self.slug + '.html'


class SiteSettings(models.Model):
    company_name = models.CharField('Название в шапке и подвале', max_length=60, default='СК Орион')
    phone = models.CharField('Контактный телефон', max_length=30, default='+7 (902) 445-30-01', validators=[RegexValidator(r'^\+?[0-9()\s-]{10,30}$', 'Введите телефон с кодом страны, например +7 (902) 445-30-01.')])
    company_subtitle = models.CharField('Подпись под логотипом', max_length=100, default='строительная компания')
    region = models.CharField('Где работаем', max_length=200, default='Екатеринбург и Свердловская область')
    footer_description = models.CharField('Коротко о компании внизу сайта', max_length=300, default='Монтаж, теплоизоляция и аварийные работы.')
    emergency_notice = models.CharField('Подпись об аварийных обращениях', max_length=200, default='Аварийные обращения — 24/7')
    hero_description = models.TextField('Текст на первом экране главной', max_length=500, default='Работаем с трубопроводами любого диаметра. Делаем теплоизоляцию инженерных систем и устраняем аварии.')
    published_payload = models.JSONField(null=True, blank=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Настройки сайта'
        verbose_name_plural = 'Настройки сайта'

    def __str__(self):
        return 'Контакты компании'

    def clean(self):
        super().clean()
        if not self.pk and SiteSettings.objects.exists():
            raise ValidationError('Настройки сайта уже созданы.')
        digits = ''.join(c for c in self.phone if c.isdigit())
        if not 10 <= len(digits) <= 15:
            raise ValidationError({'phone': 'Проверьте телефон: от 10 до 15 цифр вместе с кодом страны.'})

    def as_dict(self):
        return {name: getattr(self, name) for name in ('company_name', 'phone', 'hero_description', 'company_subtitle', 'region', 'footer_description', 'emergency_notice')}


def content_upload_path(instance, filename):
    return 'content/' + uuid.uuid4().hex + '.webp'


class WebsiteContent(models.Model):
    title = models.CharField('Название', max_length=200)
    seo_title = models.CharField('Название в поиске', max_length=100, blank=True, help_text='Необязательно. Если оставить пустым, используем название страницы.')
    seo_description = models.CharField('Описание в поиске', max_length=200, blank=True, help_text='Необязательно. Если оставить пустым, составим описание автоматически.')
    published_payload = models.JSONField(null=True, blank=True, editable=False)
    first_published_at = models.DateTimeField(null=True, editable=False)
    updated_at = models.DateTimeField('Изменено', auto_now=True)

    class Meta:
        abstract = True


class SitePage(WebsiteContent):
    route = models.CharField(max_length=80, unique=True, editable=False)
    label = models.CharField('Страница', max_length=80, editable=False)
    intro = models.TextField('Вступление', max_length=2000, blank=True)
    image = models.CharField(max_length=240, blank=True, editable=False)
    image_upload = models.ImageField('Заменить фотографию', upload_to=content_upload_path, blank=True)

    class Meta:
        verbose_name = 'Страница'
        verbose_name_plural = 'Страницы'
        ordering = ['pk']

    def __str__(self):
        return self.label

    def get_absolute_url(self):
        return '/' + self.route


class PageSection(models.Model):
    page = models.ForeignKey(SitePage, on_delete=models.CASCADE, related_name='sections')
    key = models.CharField(max_length=60, editable=False)
    title = models.CharField('Заголовок блока', max_length=200, blank=True)
    body = models.TextField('Текст блока', max_length=20000, blank=True)
    image = models.CharField(max_length=240, blank=True, editable=False)
    image_upload = models.ImageField('Заменить фотографию', upload_to=content_upload_path, blank=True)
    position = models.PositiveIntegerField(default=0, editable=False)

    class Meta:
        ordering = ['position', 'pk']
        constraints = [models.UniqueConstraint(fields=['page', 'key'], name='unique_page_section')]
        verbose_name = 'Блок страницы'
        verbose_name_plural = 'Блоки страницы'

    def __str__(self):
        return self.title or 'Блок страницы'


class Service(WebsiteContent):
    slug = models.SlugField(max_length=140, unique=True, editable=False)
    summary = models.TextField('Краткое описание', max_length=500)
    intro = models.TextField('Описание услуги', max_length=20000)
    scope = models.TextField('Какие задачи решаем', max_length=4000, help_text='Каждый пункт — с новой строки.')
    prepare = models.TextField('Что подготовить для обсуждения', max_length=6000)
    image = models.CharField(max_length=240, default='assets/client/pipeline-installation.jpg', editable=False)
    image_upload = models.ImageField('Загрузить фотографию', upload_to=content_upload_path, blank=True)
    position = models.PositiveIntegerField('Место в списке', default=10, help_text='Меньшее число — ближе к началу.')

    class Meta:
        verbose_name = 'Услуга'
        verbose_name_plural = 'Услуги'
        ordering = ['position', 'pk']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return '/services/' + self.slug + '.html'

    def clean(self):
        super().clean()
        check_stable_address(self)


class Project(WebsiteContent):
    slug = models.SlugField(max_length=140, unique=True, editable=False)
    summary = models.TextField('Краткое описание', max_length=700)
    description = models.TextField('О работе', max_length=30000)
    details = models.TextField('Что сделано', max_length=5000, blank=True, help_text='Каждый пункт — с новой строки. Можно оставить пустым.')
    location = models.CharField('Адрес или название объекта', max_length=240, blank=True, help_text='Необязательно. Укажите, если можно публиковать.')
    category = models.CharField('Направление', max_length=20, choices=[('outside', 'Наружные сети'), ('inside', 'Внутренние системы'), ('insulation', 'Теплоизоляция')], default='inside')
    service = models.ForeignKey(Service, verbose_name='Услуга', on_delete=models.SET_NULL, blank=True, null=True)
    position = models.PositiveIntegerField('Место в списке', default=10, help_text='Меньшее число — ближе к началу.')

    class Meta:
        verbose_name = 'Работа'
        verbose_name_plural = 'Наши работы'
        ordering = ['position', 'pk']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return '/works/' + self.slug + '.html'

    def clean(self):
        super().clean()
        check_stable_address(self)


class ProjectPhoto(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='photos')
    caption = models.CharField('Подпись к фотографии', max_length=240, blank=True, help_text='Необязательно. Без подписи используем название работы.')
    image_upload = models.ImageField('Фотография', upload_to=content_upload_path, blank=True)
    source = models.JSONField(default=dict, editable=False)
    position = models.PositiveIntegerField('Место в галерее', default=10, help_text='Первая фотография — обложка работы.')

    class Meta:
        ordering = ['position', 'pk']
        verbose_name = 'Фотография'
        verbose_name_plural = 'Фотографии работы'

    def __str__(self):
        return self.caption or 'Фотография работы'

    def clean(self):
        super().clean()
        if not self.image_upload and not self.source.get('src'):
            raise ValidationError({'image_upload': 'Добавьте фотографию.'})


def check_stable_address(instance):
    if instance.pk:
        old = type(instance).objects.filter(pk=instance.pk).values('slug', 'first_published_at').first()
        if old and old['first_published_at'] and old['slug'] != instance.slug:
            raise ValidationError('Адрес уже опубликованной страницы менять нельзя.')


class ContentImport(models.Model):
    key = models.CharField(max_length=60, unique=True, editable=False)

    class Meta:
        default_permissions = ()
