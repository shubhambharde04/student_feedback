import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feedback_system.settings')
import django
django.setup()

from users.models import User

# Reset HOD password for testing
hod = User.objects.filter(role='hod', username='test_hod').first()
if not hod:
    hod = User.objects.filter(role='hod').first()
if hod:
    hod.set_password('test1234')
    hod.save()
    print(f"Reset password for HOD: {hod.username}")
else:
    print("No HOD found")
