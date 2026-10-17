from django.contrib import admin
from django.urls import path, re_path
from cms import views

urlpatterns = [
    path('cms-preview/<int:pk>/', admin.site.admin_view(views.preview_article), name='article-preview'),
    path('admin/article-cover/<int:pk>/', admin.site.admin_view(views.article_cover), name='article-cover'),
    path('admin/', admin.site.urls),
    re_path(r'^(?P<path>.*)$', views.public_file),
]
