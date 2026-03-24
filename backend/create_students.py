import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feedback_system.settings')
django.setup()

from users.models import User

def create_students():
    start_no = 2307001
    end_no = 2307068
    created_count = 0
    
    for i in range(start_no, end_no + 1):
        enrollment_no = str(i)
        
        # Check if user already exists
        if not User.objects.filter(username=enrollment_no).exists():
            user = User.objects.create_user(
                username=enrollment_no,
                password=enrollment_no,
                role='student',
                enrollment_no=enrollment_no,
                is_first_login=True
            )
            created_count += 1
            print(f"Created student {enrollment_no}")
        else:
            print(f"Student {enrollment_no} already exists")
            
    print(f"Successfully created {created_count} new students.")

if __name__ == '__main__':
    create_students()
