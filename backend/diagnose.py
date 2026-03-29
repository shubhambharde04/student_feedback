"""Diagnose database relationships and data flow for student feedback system."""
import os
import sys

# Setup Django first
os.environ['DJANGO_SETTINGS_MODULE'] = 'feedback_system.settings'
import django
django.setup()

# Now import models after Django is ready
from users.models import User, StudentSemester, SubjectOffering, SubjectAssignment, Branch, Semester, Subject

print("=" * 60)
print("DATABASE DIAGNOSIS")
print("=" * 60)

# 1. Students
students = User.objects.filter(role='student')
print(f"\n1. STUDENTS: {students.count()} total")
for s in students[:5]:
    print(f"   id={s.id} username={s.username} enrollment_no={s.enrollment_no}")

# 2. StudentSemester (enrollment)
print(f"\n2. STUDENT SEMESTER ENROLLMENTS:")
ss = StudentSemester.objects.all().select_related('student', 'branch', 'semester')
print(f"   Total: {ss.count()}")
for s in ss[:10]:
    print(f"   student={s.student.username} -> branch={s.branch.code} sem={s.semester.number}")

# 3. Branches
print(f"\n3. BRANCHES:")
for b in Branch.objects.all():
    print(f"   id={b.id} code={b.code} name={b.name}")

# 4. Semesters
print(f"\n4. SEMESTERS:")
for s in Semester.objects.all():
    print(f"   id={s.id} number={s.number} name={s.name}")

# 5. Subjects
print(f"\n5. SUBJECTS: {Subject.objects.count()} total")
for s in Subject.objects.all()[:10]:
    print(f"   id={s.id} code={s.code} name={s.name}")

# 6. Subject Offerings
print(f"\n6. SUBJECT OFFERINGS:")
offerings = SubjectOffering.objects.all().select_related('subject', 'branch', 'semester')
print(f"   Total: {offerings.count()}")
for o in offerings[:10]:
    print(f"   id={o.id} {o.subject.code} | {o.branch.code} | sem={o.semester.number} | active={o.is_active}")

# 7. Subject Assignments
print(f"\n7. SUBJECT ASSIGNMENTS (teacher -> offering):")
assignments = SubjectAssignment.objects.all().select_related(
    'offering__subject', 'offering__branch', 'offering__semester', 'teacher'
)
print(f"   Total: {assignments.count()}")
for a in assignments[:10]:
    print(f"   teacher={a.teacher.username} -> {a.offering.subject.code} | {a.offering.branch.code} sem={a.offering.semester.number} | active={a.is_active}")

# 8. Test: For a specific student, what would get_student_subjects return?
print(f"\n8. TEST SUBJECT LOOKUP FOR FIRST ENROLLED STUDENT:")
first_enrolled = StudentSemester.objects.first()
if first_enrolled:
    student = first_enrolled.student
    branch = first_enrolled.branch
    semester = first_enrolled.semester
    print(f"   Student: {student.username}, Branch: {branch.code}, Semester: {semester.number}")
    
    matching_offerings = SubjectOffering.objects.filter(
        branch=branch, semester=semester, is_active=True
    )
    print(f"   Matching offerings: {matching_offerings.count()}")
    for o in matching_offerings:
        has_assignment = hasattr(o, 'assignment')
        try:
            assignment = o.assignment
            teacher = assignment.teacher.username if assignment.is_active else "INACTIVE"
        except Exception:
            teacher = "NO ASSIGNMENT"
        print(f"   -> {o.subject.code} | teacher={teacher}")
else:
    print("   NO STUDENTS ENROLLED IN ANY SEMESTER!")

# 9. Test the v2 API would work
print(f"\n9. API student-subjects/ WOULD RETURN:")
if first_enrolled:
    print(f"   (for student {first_enrolled.student.username})")
    offerings = SubjectOffering.objects.filter(
        branch=first_enrolled.branch,
        semester=first_enrolled.semester,
        is_active=True
    ).select_related('subject', 'branch', 'semester')
    if offerings.count() == 0:
        print("   *** EMPTY - No subject offerings for this branch+semester ***")
        print(f"   Looking for: branch_id={first_enrolled.branch.id} ({first_enrolled.branch.code}), semester_id={first_enrolled.semester.id} (sem #{first_enrolled.semester.number})")
        print(f"   Available offerings branch IDs: {list(SubjectOffering.objects.values_list('branch_id', flat=True).distinct())}")
        print(f"   Available offerings semester IDs: {list(SubjectOffering.objects.values_list('semester_id', flat=True).distinct())}")
    else:
        for o in offerings:
            print(f"   {o.subject.name} ({o.subject.code})")
else:
    print("   CANNOT TEST - no enrolled students")

print("\n" + "=" * 60)
print("DIAGNOSIS COMPLETE")
print("=" * 60)
