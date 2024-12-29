from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_user, name='login'),
    path('users/', views.list_users, name='list-users'),
    path('staff/add/', views.add_staff, name='add_staff'),
    path('staff/list/', views.list_staff, name='list_staff'),
    path('staff/delete/<int:staff_id>/', views.delete_staff, name='delete_staff'),
    path('staff/update/<int:staff_id>/', views.update_staff, name='update_staff'),
] 