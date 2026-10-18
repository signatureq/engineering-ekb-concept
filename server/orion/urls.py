from django.contrib import admin
from django.urls import path, re_path
from cms import views
from cms.inquiries import inquiry

urlpatterns = [
    path('api/inquiry/', inquiry, name='inquiry'),
    path('cms-preview/<int:pk>/', admin.site.admin_view(views.preview_article), name='article-preview'),
    path('admin/article-cover/<int:pk>/', admin.site.admin_view(views.article_cover), name='article-cover'),
    path('cms-preview/<str:kind>/<int:pk>/', admin.site.admin_view(views.preview_content), name='content-preview'),
    path('admin/content-image/<str:kind>/<int:pk>/', admin.site.admin_view(views.content_image), name='content-image'),
    path('admin/content-upload/<str:name>', admin.site.admin_view(views.preview_upload), name='preview-upload'),
    path('admin/', admin.site.urls),
    re_path(r'^(?P<path>.*)$', views.public_file),
]
