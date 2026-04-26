import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feedback_system.settings')
import django
django.setup()

from users.models import SessionOffering, SubjectOffering, SubjectAssignment

# Check SessionOfferings without teachers
null_teacher = SessionOffering.objects.filter(teacher__isnull=True)
print(f"SessionOfferings without teacher: {null_teacher.count()}")
for so in null_teacher:
    print(f"  - {so.base_offering.subject.name} ({so.base_offering.branch.code}/Sem{so.base_offering.semester.number})")
    # Check if SubjectAssignment exists for this offering
    try:
        sa = so.base_offering.assignment
        print(f"    SubjectAssignment exists: teacher={sa.teacher.get_full_name()} active={sa.is_active}")
    except SubjectAssignment.DoesNotExist:
        print(f"    No SubjectAssignment exists")

print(f"\nSessionOfferings WITH teacher: {SessionOffering.objects.exclude(teacher__isnull=True).count()}")
