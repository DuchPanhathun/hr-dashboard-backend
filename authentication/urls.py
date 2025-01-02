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
    path('notifications/', views.get_notifications, name='get_notifications'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('upload-file/', views.upload_file, name='upload-file'),
    path('projects/', views.list_projects, name='list_projects'),
    path('projects/<int:project_id>/staff/', views.get_project_staff, name='get_project_staff'),
    path('projects/<int:project_id>/', views.delete_project, name='delete_project'),
] 