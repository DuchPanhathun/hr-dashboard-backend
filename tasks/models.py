from django.db import models
from djongo import models as djongo_models
from django_mongoengine import Document, fields
from django.utils import timezone
from mongoengine import StringField, DateTimeField, FloatField, SequenceField

class Staff(models.Model):
    staff_name = models.CharField(max_length=100)
    skills = models.TextField(blank=True)  # Comma-separated skills
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    # ... other existing fields ... 

    def __str__(self):
        return self.staff_name

class Project(models.Model):
    award_name = models.CharField(max_length=200)
    project_start_date = models.DateTimeField()
    project_end_date = models.DateTimeField()
    required_loe = models.FloatField(default=0)  # Level of Effort required

    def __str__(self):
        return self.award_name

class ProjectStaff(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    loe_percentage = models.FloatField(default=0)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()

    class Meta:
        unique_together = ('project', 'staff')

    def __str__(self):
        return f"{self.staff.staff_name} - {self.project.award_name}"

class Task(Document):
    id = SequenceField(primary_key=True)
    title = StringField(max_length=200, required=True)
    required_loe = FloatField(default=0, min_value=0, max_value=100)
    deadline = DateTimeField(required=True)
    status = StringField(
        max_length=50,
        default='unassigned',
        choices=(
            ('unassigned', 'Unassigned'),
            ('assigned', 'Assigned'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed')
        )
    )
    created_at = DateTimeField(default=timezone.now)

    meta = {
        'collection': 'tasks',
        'ordering': ['-created_at']
    }

    def __str__(self):
        return self.title 