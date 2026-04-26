import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feedback_system.settings')
import django
django.setup()

from users.models import User

# Reset student passwords to their username (enrollment number)
students = User.objects.filter(role='student')
count = 0
for student in students:
    student.set_password(student.username)
    student.save()
    count += 1
    if count % 50 == 0:
        print(f"Updated {count} students...")

print(f"Successfully reset passwords for all {count} students to their enrollment numbers.")
