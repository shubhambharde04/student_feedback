"""
Fix all student passwords to be properly hashed.
For each student:
  - If password is not usable (blank/corrupted) -> set to enrollment_no
  - If is_first_login=True -> re-hash password as enrollment_no (safe reset)
  - If is_first_login=False -> skip (student already changed their password)
After fixing, verify one student can authenticate.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feedback_system.settings')
django.setup()

from users.models import User
from django.contrib.auth import authenticate

def fix_all_students():
    students = User.objects.filter(role='student')
    total = students.count()
    print(f"Checking {total} student(s)...\n")
    
    fixed = 0
    skipped = 0
    already_ok = 0
    
    for student in students:
        enrollment = student.enrollment_no or student.username
        
        if not student.has_usable_password():
            # Password is blank or unusable - must fix
            student.set_password(enrollment)
            student.is_first_login = True
            student.save(update_fields=['password', 'is_first_login'])
            fixed += 1
            print(f"  FIXED (no password): {student.username}")
        elif student.is_first_login:
            # Still on default password - re-hash to be sure
            if student.check_password(enrollment):
                already_ok += 1
            else:
                student.set_password(enrollment)
                student.save(update_fields=['password'])
                fixed += 1
                print(f"  FIXED (rehashed):    {student.username}")
        else:
            # Student already changed password - don't touch
            skipped += 1
    
    print(f"\nResults:")
    print(f"  Fixed:      {fixed}")
    print(f"  Already OK: {already_ok}")
    print(f"  Skipped:    {skipped} (already changed password)")
    print(f"  Total:      {total}")
    
    # Verify: pick a first_login student and test authenticate
    test_student = User.objects.filter(role='student', is_first_login=True).first()
    if test_student:
        enrollment = test_student.enrollment_no or test_student.username
        print(f"\n--- Verification ---")
        print(f"Testing: {test_student.username} (enrollment: {enrollment})")
        print(f"  has_usable_password: {test_student.has_usable_password()}")
        print(f"  check_password('{enrollment}'): {test_student.check_password(enrollment)}")
        
        auth_result = authenticate(username=test_student.username, password=enrollment)
        if auth_result:
            print(f"  authenticate(): SUCCESS")
        else:
            print(f"  authenticate(): FAILED")
            # Check if user is active
            print(f"  is_active: {test_student.is_active}")
    else:
        print("\nNo first-login students found for verification.")

if __name__ == '__main__':
    fix_all_students()
