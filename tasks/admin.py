from django.contrib import admin
from .models import Staff, Project, ProjectStaff

admin.site.register(Staff)
admin.site.register(Project)
admin.site.register(ProjectStaff) 