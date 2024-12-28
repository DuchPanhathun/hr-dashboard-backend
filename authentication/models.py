from django_mongoengine import Document, fields
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone

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