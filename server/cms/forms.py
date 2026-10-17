from io import BytesIO
from pathlib import Path
from django import forms
from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError
from .models import Article
from .editor_content import fill_automatic_fields
from scripts.article_content import render_markdown


class ArticleTextWidget(forms.Textarea):
    template_name = 'cms/article_text.html'
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['widget']['attrs'].pop('required', None)
        context['widget']['formatted_text'] = render_markdown(value or '')[0]
        return context


def library_choices():
    return [('assets/client/pipeline-installation.jpg', 'Монтаж трубопроводов'), ('assets/client/pipeline-welding.jpg', 'Сварка труб'), ('assets/client/repair-team.jpg', 'Коммерческий узел учёта'), ('assets/client/pipe-insulation.jpg', 'Теплоизоляция в помещении'), ('assets/client/heat-network-chamber.jpg', 'Камера тепловой сети'), ('assets/projects/nasosnyy-uzel/01.webp', 'Насосный узел'), ('assets/projects/naruzhnye-seti/01.webp', 'Наружная трасса'), ('assets/projects/teploizolyaciya-naruzhnyh-setey/01.webp', 'Наружная теплоизоляция')]


class ArticleForm(forms.ModelForm):
    cover = forms.ChoiceField(label='Или фото из наших работ', choices=library_choices)

    class Meta:
        model = Article
        fields = ('title', 'body', 'cover_upload', 'cover', 'seo_title', 'seo_description')
        labels = {'title': 'Название статьи', 'body': 'Текст статьи', 'cover_upload': 'Загрузить фотографию', 'seo_title': 'Название в поиске', 'seo_description': 'Описание в поиске'}
        help_texts = {'body': 'Пишите как в обычном документе. Выделение и подзаголовки добавляются кнопками.', 'cover_upload': 'Необязательно. Если своей фотографии нет, используем выбранное фото из работ.', 'seo_title': 'Необязательно. Если оставить пустым, используем название статьи.', 'seo_description': 'Необязательно. Если оставить пустым, составим описание из текста статьи.'}
        widgets = {'body': ArticleTextWidget(), 'seo_description': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cover_upload'].widget.template_name = 'cms/cover_input.html'

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('title') and cleaned.get('body'):
            fill_automatic_fields(self.instance, cleaned['title'], cleaned['body'])
        return cleaned

    def clean_cover_upload(self):
        uploaded = self.cleaned_data.get('cover_upload')
        if not uploaded or not hasattr(uploaded, 'content_type'):
            return uploaded
        if uploaded.size > 5 * 1024 * 1024:
            raise forms.ValidationError('Фотография больше 5 МБ. Уменьшите файл и загрузите снова.')
        try:
            im = Image.open(uploaded)
            if im.format not in ('JPEG', 'PNG', 'WEBP') or im.width * im.height > 16000000:
                raise forms.ValidationError('Нужен JPG, PNG или WebP до 16 мегапикселей.')
            im = ImageOps.exif_transpose(im).convert('RGB')
            im.thumbnail((1800, 1800))
            output = BytesIO(); im.save(output, 'WEBP', quality=84)
            return ContentFile(output.getvalue(), name=Path(uploaded.name).stem + '.webp')
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
            raise forms.ValidationError('Не удалось прочитать фотографию. Загрузите другой JPG, PNG или WebP.')
