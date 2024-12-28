from django.core.management.base import BaseCommand
from authentication.models import User
from django.utils import timezone

class Command(BaseCommand):
    help = 'Creates a superuser'

    def handle(self, *args, **options):
        if not User.objects.filter(username='admin').first():
            current_time = timezone.now()
            user = User(
                username='admin',
                email='admin@example.com',
                is_staff=True,
                is_superuser=True,
                date_joined=current_time,
                last_login=current_time
            )
            user.set_password('admin')
            user.save()
            self.stdout.write(self.style.SUCCESS('Superuser created successfully'))
        else:
            self.stdout.write(self.style.WARNING('Superuser already exists')) 