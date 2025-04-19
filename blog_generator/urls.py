from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login', views.user_login, name='index'),
    path('signup', views.user_signup, name='signup'),
    path('logout', views.user_logout, name='logout'),
    path('generate-blog', views.generate_blog),
    path('blog-list', views.blog_list, name='blog-list'),
    path('youtube-downloader', views.youtube_downloader, name='blog-list'),
    path('blog-details/<int:pk>/', views.blog_details, name='blog-details')
]
