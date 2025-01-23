from django.urls import path
from .views import (
    task_list_create,
    task_detail,
    get_task_stats,
    get_workload_overview,
    get_staff_details,
    get_project_staff
)

urlpatterns = [
    path('api/workload-overview/', get_workload_overview, name='workload-overview'),
    path('api/staff/list/', get_staff_details, name='staff-details'),
    path('api/project-staff/', get_project_staff, name='project-staff'),
    path('api/tasks/', task_list_create, name='task-list-create'),
    path('api/tasks/<int:task_id>/', task_detail, name='task-detail'),
    path('api/tasks/stats/', get_task_stats, name='task-stats'),
]