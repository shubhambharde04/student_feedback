import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feedback_system.settings')
django.setup()

from users.models import Semester

def delete_sem_99():
    deleted, _ = Semester.objects.filter(number=99).delete()
    print(f"Deleted {deleted} Semester(s) with number 99.")

if __name__ == '__main__':
    delete_sem_99()
