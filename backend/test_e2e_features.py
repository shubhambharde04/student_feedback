import os
import django
import sys
from datetime import date, timedelta

# Setup Django
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "feedback_system.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from users.models import (
    Branch, Semester, FeedbackSession, Subject, SubjectOffering, 
    SubjectAssignment, StudentSemester, Feedback, Department
)
from users.views import hod_teacher_report, hod_department_report
from rest_framework.test import APIRequestFactory, force_authenticate

User = get_user_model()

def run_e2e_tests():
    print("Starting E2E Integration Tests (Hardened)...\n")
    factory = APIRequestFactory()
    
    # 1. SETUP TEST DATA
    print("--- 1. Setting Up Test Data ---")
    
    # Aggressive Cleanup
    test_dept_code = "E2E_DEPT"
    test_branch_code = "E2E_IT"
    test_subj_code = "E2E_SUB"
    
    # Cleanup data
    print("Cleaning up old test data...")
    User.objects.filter(username__startswith="test_").delete()
    FeedbackSession.objects.filter(name__startswith="E2E_").delete()
    Subject.objects.filter(code=test_subj_code).delete()
    Branch.objects.filter(code=test_branch_code).delete()
    Department.objects.filter(code=test_dept_code).delete()

    # Create fresh Dept/Branch
    dept = Department.objects.create(name="E2E Research Department", code=test_dept_code)
    branch = Branch.objects.create(code=test_branch_code, name="Test E2E Branch", department=dept)
    semester, _ = Semester.objects.get_or_create(number=99, defaults={"name": "E2E Semester"})
    
    # Create Users
    hod_user = User.objects.create(username="test_hod", role="hod", department=dept)
    teacher_user = User.objects.create(username="test_teacher", role="teacher")
    
    students = []
    for i in range(1, 11):
        std = User.objects.create(username=f"test_std_{i}", role="student")
        students.append(std)

    # Create Session
    test_year = 9999
    session = FeedbackSession.objects.create(
        name="E2E_SESSION",
        year=test_year,
        type="ODD",
        start_date=timezone.now().date() - timezone.timedelta(days=1),
        end_date=(timezone.now() + timezone.timedelta(days=30)).date(),
        is_active=True
    )
    print(f"Created Session: {session.name} ({session.year})")

    # Create Subject & Offering
    subject = Subject.objects.create(code=test_subj_code, name="E2E Test Subject")
    offering = SubjectOffering.objects.create(
        subject=subject,
        branch=branch,
        semester=semester,
        is_active=True
    )
    
    # Assign Teacher
    SubjectAssignment.objects.create(
        offering=offering,
        teacher=teacher_user,
        is_active=True
    )
    
    # Enroll Students
    for std in students:
        StudentSemester.objects.create(
            student=std,
            session=session,
            branch=branch,
            semester=semester,
            is_active=True
        )
    print(f"Enrolled {len(students)} students.")

    # 2. TEST REPORT THRESHOLD (1/10 = 10% < 30%)
    print("\n--- 2. Testing 30% Threshold (Under) ---")
    Feedback.objects.create(
        student=students[0],
        offering=offering,
        punctuality_rating=5, teaching_rating=5, clarity_rating=5, interaction_rating=5, behavior_rating=5,
        comment="Teacher is very punctual and has great domain knowledge."
    )
    
    request = factory.get(f'/api/hod/teacher/{teacher_user.id}/report/', {'session': session.id})
    force_authenticate(request, user=hod_user)
    response = hod_teacher_report(request, pk=teacher_user.id)
    
    data = response.data
    off_data = next((o for o in data['offerings'] if o['offering_id'] == offering.id), None)
    
    print(f"Feedback Percentage: {off_data['feedback_percentage']}%")
    print(f"Threshold Met: {off_data['threshold_met']}")
    
    assert off_data['threshold_met'] == False
    assert off_data['score'] == 0 or off_data['score'] is None

    # 3. TEST REPORT THRESHOLD (4/10 = 40% > 30%)
    print("\n--- 3. Testing 30% Threshold (Over) ---")
    for i in range(1, 4):
        Feedback.objects.create(
            student=students[i], offering=offering,
            punctuality_rating=4, teaching_rating=4, clarity_rating=4, interaction_rating=4, behavior_rating=4,
            comment="Good style."
        )
    
    response = hod_teacher_report(request, pk=teacher_user.id)
    off_data = next((o for o in response.data['offerings'] if o['offering_id'] == offering.id), None)
    
    print(f"Feedback Percentage: {off_data['feedback_percentage']}%")
    print(f"Threshold Met: {off_data['threshold_met']}")
    
    assert off_data['threshold_met'] == True
    assert off_data['score'] > 0

    # 4. TEST OBSERVATIONS
    print("\n--- 4. Testing Observations ---")
    key_obs = response.data.get('overall_remarks', "")
    if not key_obs: # Try teacher specific remarks
        key_obs = response.data.get('key_observations', "")
    print(f"Observations: {key_obs}")
    assert "Punctual" in key_obs or "punctual" in key_obs.lower()

    # 5. TEST SESSION ARCHIVAL / STUDENT LISTING
    print("\n--- 5. Testing Archival Lockdown ---")
    from users.views import close_feedback_session, get_student_subjects
    
    # Close session
    close_req = factory.post(f'/api/sessions/{session.id}/close/')
    force_authenticate(close_req, user=hod_user)
    close_feedback_session(close_req, pk=session.id)
    
    session.refresh_from_db()
    print(f"Session is_active: {session.is_active}")
    assert session.is_active == False
    
    # Check student visibility (should be session aware)
    std_req = factory.get('/api/student/subjects/', {'session': session.id}) # Pass session to test session-aware listing
    force_authenticate(std_req, user=students[5])
    # Note: get_student_subjects currently looks at ACTIVE sessions if none passed.
    # If the session is closed, and it's the only one, student might see nothing.
    std_resp = get_student_subjects(std_req)
    print(f"Found {len(std_resp.data)} subjects for closed session.")
    
    print("\nDone. E2E Hardened Tests Passed!")

if __name__ == "__main__":
    try:
        run_e2e_tests()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
