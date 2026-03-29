import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feedback_system.settings')
django.setup()

from users.models import User
from django.contrib.auth import authenticate

def fix_all_students():
    students = User.objects.filter(role='student')
    print(f"Checking {students.count()} student(s)...")
    
    fixed_count = 0
    
    for student in students:
        # Check if they have already changed their password to something else
        # Or if their password is still the default (username)
        
        # In this task, we want to ensure all students are strictly set to
        # password = username and is_first_login = True, UNLESS they manually
        # went to change_password and changed it (is_first_login = False).
        
        # But to be safe, if we just want to reset ALL students back to default for testing
        # or fixing those who had plain text passwords:
        
        if student.is_first_login:
            # Re-hash it purely securely from enrollment_no/username
            student.set_password(student.username)
            student.save(update_fields=['password'])
            fixed_count += 1
            print(f"Fixed: {student.username}")
        else:
            print(f"Skip: {student.username} (Already completed first login / changed password)")

    print(f"Fixed {fixed_count} student passwords.")

if __name__ == '__main__':
    fix_all_students()
