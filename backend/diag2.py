import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'feedback_system.settings'
import django
django.setup()
from users.models import User, StudentSemester, SubjectOffering, SubjectAssignment, Branch, Semester, Subject
import json

result = {}

# StudentSemesters
ss = StudentSemester.objects.all().select_related('student','branch','semester')
result['student_semester_count'] = ss.count()
result['student_semester_sample'] = [
    {'student': s.student.username, 'branch_id': s.branch.id, 'branch_code': s.branch.code, 'sem_id': s.semester.id, 'sem_num': s.semester.number}
    for s in ss[:5]
]

# Offerings 
ofs = SubjectOffering.objects.all().select_related('subject','branch','semester')
result['offering_count'] = ofs.count()
result['offering_sample'] = [
    {'id': o.id, 'subj': o.subject.code, 'branch_id': o.branch.id, 'branch': o.branch.code, 'sem_id': o.semester.id, 'sem': o.semester.number, 'active': o.is_active}
    for o in ofs[:10]
]

# distinct branch+sem combos in offerings
result['offering_branch_ids'] = list(SubjectOffering.objects.values_list('branch_id',flat=True).distinct())
result['offering_semester_ids'] = list(SubjectOffering.objects.values_list('semester_id',flat=True).distinct())

# Assignments
asns = SubjectAssignment.objects.all().select_related('offering__subject','teacher')
result['assignment_count'] = asns.count()

# Test lookup 
first = StudentSemester.objects.first()
if first:
    result['test_student'] = first.student.username
    result['test_branch_id'] = first.branch.id
    result['test_sem_id'] = first.semester.id
    matching = SubjectOffering.objects.filter(branch=first.branch, semester=first.semester, is_active=True).count()
    result['matching_offerings'] = matching
else:
    result['test_student'] = 'NONE'
    result['matching_offerings'] = 0

with open('diag.json','w') as f:
    json.dump(result, f, indent=2)
print("DONE")
