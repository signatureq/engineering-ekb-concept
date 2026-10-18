import logging
from django.contrib import admin, messages
from django.db import transaction
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html
from .forms import ArticleForm
from .models import Article, SiteSettings
from .publishing import publish_article, unpublish_article, publish_settings, PublicationError

logger = logging.getLogger(__name__)
admin.site.site_header = 'СК Орион — управление сайтом'
admin.site.site_title = 'СК Орион · редактор'
admin.site.index_title = 'Управление сайтом'
admin.site.site_url = '/'
admin.site.enable_nav_sidebar = False


class PublicationFilter(admin.SimpleListFilter):
    title = 'Публикация'
    parameter_name = 'published'
    def lookups(self, request, model_admin):
        return [('yes', 'На сайте'), ('no', 'Черновики')]
    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(published_payload__isnull=False)
        if self.value() == 'no':
            return queryset.filter(published_payload__isnull=True)
        return queryset


def after_commit(request, operation, success):
    def run():
        try:
            operation()
        except PublicationError as error:
            messages.error(request, str(error) + ' Черновик сохранён; предыдущая версия сайта продолжает работать.')
        except Exception:
            logger.exception('Publication failed')
            messages.error(request, 'Публикация не выполнена. Черновик сохранён, предыдущая версия сайта продолжает работать. Повторите публикацию; если ошибка повторяется, проверьте журнал сервера.')
        else:
            messages.success(request, success)
    transaction.on_commit(run)


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    view_on_site = False
    form = ArticleForm
    list_display = ('title', 'publication_status', 'updated_at', 'published_link')
    list_filter = (PublicationFilter,)
    show_facets = admin.ShowFacets.NEVER
    search_fields = ('title', 'summary', 'body')
    list_per_page = 25
    readonly_fields = ('publication_status', 'cover_preview')
    fieldsets = [
        (None, {'fields': ('title', 'body')}),
        ('Фотография', {'fields': ('cover_preview', 'cover_upload', 'cover')}),
        ('Дополнительно — вид в поиске', {'fields': ('seo_title', 'seo_description'), 'classes': ('collapse',)}),
    ]
    change_form_template = 'admin/cms/article/change_form.html'
    change_list_template = 'admin/cms/article/change_list.html'

    def changelist_view(self, request, extra_context=None):
        return super().changelist_view(request, extra_context={**(extra_context or {}), 'title': 'Статьи'})

    class Media:
        css = {'all': ('cms/vendor/quill.core.css',)}
        js = ('cms/vendor/quill.js', 'cms/vendor/turndown.js', 'cms/editor.js?v=20261019-content')

    @admin.display(description='Состояние')
    def publication_status(self, obj):
        if not obj or not obj.pk or not obj.published_payload:
            return 'Черновик'
        snapshot = obj.published_payload
        changed = any(getattr(obj, name) != snapshot.get(name) for name in ('title', 'summary', 'body', 'category', 'seo_title', 'seo_description', 'cover_alt', 'service', 'featured'))
        from pathlib import Path
        current_cover = 'assets/uploads/' + Path(obj.cover_upload.name).name if obj.cover_upload else obj.cover
        changed = changed or current_cover != snapshot.get('cover')
        return 'Есть неопубликованные правки' if changed else 'Опубликовано'

    @admin.display(description='На сайте')
    def published_link(self, obj):
        return format_html('<a href="{}" target="_blank" rel="noopener">Открыть</a>', obj.get_absolute_url()) if obj.published_payload else '—'

    @admin.display(description='Текущая обложка')
    def cover_preview(self, obj):
        if not obj or not obj.pk:
            return 'Обложку можно посмотреть после сохранения статьи.'
        return format_html('<img class="cms-cover-preview" src="{}" alt="{}" />', reverse('article-cover', args=[obj.pk]), obj.cover_alt)

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj) and not (obj and obj.published_payload)

    def get_actions(self, request):
        # Deleting a live article requires an explicit unpublish first.
        actions = super().get_actions(request)
        actions.pop('delete_selected', None)
        return actions

    def render_change_form(self, request, context, *args, **kwargs):
        context['cms_published'] = bool(context.get('original') and context['original'].published_payload)
        context['title'] = 'Редактирование статьи' if context.get('original') else 'Новая статья'
        return super().render_change_form(request, context, *args, **kwargs)

    def publication_response(self, request, obj):
        if '_publish' in request.POST:
            after_commit(request, lambda: publish_article(obj.pk), 'Статья опубликована. Страницы и карта сайта обновлены.')
        elif '_unpublish' in request.POST:
            after_commit(request, lambda: unpublish_article(obj.pk), 'Статья снята с публикации и сохранена как черновик.')
        elif '_preview' in request.POST:
            return HttpResponseRedirect(reverse('article-preview', args=[obj.pk]))
        else:
            return None
        return HttpResponseRedirect(reverse('admin:cms_article_change', args=[obj.pk]))

    def response_add(self, request, obj, post_url_continue=None):
        return self.publication_response(request, obj) or self.saved_response(request, obj)

    def response_change(self, request, obj):
        return self.publication_response(request, obj) or self.saved_response(request, obj)

    def saved_response(self, request, obj):
        messages.success(request, 'Статья сохранена. Нажмите «Опубликовать», когда она будет готова для сайта.')
        return HttpResponseRedirect(reverse('admin:cms_article_change', args=[obj.pk]))


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fields = ('company_name', 'company_subtitle', 'phone', 'region', 'emergency_notice', 'footer_description')
    change_form_template = 'admin/cms/company_change_form.html'
    def changelist_view(self, request, extra_context=None):
        profile = SiteSettings.objects.first()
        if profile:
            return HttpResponseRedirect(reverse('admin:cms_sitesettings_change', args=[profile.pk]))
        return super().changelist_view(request, extra_context)
    def render_change_form(self, request, context, *args, **kwargs):
        context['title'] = 'Контакты компании'
        return super().render_change_form(request, context, *args, **kwargs)
    def has_add_permission(self, request):
        return not SiteSettings.objects.exists() and super().has_add_permission(request)
    def has_delete_permission(self, request, obj=None):
        return False
    def response_change(self, request, obj):
        after_commit(request, lambda: publish_settings(obj.pk), 'Название и телефон опубликованы на всём сайте.')
        return super().response_change(request, obj)
    def response_add(self, request, obj, post_url_continue=None):
        after_commit(request, lambda: publish_settings(obj.pk), 'Настройки сайта опубликованы.')
        return super().response_add(request, obj, post_url_continue)


