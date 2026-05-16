from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = 'videos'

urlpatterns = [
    path('', views.index, name='index'),
    path('accounts/register/', views.register, name='register'),
    path(
        'accounts/login/',
        auth_views.LoginView.as_view(template_name='videos/login.html'),
        name='login',
    ),
    path('accounts/logout/', views.logout_view, name='logout'),
    path('jobs/<int:pk>/', views.detail, name='detail'),
    path('jobs/<int:pk>/retry/', views.retry, name='retry'),
    path('jobs/<int:pk>/download/original/', views.download_original, name='download_original'),
    path('jobs/<int:pk>/download/translated/', views.download_translated, name='download_translated'),
]
