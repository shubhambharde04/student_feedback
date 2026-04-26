import os
import sys
import django
import pandas as pd
from io import BytesIO

# Add the current directory to sys.path to ensure 'users' can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feedback_system.settings')
django.setup()

from users.student_import import StudentImportService
from users.models import Semester, Branch, FeedbackSession, StudentSemester, User

def test_mapping():
    print("Testing Semester-to-Year Mapping...")
    
    # Setup test session
    session, _ = FeedbackSession.objects.get_or_create(
        name='TEST SESSION',
        defaults={
            'type': 'ODD',
            'year': 2025,
            'is_active': True,
            'start_date': '2025-01-01',
            'end_date': '2025-06-30'
        }
    )
    
    # Mock data with different semesters
    data = [
        {'name': 'Student 1', 'enrollment_no': 'S1', 'department': 'IT', 'semester': '1', 'session': 'TEST SESSION'},
        {'name': 'Student 2', 'enrollment_no': 'S2', 'department': 'IT', 'semester': '3', 'session': 'TEST SESSION'},
        {'name': 'Student 3', 'enrollment_no': 'S3', 'department': 'IT', 'semester': '5', 'session': 'TEST SESSION'},
    ]
    
    # Create a user to act as uploader
    admin = User.objects.filter(role='admin').first() or User.objects.create(username='test_admin', role='admin')
    
    # Run the save_to_db logic (directly or via process)
    # We'll use save_to_db directly for easier testing of the mapping
    result = StudentImportService.save_to_db(data, admin)
    
    print(f"Import result: {result['created']} created, {result['updated']} updated")
    
    # Verify mappings
    for enroll, expected_class in [('S1', '1st Year'), ('S2', '2nd Year'), ('S3', '3rd Year')]:
        ss = StudentSemester.objects.filter(student__username=enroll, session=session).first()
        if ss:
            print(f"Enrollment {enroll} (Sem {ss.semester.number}) -> Class: '{ss.class_name}' (Expected: '{expected_class}')")
            if ss.class_name == expected_class:
                print("  SUCCESS")
            else:
                print(f"  FAILURE: Got '{ss.class_name}', expected '{expected_class}'")
        else:
            print(f"  FAILURE: StudentSemester record not found for {enroll}")

if __name__ == "__main__":
    test_mapping()
