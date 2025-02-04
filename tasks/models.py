from django_mongoengine import Document, fields
from django.utils import timezone
from mongoengine import StringField, DateTimeField, FloatField, IntField, ReferenceField
from authentication.models import Staff, Project, Skill

class Task(Document):
    title = StringField(max_length=200, required=True)
    required_skills = fields.ListField(ReferenceField(Skill), default=list)  # Update to use Skill references
    required_loe = FloatField(
        default=0,
        min_value=0,
        max_value=100
    )
    deadline = DateTimeField(required=True)
    status = StringField(
        choices=[
            ('unassigned', 'Unassigned'),
            ('assigned', 'Assigned'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed')
        ],
        default='unassigned'
    )
    project = ReferenceField(Project, required=False)
    assigned_staff = ReferenceField(Staff, required=False)
    complexity_level = IntField(
        default=3,
        min_value=1,
        max_value=5
    )
    created_at = DateTimeField(default=timezone.now)
    updated_at = DateTimeField(default=timezone.now)
    dependencies = fields.ListField(ReferenceField('Task'), default=list)
    priority = IntField(min_value=1, max_value=5, default=3)

    meta = {
        'collection': 'tasks',
        'ordering': ['deadline']
    }

    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()
        if not self.complexity_level:
            from .services import calculate_task_complexity
            self.complexity_level = calculate_task_complexity(self)
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.status})"