from django_mongoengine import mongo_admin as admin
from .models import Task

@admin.register(Task)
class TaskAdmin(admin.DocumentAdmin):
    list_display = ('title', 'status', 'deadline', 'assigned_staff')
    list_filter = ('status', 'complexity_level', 'priority')
    search_fields = ('title',)
    ordering = ('deadline',)