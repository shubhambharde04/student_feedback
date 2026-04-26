import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feedback_system.settings')
import django
django.setup()

from users.models import User, SessionOffering, FeedbackResponse, FeedbackSession, SubjectOffering, SubjectAssignment, StudentSemester

# HOD info
hod = User.objects.filter(role='hod').first()
if hod:
    print(f"HOD: {hod.username} ({hod.get_full_name()})")
else:
    print("No HOD found")

# Teachers
teachers = User.objects.filter(role='teacher')
print(f"\nTeachers: {teachers.count()}")
for t in teachers[:5]:
    so_count = SessionOffering.objects.filter(teacher=t, is_active=True).count()
    print(f"  - {t.username} ({t.get_full_name()}) active={t.is_active} session_offerings={so_count}")

# Students
students = User.objects.filter(role='student')
print(f"\nStudents: {students.count()}")

# Active session
session = FeedbackSession.objects.filter(is_active=True).first()
if session:
    print(f"\nActive Session: {session.name} (ID={session.id})")
else:
    print("\nNo active session!")

# Subject offerings
so_count = SubjectOffering.objects.count()
print(f"\nSubjectOfferings: {so_count}")

# Subject assignments
sa_count = SubjectAssignment.objects.count()
sa_active = SubjectAssignment.objects.filter(is_active=True).count()
print(f"SubjectAssignments: total={sa_count}, active={sa_active}")

# Session offerings
soff = SessionOffering.objects.all()
soff_active = soff.filter(is_active=True)
print(f"SessionOfferings: total={soff.count()}, active={soff_active.count()}")
for s in soff_active[:5]:
    print(f"  - {s.base_offering.subject.name} -> teacher={s.teacher.get_full_name()}")

# Student semesters
ss = StudentSemester.objects.all()
ss_active = ss.filter(is_active=True)
print(f"\nStudentSemesters: total={ss.count()}, active={ss_active.count()}")

# Feedback responses
fr = FeedbackResponse.objects.count()
print(f"\nFeedbackResponses: {fr}")
