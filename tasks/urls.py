from django.urls import path
from .views import create_task, delete_task, assign_staff

urlpatterns = [
    path("api/tasks/create/", create_task, name="create-task"),
    path("api/tasks/<str:task_id>/delete/", delete_task, name="delete-task"),
    path("api/assign-staff/", assign_staff, name="assign-staff"),
]