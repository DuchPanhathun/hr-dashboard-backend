from django_mongoengine import Document, fields
from django.utils import timezone
from mongoengine import StringField, DateTimeField, FloatField, IntField, ReferenceField, ListField, ObjectIdField
from authentication.models import Staff, Project, Skill

class Task(Document):
    title = StringField(max_length=200, required=True)
    required_skills = ListField(ReferenceField(Skill))
    required_loe = FloatField(required=True, min_value=0, max_value=100)
    deadline = DateTimeField(required=True)
    status = StringField(
        choices=[
            ('unassigned', 'Unassigned'),
            ('assigned', 'Assigned'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed')
        ],
        required=True,
        default='unassigned'
    )
    project = ReferenceField(Project)
    assigned_staff = ReferenceField(Staff)
    complexity_level = FloatField()
    created_at = DateTimeField(default=timezone.now)
    updated_at = DateTimeField(default=timezone.now)
    priority = IntField(min_value=1, max_value=5, default=3)
    completion_date = DateTimeField(required=False)
    completed_by = StringField(required=False)
    completion_notes = StringField(required=False)

    meta = {
        'collection': 'tasks',
        'ordering': ['deadline']
    }

    def clean(self):
        self.updated_at = timezone.now()
        if self.deadline:
            self.deadline = self.deadline.replace(hour=0, minute=0, second=0, microsecond=0)
        if not self.complexity_level:
            from .services import calculate_task_complexity
            self.complexity_level = calculate_task_complexity(self)

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.status})"