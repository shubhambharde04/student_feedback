import django
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "feedback_system.settings")
django.setup()

from users.models import Feedback, SubjectOffering, SubjectAssignment

feedbacks = Feedback.objects.all()
for f in feedbacks:
    offering = getattr(f, 'offering', None)
    subject = offering.subject.name if offering and offering.subject else "None"
    teacher = "Unassigned"
    if offering:
        assignment = getattr(offering, 'assignment', None)
        if assignment and assignment.is_active:
            teacher = assignment.teacher.username
    print(f"Feedback ID: {f.id}, Student: {f.student.username}, Offering ID: {f.offering_id}, Subject: {subject}, Teacher: {teacher}")

print("\n--- Teacher Offerings ---")
assignments = SubjectAssignment.objects.all()
for a in assignments:
    print(f"Assignment ID: {a.id}, Offering ID: {a.offering_id}, Teacher: {a.teacher.username}, IsActive: {a.is_active}")
