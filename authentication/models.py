from django_mongoengine import Document, fields
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from django.db import models
from mongoengine import StringField, DateTimeField, FloatField, SequenceField, BooleanField

class User(Document):
    username = fields.StringField(max_length=150, unique=True, blank=False)
    email = fields.EmailField(unique=True, blank=False)
    password = fields.StringField(max_length=128, blank=False)
    is_active = fields.BooleanField(default=True)
    is_staff = fields.BooleanField(default=False)
    is_superuser = fields.BooleanField(default=False)
    date_joined = fields.DateTimeField(default=timezone.now)
    last_login = fields.DateTimeField(default=timezone.now)

    # Add these properties for Django authentication compatibility
    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_username(self):
        return self.username

    meta = {
        'collection': 'users',
        'indexes': ['username', 'email']
    }

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return self.username 

class Staff(Document):
    id = SequenceField(primary_key=True)
    staff_name = StringField(required=True, max_length=100)
    role = StringField(required=True, max_length=100)
    start_date = DateTimeField(required=True)
    end_date = DateTimeField(required=True)
    total_loe = FloatField(required=True, min_value=0, max_value=100)

    meta = {
        'collection': 'staff'
    }

    def __str__(self):
        return self.staff_name 

class Notification(Document):
    id = SequenceField(primary_key=True)
    message = StringField(required=True)
    action_type = StringField(required=True)  # 'add', 'update', 'delete'
    staff_name = StringField(required=True)
    user_name = StringField(required=True)
    details = StringField(required=True)
    timestamp = DateTimeField(default=timezone.now)
    is_read = BooleanField(default=False)

    meta = {
        'collection': 'notifications',
        'ordering': ['-timestamp']
    } 

class Project(Document):
    id = SequenceField(primary_key=True)
    award_name = StringField(max_length=200, blank=False)
    status = StringField(max_length=100, blank=False)
    project_start_date = DateTimeField(blank=False)
    project_end_date = DateTimeField(blank=False)
    loe_percentage = FloatField(min_value=0, max_value=100)

    meta = {
        'collection': 'projects'
    }

    def __str__(self):
        return self.award_name

class ProjectStaff(Document):
    id = SequenceField(primary_key=True)
    project = fields.ReferenceField(Project, blank=False)
    staff = fields.ReferenceField(Staff, blank=False)
    loe_percentage = FloatField(min_value=0, max_value=100)
    start_date = DateTimeField()
    end_date = DateTimeField()

    meta = {
        'collection': 'project_staff',
        'indexes': [
            {'fields': ('project', 'staff'), 'unique': True}
        ]
    }

    def __str__(self):
        return f"{self.project.award_name} - {self.staff.staff_name}" 