# The client edits visible content; addresses and publication snapshots stay internal.
from .forms import PageForm, SectionForm, ServiceForm, ProjectForm, PhotoForm
from .models import SitePage, PageSection, Service, Project, ProjectPhoto
from .publishing import publish_content, unpublish_content, content_payload


class ContentAdmin(admin.ModelAdmin):
    view_on_site = False
    list_display = ('title', 'publication_status', 'published_link')
    search_fields = ('title',)
    list_filter = (PublicationFilter,)
    show_facets = admin.ShowFacets.NEVER
    actions = None
    readonly_fields = ('photo_preview',)
    change_form_template = 'admin/cms/content_change_form.html'
    change_list_template = 'admin/cms/content_change_list.html'

    class Media:
        css = {'all': ('cms/vendor/quill.core.css',)}
        js = ('cms/vendor/quill.js', 'cms/vendor/turndown.js', 'cms/editor.js?v=20261019-content')

    @admin.display(description='Состояние')
    def publication_status(self, obj):
        if not obj.published_payload:
            return 'Черновик'
        try:
            draft = content_payload(obj)
            snapshot = obj.published_payload
            if isinstance(obj, Service):
                derived = ('works', 'alt', 'width', 'height')
                draft = {k: v for k, v in draft.items() if k not in derived}
                snapshot = {k: v for k, v in snapshot.items() if k not in derived}
            return 'Опубликовано' if draft == snapshot else 'Есть неопубликованные правки'
        except Exception:
            return 'Есть неопубликованные правки'

    @admin.display(description='На сайте')
    def published_link(self, obj):
        return format_html('<a href="{}" target="_blank" rel="noopener">Открыть</a>', obj.get_absolute_url()) if obj.published_payload else '—'

    @admin.display(description='Фотография')
    def photo_preview(self, obj):
        if not obj or not obj.pk or not (getattr(obj, 'image', '') or getattr(obj, 'image_upload', None)):
            return 'Фотографию можно добавить ниже.'
        return format_html('<img class="cms-cover-preview" src="{}" alt="Фотография" />', reverse('content-image', args=[obj._meta.model_name, obj.pk]))

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj) and not (obj and obj.published_payload)

    def render_change_form(self, request, context, *args, **kwargs):
        obj = context.get('original')
        context.update(cms_published=bool(obj and obj.published_payload), cms_can_hide=self.model != SitePage, cms_content_label=self.model._meta.verbose_name_plural, cms_list_url=reverse('admin:cms_' + self.model._meta.model_name + '_changelist'), title=('Редактирование: ' + str(obj)) if obj else 'Добавить: ' + self.model._meta.verbose_name.lower())
        return super().render_change_form(request, context, *args, **kwargs)

    def changelist_view(self, request, extra_context=None):
        titles = {SitePage: 'Страницы сайта', Service: 'Услуги', Project: 'Наши работы'}
        return super().changelist_view(request, extra_context={**(extra_context or {}), 'title': titles[self.model], 'cms_add_label': 'Добавить услугу' if self.model == Service else 'Добавить работу'})

    def publication_response(self, request, obj):
        if '_publish' in request.POST:
            after_commit(request, lambda: publish_content(type(obj), obj.pk), 'Изменения опубликованы. Страницы сайта обновлены.')
        elif '_unpublish' in request.POST and self.model != SitePage:
            after_commit(request, lambda: unpublish_content(type(obj), obj.pk), 'Снято с публикации. Содержимое сохранено в редакторе.')
        elif '_preview' in request.POST:
            try:
                content_payload(obj)
            except PublicationError as error:
                messages.error(request, str(error) + ' Черновик сохранён.')
                return HttpResponseRedirect(reverse('admin:cms_' + obj._meta.model_name + '_change', args=[obj.pk]))
            return HttpResponseRedirect(reverse('content-preview', args=[obj._meta.model_name, obj.pk]))
        else:
            messages.success(request, 'Сохранено в редакторе. Чтобы показать изменения посетителям, нажмите «Опубликовать».')
        return HttpResponseRedirect(reverse('admin:cms_' + obj._meta.model_name + '_change', args=[obj.pk]))

    def response_add(self, request, obj, post_url_continue=None):
        return self.publication_response(request, obj)

    def response_change(self, request, obj):
        return self.publication_response(request, obj)


