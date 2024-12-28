from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_user, name='login'),
    path('users/', views.list_users, name='list-users'),
] 