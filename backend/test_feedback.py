import django
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "feedback_system.settings")
django.setup()

from users.models import FeedbackSubmission, SessionOffering, SubjectAssignment

feedbacks = FeedbackSubmission.objects.all()
for f in feedbacks:
    offering = getattr(f, 'offering', None)
    base_offering = offering.base_offering if offering else None
    subject = base_offering.subject.name if base_offering and base_offering.subject else "None"
    teacher = "Unassigned"
    if offering and offering.teacher:
        teacher = offering.teacher.username
    print(f"Feedback ID: {f.id}, Student: {f.student.username}, Session Offering ID: {f.offering_id}, Subject: {subject}, Teacher: {teacher}")

print("\n--- Teacher Offerings ---")
assignments = SubjectAssignment.objects.all()
for a in assignments:
    print(f"Assignment ID: {a.id}, Offering ID: {a.offering_id}, Teacher: {a.teacher.username}, IsActive: {a.is_active}")
