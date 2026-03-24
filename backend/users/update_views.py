import re

def update_views():
    filepath = r"d:\student_feedback\feedback_system\users\views.py"
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Update imports
    content = content.replace(
        "from .models import User, Subject, Feedback, FeedbackWindow, Enrollment\nfrom .serializers import (\n    SubjectSerializer, FeedbackSerializer,\n    LoginSerializer, FeedbackWindowSerializer,\n    ChangePasswordSerializer, EnrollmentSerializer\n)",
        "from .models import User, Subject, Feedback, FeedbackWindow\nfrom .serializers import (\n    SubjectSerializer, FeedbackSerializer,\n    LoginSerializer, FeedbackWindowSerializer,\n    ChangePasswordSerializer\n)"
    )

    # 2. Update FeedbackViewSet.create
    old_enroll_check = """        # Check enrollment — student must be enrolled in this subject
        subject_id = request.data.get('subject')
        if not Enrollment.objects.filter(student=request.user, subject_id=subject_id).exists():
            return Response(
                {'error': 'You are not enrolled in this subject'},
                status=status.HTTP_403_FORBIDDEN
            )"""
            
    new_enroll_check = """        # Check enrollment — student must be enrolled in this subject
        subject_id = request.data.get('subject')
        try:
            subject = Subject.objects.get(pk=subject_id)
        except Subject.DoesNotExist:
            return Response({'error': 'Subject not found'}, status=status.HTTP_404_NOT_FOUND)

        if not subject.students.filter(id=request.user.id).exists():
            return Response(
                {'error': 'You are not enrolled in this subject'},
                status=status.HTTP_403_FORBIDDEN
            )"""
    content = content.replace(old_enroll_check, new_enroll_check)

    # 3. Update student_subjects
    old_student_subj = """    enrollments = Enrollment.objects.filter(
        student=request.user
    ).select_related('subject__teacher')

    data = []
    for enrollment in enrollments:
        subject = enrollment.subject"""
        
    new_student_subj = """    subjects = request.user.enrolled_subjects.select_related('teacher')

    data = []
    for subject in subjects:"""
    content = content.replace(old_student_subj, new_student_subj)

    # 4. Modify the ENROLLMENT VIEWS (end of file)
    enrollment_start = content.find("# ============================================================\n# ENROLLMENT VIEWS\n# ============================================================")
    
    new_enrollment_views = """# ============================================================
# ENROLLMENT VIEWS
# ============================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def enroll_student(request):
    \"\"\"Enroll a single student in a subject (HOD/Admin only).\"\"\"
    if request.user.role not in ('hod', 'admin'):
        return Response({'error': 'Only HOD/Admin can assign enrollments'}, status=403)

    student_id = request.data.get('student')
    subject_id = request.data.get('subject')

    if not student_id or not subject_id:
        return Response({'error': 'student and subject are required'}, status=400)

    try:
        student = User.objects.get(pk=student_id, role='student')
    except User.DoesNotExist:
        return Response({'error': 'Student not found'}, status=404)

    try:
        subject = Subject.objects.get(pk=subject_id)
    except Subject.DoesNotExist:
        return Response({'error': 'Subject not found'}, status=404)

    # Branch / Semester validation
    if student.branch and subject.branches.exists() and not subject.branches.filter(id=student.branch.id).exists():
        return Response(
            {'error': f'Branch mismatch: student is in {student.branch.name} but subject is not offered to this branch'},
            status=400
        )
    if subject.semester and student.semester and student.semester != subject.semester:
        return Response(
            {'error': f'Semester mismatch: student is in semester {student.semester.number} but subject belongs to semester {subject.semester.number}'},
            status=400
        )

    # Duplicate check
    if subject.students.filter(id=student.id).exists():
        return Response({'error': 'Student is already enrolled in this subject'}, status=400)

    subject.students.add(student)
    return Response({'message': 'Successfully enrolled'}, status=201)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_enroll(request):
    \"\"\"Enroll multiple students in one subject (HOD/Admin only).\"\"\"
    if request.user.role not in ('hod', 'admin'):
        return Response({'error': 'Only HOD/Admin can assign enrollments'}, status=403)

    student_ids = request.data.get('students', [])
    subject_id = request.data.get('subject')

    if not student_ids or not subject_id:
        return Response({'error': 'students (list) and subject are required'}, status=400)

    try:
        subject = Subject.objects.get(pk=subject_id)
    except Subject.DoesNotExist:
        return Response({'error': 'Subject not found'}, status=404)

    created_count = 0
    errors = []

    for sid in student_ids:
        try:
            student = User.objects.get(pk=sid, role='student')
        except User.DoesNotExist:
            errors.append({'student_id': sid, 'error': 'Student not found'})
            continue

        # Branch validation
        if student.branch and subject.branches.exists() and not subject.branches.filter(id=student.branch.id).exists():
            errors.append({
                'student_id': sid,
                'error': f'Branch mismatch ({student.branch.name} vs subject branches)'
            })
            continue

        # Semester validation
        if subject.semester and student.semester and student.semester != subject.semester:
            errors.append({
                'student_id': sid,
                'error': f'Semester mismatch (sem {student.semester.number} vs sem {subject.semester.number})'
            })
            continue

        # Duplicate check
        if subject.students.filter(id=student.id).exists():
            errors.append({'student_id': sid, 'error': 'Already enrolled'})
            continue

        subject.students.add(student)
        created_count += 1

    return Response({
        'created_count': created_count,
        'errors': errors,
        'error_count': len(errors),
    }, status=201 if created_count > 0 else 400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_enrollments(request):
    \"\"\"List all enrollments (HOD/Admin only).\"\"\"
    if request.user.role not in ('hod', 'admin'):
        return Response({'error': 'Only HOD/Admin can view enrollments'}, status=403)

    subject_id = request.GET.get('subject')
    queryset = Subject.objects.prefetch_related('students').all()

    if subject_id:
        queryset = queryset.filter(id=subject_id)

    data = []
    from django.utils import timezone
    now = timezone.now().isoformat()
    for subject in queryset:
        for student in subject.students.all():
            data.append({
                'id': f"{subject.id}-{student.id}",
                'student': student.id,
                'subject': subject.id,
                'student_name': student.get_full_name() or student.username,
                'student_enrollment_no': student.enrollment_no,
                'subject_name': subject.name,
                'subject_code': subject.code,
                'created_at': now,
            })

    return Response(data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_enrollment(request, pk):
    \"\"\"Remove an enrollment (HOD/Admin only). pk is format: subject_id-student_id\"\"\"
    if request.user.role not in ('hod', 'admin'):
        return Response({'error': 'Only HOD/Admin can remove enrollments'}, status=403)

    try:
        pk_str = str(pk)
        if '-' in pk_str:
            subject_id, student_id = pk_str.split('-')
            subject = Subject.objects.get(pk=int(subject_id))
            student = User.objects.get(pk=int(student_id))
        else:
            return Response({'error': 'Invalid format'}, status=400)
    except (ValueError, Subject.DoesNotExist, User.DoesNotExist):
        return Response({'error': 'Enrollment not found'}, status=404)

    subject.students.remove(student)
    return Response({'message': 'Enrollment removed successfully'}, status=200)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def enrollment_form_data(request):
    \"\"\"Return students and subjects for the enrollment form (HOD/Admin only).\"\"\"
    if request.user.role not in ('hod', 'admin'):
        return Response({'error': 'Only HOD/Admin allowed'}, status=403)

    students = User.objects.filter(role='student').values(
        'id', 'username', 'first_name', 'last_name',
        'enrollment_no', 'branch_id', 'semester_id'
    )
    subjects = Subject.objects.select_related('teacher', 'semester').prefetch_related('branches').all()
    subject_data = []
    for s in subjects:
        branch_ids = [b.id for b in s.branches.all()]
        subject_data.append({
            'id': s.id,
            'name': s.name,
            'code': s.code,
            'teacher_name': s.teacher.get_full_name() or s.teacher.username,
            'branch_ids': branch_ids,
            'semester_id': s.semester_id,
            'semester_number': s.semester.number if s.semester else None,
        })

    return Response({
        'students': list(students),
        'subjects': subject_data,
    })
"""
    content = content[:enrollment_start] + new_enrollment_views

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    update_views()
