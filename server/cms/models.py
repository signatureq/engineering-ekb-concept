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
    hero_description = models.TextField('Текст на первом экране главной', max_length=500, default='Работаем с трубопроводами обычного и большого диаметра. Делаем теплоизоляцию инженерных систем и устраняем аварии.')
    published_payload = models.JSONField(null=True, blank=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Настройки сайта'
        verbose_name_plural = 'Настройки сайта'

    def __str__(self):
        return 'Контакты и первый экран'

    def clean(self):
        super().clean()
        if not self.pk and SiteSettings.objects.exists():
            raise ValidationError('Настройки сайта уже созданы.')
        digits = ''.join(c for c in self.phone if c.isdigit())
        if not 10 <= len(digits) <= 15:
            raise ValidationError({'phone': 'Проверьте телефон: от 10 до 15 цифр вместе с кодом страны.'})

    def as_dict(self):
        return {'company_name': self.company_name, 'phone': self.phone, 'hero_description': self.hero_description}
