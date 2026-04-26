import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feedback_system.settings')
import django
django.setup()

from users.models import User

# Reset student password for testing
student = User.objects.filter(role='student').first()
if student:
    print(f"Student: {student.username}")
    student.set_password('test1234')
    student.save()
    print("Password reset")
else:
    print("No student found")
