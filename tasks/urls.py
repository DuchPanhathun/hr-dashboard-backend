from django.urls import path
from . import views

urlpatterns = [
    path('tasks/', views.task_list_create, name='task-list-create'),
    path('tasks/<int:task_id>/', views.task_detail, name='task-detail'),
    path('tasks/stats/', views.get_task_stats, name='task-stats'),
    path('tasks/workload-overview/', views.get_workload_overview, name='workload_overview'),
    path('tasks/assign-staff/', views.assign_staff, name='assign_staff'),
    path('staff-details/', views.get_staff_details, name='staff_details'),
]