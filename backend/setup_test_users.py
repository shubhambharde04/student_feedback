import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feedback_system.settings')
django.setup()

from users.models import User, Department, Branch, Semester, StudentSemester, FeedbackSession
from django.utils import timezone

def setup_test_data():
    # 0. Active Session
    session, _ = FeedbackSession.objects.get_or_create(
        name='ODD 2024',
        defaults={
            'type': 'ODD',
            'year': 2024,
            'is_active': True,
            'start_date': timezone.now().date(),
            'end_date': (timezone.now() + timezone.timedelta(days=30)).date()
        }
    )

    # 1. Department
    dept, _ = Department.objects.get_or_create(name='Computer Science')
    
    # 2. HOD
    hod, created = User.objects.get_or_create(
        username='test_hod',
        defaults={'email': 'hod@test.com', 'role': 'hod', 'department': dept, 'is_first_login': False}
    )
    hod.set_password('TestPass123!')
    hod.is_first_login = False
    hod.save()
    print(f"HOD test_hod ready (first_login=False).")

    # 3. Teacher
    teacher, created = User.objects.get_or_create(
        username='test_teacher',
        defaults={'email': 'teacher@test.com', 'role': 'teacher', 'department': dept, 'is_first_login': False}
    )
    teacher.set_password('TestPass123!')
    teacher.is_first_login = False
    teacher.save()
    print(f"Teacher test_teacher ready (first_login=False).")

    # 4. Student
    student, created = User.objects.get_or_create(
        username='test_student',
        defaults={
            'email': 'student@test.com', 
            'role': 'student', 
            'department': dept,
            'enrollment_no': 'TESTSTU001',
            'is_first_login': True
        }
    )
    student.set_password('TESTSTU001') # Default is enrollment_no
    student.save()
    
    # Setup Student Academic Profile
    branch, _ = Branch.objects.get_or_create(code='CS', name='Computer Science')
    semester, _ = Semester.objects.get_or_create(number=1)
    
    StudentSemester.objects.update_or_create(
        student=student,
        session=session,
        defaults={
            'branch': branch, 
            'semester': semester,
            'class_name': semester.year_name
        }
    )
    print(f"Student test_student ready with CS Sem 1 in session {session.name}.")

if __name__ == "__main__":
    setup_test_data()