class SectionInline(admin.StackedInline):
    model = PageSection
    form = SectionForm
    template = 'admin/cms/page_sections.html'
    extra = 0
    can_delete = False
    fields = ('title', 'body', 'photo_preview', 'image_upload')
    readonly_fields = ('photo_preview',)
    def has_add_permission(self, request, obj=None):
        return False
    @admin.display(description='Фотография блока')
    def photo_preview(self, obj):
        if not obj.pk or not (obj.image or obj.image_upload):
            return 'В этом блоке фотография не используется.'
        return format_html('<img class="cms-cover-preview" src="{}" alt="Фотография блока" />', reverse('content-image', args=['pagesection', obj.pk]))
    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        # Photo controls only belong to blocks that actually use a photo.
        original = formset.form
        class SectionPhotoForm(original):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                if not self.instance.image and not self.instance.image_upload:
                    self.fields['image_upload'].widget = __import__('django.forms', fromlist=['HiddenInput']).HiddenInput()
                    self.fields['image_upload'].disabled = True
        formset.form = SectionPhotoForm
        return formset


@admin.register(SitePage)
class PageAdmin(ContentAdmin):
    form = PageForm
    list_display = ('label', 'publication_status', 'published_link')
    list_filter = ()
    search_fields = ()
    inlines = (SectionInline,)
    fieldsets = [(None, {'fields': ('title', 'intro')}), ('Фотография первого экрана', {'fields': ('photo_preview', 'image_upload')}), ('Дополнительно — вид в поиске', {'fields': ('seo_title', 'seo_description'), 'classes': ('collapse',)})]
    def get_fieldsets(self, request, obj=None):
        return [f for f in self.fieldsets if f[0] != 'Фотография первого экрана' or (obj and (obj.image or obj.image_upload))]
    def has_add_permission(self, request):
        return False
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Service)
class ServiceAdmin(ContentAdmin):
    form = ServiceForm
    fieldsets = [(None, {'fields': ('title', 'summary', 'intro', 'scope', 'prepare')}), ('Фотография', {'fields': ('photo_preview', 'image_upload')}), ('Дополнительно', {'fields': ('position',), 'classes': ('collapse',)}), ('Дополнительно — вид в поиске', {'fields': ('seo_title', 'seo_description'), 'classes': ('collapse',)})]


class PhotoInline(admin.StackedInline):
    model = ProjectPhoto
    form = PhotoForm
    extra = 0
    fields = ('photo_preview', 'image_upload', 'caption', 'position')
    readonly_fields = ('photo_preview',)
    @admin.display(description='Фотография')
    def photo_preview(self, obj):
        if not obj.pk:
            return 'Выберите файл ниже.'
        return format_html('<img class="cms-cover-preview" src="{}" alt="Фотография работы" />', reverse('content-image', args=['projectphoto', obj.pk]))


@admin.register(Project)
class ProjectAdmin(ContentAdmin):
    form = ProjectForm
    def get_inline_formsets(self, request, formsets, inline_instances, obj=None):
        import json
        helpers = super().get_inline_formsets(request, formsets, inline_instances, obj)
        for helper in helpers:
            data = json.loads(helper.inline_formset_data())
            data['options']['addText'] = 'Добавить фотографию'
            helper.inline_formset_data = lambda value=json.dumps(data): value
        return helpers
    inlines = (PhotoInline,)
    fieldsets = [(None, {'fields': ('title', 'summary', 'description', 'details', 'location', 'category', 'service')}), ('Дополнительно', {'fields': ('position',), 'classes': ('collapse',)}), ('Дополнительно — вид в поиске', {'fields': ('seo_title', 'seo_description'), 'classes': ('collapse',)})]
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'service':
            kwargs['queryset'] = Service.objects.order_by('position', 'pk')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
