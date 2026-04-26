
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feedback_system.settings')
django.setup()

from users.models import User

def reset():
    users = ['test_std_1', 'test_teacher', 'test_hod', 'admin']
    for username in users:
        u = User.objects.filter(username=username).first()
        if u:
            u.set_password('password')
            u.save()
            print(f"Reset {username}")
        else:
            print(f"User {username} not found")

if __name__ == "__main__":
    reset()
