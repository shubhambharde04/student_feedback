import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feedback_system.settings')
import django
django.setup()

from users.models import User, StudentSemester, SessionOffering, FeedbackSession, SubjectOffering

# Check a sample student
student = User.objects.filter(role='student').first()
if student:
    print(f"Student: {student.username} ({student.get_full_name()})")
    
    # Check their StudentSemester records
    semesters = StudentSemester.objects.filter(student=student)
    print(f"  StudentSemesters: {semesters.count()}")
    for ss in semesters:
        print(f"    - Branch: {ss.branch.name}, Sem: {ss.semester.number}, Session: {ss.session.name if ss.session else 'None'}, Active: {ss.is_active}")
    
    # Check active session
    active_session = FeedbackSession.objects.filter(is_active=True).first()
    if active_session:
        print(f"\n  Active Session: {active_session.name}")
        
        # Check if student has semester for this session
        active_ss = semesters.filter(session=active_session)
        print(f"  Student semesters for active session: {active_ss.count()}")
        
        if active_ss.exists():
            ss = active_ss.first()
            # Check SessionOfferings for this branch/semester
            offerings = SessionOffering.objects.filter(
                session=active_session,
                base_offering__branch=ss.branch,
                base_offering__semester=ss.semester,
                is_active=True
            )
            print(f"  SessionOfferings for {ss.branch.code}/Sem{ss.semester.number}: {offerings.count()}")
            for o in offerings:
                print(f"    - {o.base_offering.subject.name} -> teacher: {o.teacher.get_full_name()}")
else:
    print("No students found")
