import logging
from django.contrib import admin, messages
from django.db import transaction
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html
from .forms import ArticleForm
from .models import Article, SiteSettings
from .publishing import publish_article, unpublish_article, publish_settings

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
        js = ('cms/vendor/quill.js', 'cms/vendor/turndown.js', 'cms/editor.js')

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
    fields = ('company_name', 'phone', 'hero_description')
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
        after_commit(request, lambda: publish_settings(obj.pk), 'Контакты и текст главной страницы опубликованы на сайте.')
        return super().response_change(request, obj)
    def response_add(self, request, obj, post_url_continue=None):
        after_commit(request, lambda: publish_settings(obj.pk), 'Настройки сайта опубликованы.')
        return super().response_add(request, obj, post_url_continue)
