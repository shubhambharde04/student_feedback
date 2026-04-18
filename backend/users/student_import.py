import pandas as pd
import openpyxl
from io import BytesIO
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone

from .models import (
    User, FeedbackSession, StudentSemester, StudentProfile, 
    Branch, Semester
)
from .serializers import (
    UserSerializer, StudentSemesterSerializer, FeedbackSessionSerializer
)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_students(request):
    """
    Upload students from Excel/CSV file
    Required columns: enrollment_no, name, class, department (optional)
    """
    user = request.user
    
    # Only HOD and Admin can upload students
    if user.role not in ['hod', 'admin']:
        raise PermissionDenied("Only HOD and Admin can upload students")
    
    if 'file' not in request.FILES:
        return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
    
    session_id = request.data.get('session_id')
    if not session_id:
        return Response({'error': 'session_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Get session
    session = get_object_or_404(FeedbackSession, pk=session_id)
    
    # Validate session is active
    if not session.is_active:
        return Response({'error': 'Cannot upload students to inactive session'}, status=status.HTTP_400_BAD_REQUEST)
    
    file = request.FILES['file']
    
    # Validate file type
    if not file.name.endswith(('.csv', '.xlsx', '.xls')):
        return Response({'error': 'Only CSV and Excel files are allowed'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Parse file
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
        
        # Validate required columns
        required_columns = ['enrollment_no', 'name', 'class']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return Response({
                'error': f'Missing required columns: {", ".join(missing_columns)}',
                'required_columns': required_columns
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Clean and validate data
        df = df.dropna(subset=['enrollment_no', 'name', 'class'])
        df['enrollment_no'] = df['enrollment_no'].astype(str).str.strip()
        df['name'] = df['name'].astype(str).str.strip()
        df['class'] = df['class'].astype(str).str.strip()
        
        # Remove duplicates based on enrollment_no
        df = df.drop_duplicates(subset=['enrollment_no'], keep='first')
        
        # Process students
        results = process_student_upload(df, session, user)
        
        return Response({
            'message': 'Student upload completed successfully',
            'session': FeedbackSessionSerializer(session).data,
            'results': results
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({'error': f'Error processing file: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)


def process_student_upload(df, session, uploaded_by):
    """
    Process student data from DataFrame and create/update records
    """
    created_count = 0
    updated_count = 0
    error_count = 0
    errors = []
    
    with transaction.atomic():
        for index, row in df.iterrows():
            try:
                enrollment_no = str(row['enrollment_no']).strip()
                name = str(row['name']).strip()
                class_name = str(row['class']).strip()
                department = row.get('department', '')
                
                # Parse class name to extract branch and semester
                branch, semester = parse_class_name(class_name)
                if not branch or not semester:
                    errors.append({
                        'row': index + 1,
                        'enrollment_no': enrollment_no,
                        'error': f'Invalid class format: {class_name}. Expected format: "Branch-Semester" (e.g., "IT-1", "CSE-3")'
                    })
                    error_count += 1
                    continue
                
                # Get or create branch
                branch_obj, _ = Branch.objects.get_or_create(
                    code=branch,
                    defaults={'name': branch}
                )
                
                # Get or create semester
                semester_obj, _ = Semester.objects.get_or_create(
                    number=int(semester),
                    defaults={'name': f'Semester {semester}'}
                )
                
                # Get or create user
                username = enrollment_no
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'email': f'{username}@student.com',
                        'first_name': name.split()[0] if ' ' in name else name,
                        'last_name': ' '.join(name.split()[1:]) if ' ' in name else '',
                        'role': 'student',
                        'enrollment_no': enrollment_no,
                        'is_first_login': True
                    }
                )
                
                if created:
                    # Set default password
                    user.set_password(username)
                    user.save()
                    created_count += 1
                else:
                    # Update existing user
                    user.first_name = name.split()[0] if ' ' in name else name
                    user.last_name = ' '.join(name.split()[1:]) if ' ' in name else ''
                    user.role = 'student'
                    user.enrollment_no = enrollment_no
                    user.save()
                    updated_count += 1
                
                # Create or update student profile
                profile, _ = StudentProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'enrollment_no': enrollment_no
                    }
                )
                
                # Create or update student semester assignment
                student_semester, created = StudentSemester.objects.get_or_create(
                    student=user,
                    session=session,
                    defaults={
                        'branch': branch_obj,
                        'semester': semester_obj,
                        'class_name': class_name,
                        'is_active': True
                    }
                )
                
                if not created:
                    # Update existing assignment
                    student_semester.branch = branch_obj
                    student_semester.semester = semester_obj
                    student_semester.class_name = class_name
                    student_semester.is_active = True
                    student_semester.save()
                
            except Exception as e:
                errors.append({
                    'row': index + 1,
                    'enrollment_no': row.get('enrollment_no', 'Unknown'),
                    'error': str(e)
                })
                error_count += 1
                continue
    
    return {
        'total_rows': len(df),
        'created_students': created_count,
        'updated_students': updated_count,
        'error_rows': error_count,
        'errors': errors[:10]  # Return first 10 errors
    }


def parse_class_name(class_name):
    """
    Parse class name to extract branch and semester
    Examples: "IT-1", "CSE-3", "ECE-2A", "IT-1A"
    """
    try:
        # Remove spaces and convert to uppercase
        class_clean = class_name.replace(' ', '').upper()
        
        # Split by hyphen
        parts = class_clean.split('-')
        if len(parts) < 2:
            return None, None
        
        branch = parts[0]
        semester_part = parts[1]
        
        # Extract semester number (handle cases like "1A", "2B", etc.)
        semester = ''.join(filter(str.isdigit, semester_part))
        if not semester:
            return None, None
        
        # Validate semester range
        semester_num = int(semester)
        if semester_num < 1 or semester_num > 8:
            return None, None
        
        return branch, str(semester_num)
        
    except Exception:
        return None, None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_student_upload_template(request):
    """
    Get template format for student upload
    """
    template_data = {
        'columns': {
            'enrollment_no': {
                'required': True,
                'description': 'Unique enrollment number (will be used as username)',
                'example': '2024001'
            },
            'name': {
                'required': True,
                'description': 'Full name of the student',
                'example': 'John Doe'
            },
            'class': {
                'required': True,
                'description': 'Class in format: Branch-Semester (e.g., IT-1, CSE-3)',
                'example': 'IT-1'
            },
            'department': {
                'required': False,
                'description': 'Department name (optional)',
                'example': 'Information Technology'
            }
        },
        'example_data': [
            {
                'enrollment_no': '2024001',
                'name': 'John Doe',
                'class': 'IT-1',
                'department': 'Information Technology'
            },
            {
                'enrollment_no': '2024002',
                'name': 'Jane Smith',
                'class': 'CSE-1',
                'department': 'Computer Science'
            }
        ],
        'notes': [
            'enrollment_no must be unique across all students',
            'class format should be Branch-Semester (e.g., IT-1, CSE-3)',
            'Semester should be between 1-8',
            'Duplicate enrollment numbers will be updated',
            'Existing students will be updated with new information'
        ]
    }
    
    return Response(template_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_session_students(request, session_id):
    """
    Get all students assigned to a specific session
    """
    user = request.user
    
    if user.role not in ['hod', 'admin']:
        raise PermissionDenied("Only HOD and Admin can view session students")
    
    session = get_object_or_404(FeedbackSession, pk=session_id)
    
    # Get all student semesters for this session
    student_semesters = StudentSemester.objects.filter(
        session=session
    ).select_related('student', 'branch', 'semester').order_by('branch__name', 'semester__number', 'student__username')
    
    students_data = []
    for student_sem in student_semesters:
        try:
            profile = student_sem.student.student_profile_extended
        except:
            profile = None
        
        students_data.append({
            'student_id': student_sem.student.id,
            'username': student_sem.student.username,
            'name': student_sem.student.get_full_name(),
            'enrollment_no': student_sem.student.enrollment_no or profile.enrollment_no if profile else '',
            'branch': {
                'id': student_sem.branch.id,
                'name': student_sem.branch.name,
                'code': student_sem.branch.code
            },
            'semester': {
                'id': student_sem.semester.id,
                'number': student_sem.semester.number,
                'name': student_sem.semester.name
            },
            'class_name': student_sem.class_name,
            'roll_number': student_sem.roll_number,
            'is_active': student_sem.is_active,
            'created_at': student_sem.created_at
        })
    
    return Response({
        'session': FeedbackSessionSerializer(session).data,
        'students': students_data,
        'total_count': len(students_data)
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assign_student_to_session(request):
    """
    Manually assign a single student to a session
    """
    user = request.user
    
    if user.role not in ['hod', 'admin']:
        raise PermissionDenied("Only HOD and Admin can assign students")
    
    student_id = request.data.get('student_id')
    session_id = request.data.get('session_id')
    branch_id = request.data.get('branch_id')
    semester_id = request.data.get('semester_id')
    class_name = request.data.get('class_name', 'A')
    roll_number = request.data.get('roll_number', '')
    
    if not all([student_id, session_id, branch_id, semester_id]):
        return Response({'error': 'student_id, session_id, branch_id, and semester_id are required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        student = get_object_or_404(User, pk=student_id, role='student')
        session = get_object_or_404(FeedbackSession, pk=session_id)
        branch = get_object_or_404(Branch, pk=branch_id)
        semester = get_object_or_404(Semester, pk=semester_id)
        
        # Create or update student semester assignment
        student_semester, created = StudentSemester.objects.get_or_create(
            student=student,
            session=session,
            defaults={
                'branch': branch,
                'semester': semester,
                'class_name': class_name,
                'roll_number': roll_number,
                'is_active': True
            }
        )
        
        if not created:
            student_semester.branch = branch
            student_semester.semester = semester
            student_semester.class_name = class_name
            student_semester.roll_number = roll_number
            student_semester.is_active = True
            student_semester.save()
        
        return Response({
            'message': 'Student assigned to session successfully',
            'student_semester': StudentSemesterSerializer(student_semester).data
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_student_from_session(request, session_id, student_id):
    """
    Remove a student from a session
    """
    user = request.user
    
    if user.role not in ['hod', 'admin']:
        raise PermissionDenied("Only HOD and Admin can remove students")
    
    try:
        session = get_object_or_404(FeedbackSession, pk=session_id)
        student = get_object_or_404(User, pk=student_id, role='student')
        
        student_semester = get_object_or_404(
            StudentSemester,
            student=student,
            session=session
        )
        
        student_semester.delete()
        
        return Response({'message': 'Student removed from session successfully'})
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
