# type: ignore  # Django ORM uses dynamic attributes that static type checkers cannot validate
from rest_framework import viewsets, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.db import connection
from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.http import HttpResponse
from django.core.mail import EmailMessage
from django.shortcuts import get_object_or_404
from django.conf import settings
import csv
import io
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from django.db.models import Manager

from .models import (
    User, Subject, SubjectOffering, SubjectAssignment, 
    Feedback, FeedbackWindow, Branch, Semester,
    Department, StudentSemester, FeedbackSession
)
from .serializers import (
    BranchSerializer, SemesterSerializer, SubjectSerializer,
    SubjectOfferingSerializer, SubjectAssignmentSerializer,
    UserSerializer, FeedbackSerializer, FeedbackWindowSerializer,
    LoginSerializer, FeedbackWindowSerializer,
    ChangePasswordSerializer, SubjectOfferingCreateSerializer,
    TeacherAssignmentSerializer
)
from .sentiment import analyze_sentiment
from .observations import generate_key_observations


# ============================================================
# VIEWSETS
# ============================================================

class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        if self.request.user.role != 'hod':
            raise PermissionDenied("Only HOD can create subjects")
        serializer.save()

    def perform_update(self, serializer):
        if self.request.user.role != 'hod':
            raise PermissionDenied("Only HOD can update subjects")
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        if request.user.role != 'hod':
            raise PermissionDenied("Only HOD can delete subjects")
        return super().destroy(request, *args, **kwargs)


class FeedbackViewSet(viewsets.ModelViewSet):
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

    def get_queryset(self): # type: ignore
        if getattr(self, 'swagger_fake_view', False):
            return Feedback.objects.none()
            
        user = self.request.user
        if user.role == 'hod':
            return Feedback.objects.all().order_by('-created_at')
        if user.role == 'teacher':
            return Feedback.objects.filter(offering__assignment__teacher=user).order_by('-created_at')
        if user.role == 'student':
            return Feedback.objects.filter(student=user).order_by('-created_at')
        return Feedback.objects.none()


    def perform_create(self, serializer):
        comment = serializer.validated_data.get('comment', '')
        sentiment = analyze_sentiment(comment)
        serializer.save(sentiment=sentiment)

    def perform_update(self, serializer):
        raise PermissionDenied("Feedback cannot be edited once submitted")

    def destroy(self, request, *args, **kwargs):
        raise PermissionDenied("Feedback cannot be deleted")


@swagger_auto_schema(method='post', request_body=FeedbackSerializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def feedback_submit(request):
    """
    Robust feedback submission endpoint.
    Checks window, branch/semester, teacher assignment, and duplicates via serializer.
    """
    if request.user.role != 'student':
        return Response({'error': 'Only students can submit feedback'}, status=status.HTTP_403_FORBIDDEN)

    # DEBUG: Print submission data
    print(f"[feedback_submit] Student: {request.user.username}")
    print(f"[feedback_submit] Data: {request.data}")

    serializer = FeedbackSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        comment = serializer.validated_data.get('comment', '')
        sentiment = analyze_sentiment(comment)
        
        # Save feedback (Logic for student assignment is in serializer.validate)
        feedback = serializer.save(sentiment=sentiment)
        
        # DEBUG: Print saved feedback
        print(f"[feedback_submit] Saved feedback ID: {feedback.id}")
        print(f"[feedback_submit] Offering: {feedback.offering.subject.name} ({feedback.offering.branch.code} Sem {feedback.offering.semester.number})")
        print(f"[feedback_submit] Teacher: {feedback.teacher.username if feedback.teacher else 'None'}")
        
        return Response({
            "message": "Feedback submitted successfully",
            "data": {
                "subject": feedback.offering.subject.name,
                "teacher": serializer.get_teacher_name(feedback),
                "overall_rating": feedback.overall_rating
            }
        }, status=status.HTTP_201_CREATED)
        
    print(f"[feedback_submit] Validation errors: {serializer.errors}")
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
# AUTH VIEWS
# ============================================================

@swagger_auto_schema(method='post', request_body=LoginSerializer)
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '').strip()

    if not username or not password:
        return Response(
            {'error': 'Please provide username and password'},
            status=status.HTTP_400_BAD_REQUEST
        )

    print(f"LOGIN ATTEMPT: {username}")

    # For students, try to find by enrollment_no first
    user_obj = None
    try:
        # Check if this is an enrollment number (all digits)
        if username.isdigit():
            user_obj = User.objects.filter(enrollment_no=username).first()
            if user_obj:
                print(f"Found student by enrollment_no: {user_obj.username}")
                # DEBUG: Check password state
                print(f"  Password usable: {user_obj.has_usable_password()}")
                print(f"  check_password result: {user_obj.check_password(password)}")
                user = authenticate(request, username=user_obj.username, password=password)
            else:
                print(f"No student found with enrollment_no: {username}")
                user = authenticate(request, username=username, password=password)
        else:
            # For non-students or username-based login
            user = authenticate(request, username=username, password=password)
    except Exception as e:
        print(f"Authentication error: {e}")
        user = None

    if user:
        if not user.is_active:
            return Response(
                {'error': 'User account is inactive'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        refresh = RefreshToken.for_user(user)
        
        print(f"LOGIN SUCCESS: {user.username} (role: {user.role})")
        
        # Enforce student first login password change
        if user.role == 'student' and user.is_first_login:
            return Response({
                'error': 'Please change your password first',
                'force_password_change': True,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_first_login': user.is_first_login
                }
            }, status=status.HTTP_200_OK)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_first_login': user.is_first_login
            }
        })

    print(f"LOGIN FAILED: {username} - Invalid credentials")
    return Response(
        {'error': 'Invalid enrollment number or password'},
        status=status.HTTP_401_UNAUTHORIZED
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    Logout user by blacklisting the refresh token.
    Accepts refresh token in request body.
    """
    try:
        refresh_token = request.data.get('refresh')
        
        if not refresh_token:
            return Response(
                {'error': 'Refresh token is required for logout'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Blacklist the refresh token
        token = RefreshToken(refresh_token)
        token.blacklist()
        
        return Response({
            'message': 'Successfully logged out',
            'detail': 'Refresh token has been blacklisted'
        })
        
    except Exception as e:
        return Response(
            {'error': f'Logout failed: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )


@swagger_auto_schema(method='post', request_body=ChangePasswordSerializer)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    user = request.user
    old_password = request.data.get('old_password')
    new_password = request.data.get('new_password')

    print(f"PASSWORD CHANGE ATTEMPT: {user.username} (role: {user.role})")

    if not old_password or not new_password:
        return Response(
            {'error': 'Please provide both old and new passwords'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not user.check_password(old_password):
        print(f"FAILED: Incorrect old password for {user.username}")
        return Response(
            {'error': 'Incorrect old password'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if len(new_password) < 6:
        return Response(
            {'error': 'Password must be at least 6 characters long.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Use set_password to ensure proper hashing
    user.set_password(new_password)
    user.is_first_login = False
    user.save()
    
    print(f"SUCCESS: Password changed for {user.username}")

    return Response({'message': 'Password changed successfully'})


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Health check that also verifies MySQL connectivity."""
    result = {'status': 'ok'}
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        result['database'] = 'connected'
    except Exception as e:
        result['status'] = 'degraded'
        result['database'] = f'error: {str(e)}'
    return Response(result)


@api_view(['GET'])
@permission_classes([AllowAny])
def test_endpoint(request):
    return Response({'message': 'Server is working!', 'status': 'ok'})


# ============================================================
# USER PROFILE
# ============================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """Get current user profile"""
    return Response({
        'user': {
            'id': request.user.id,
            'username': request.user.username,
            'email': request.user.email,
            'role': request.user.role,
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'is_first_login': request.user.is_first_login
        }
    })


# ============================================================
# TEACHER MANAGEMENT (HOD-only)
# ============================================================

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def manage_teachers(request):
    """
    GET  → List all teachers (with department, designation, subject count)
    POST → Create a new teacher (HOD-only)
    """
    if request.user.role != 'hod':
        return Response({'error': 'Only HOD can manage teachers'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        teachers = User.objects.filter(role='teacher').select_related('department').order_by('first_name', 'last_name')
        from .serializers import TeacherListSerializer
        serializer = TeacherListSerializer(teachers, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        from .serializers import TeacherCreateSerializer
        serializer = TeacherCreateSerializer(data=request.data)
        if serializer.is_valid():
            teacher = serializer.save()
            print(f"[manage_teachers] Created teacher: {teacher.username} (email: {teacher.email})")
            return Response({
                'message': f'Teacher {teacher.get_full_name()} created successfully',
                'teacher': {
                    'id': teacher.id,
                    'username': teacher.username,
                    'email': teacher.email,
                    'first_name': teacher.first_name,
                    'last_name': teacher.last_name,
                    'full_name': teacher.get_full_name(),
                    'department': teacher.department_id,
                    'department_name': teacher.department.name if teacher.department else None,
                    'designation': teacher.designation,
                    'role': teacher.role,
                }
            }, status=status.HTTP_201_CREATED)
        
        print(f"[manage_teachers] Validation errors: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def teacher_detail(request, pk):
    """
    GET    → Get single teacher details
    PATCH  → Update teacher fields (first_name, last_name, email, department, designation)
    DELETE → Deactivate teacher (soft delete)
    """
    if request.user.role != 'hod':
        return Response({'error': 'Only HOD can manage teachers'}, status=status.HTTP_403_FORBIDDEN)

    try:
        teacher = User.objects.select_related('department').get(pk=pk, role='teacher')
    except User.DoesNotExist:
        return Response({'error': 'Teacher not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        from .serializers import TeacherListSerializer
        serializer = TeacherListSerializer(teacher)
        return Response(serializer.data)

    elif request.method == 'PATCH':
        allowed_fields = ['first_name', 'last_name', 'email', 'department', 'designation']
        updated = []

        for field in allowed_fields:
            if field in request.data:
                value = request.data[field]
                if field == 'email' and value != teacher.email:
                    # Validate email uniqueness
                    if User.objects.filter(email=value).exclude(pk=pk).exists():
                        return Response(
                            {'email': ['A user with this email already exists.']},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                if field == 'department':
                    from .models import Department
                    try:
                        dept = Department.objects.get(pk=value) if value else None
                        teacher.department = dept
                    except Department.DoesNotExist:
                        return Response({'department': ['Department not found.']}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    setattr(teacher, field, value)
                updated.append(field)

        if updated:
            teacher.save()
            print(f"[teacher_detail] Updated teacher {teacher.username}: {updated}")

        from .serializers import TeacherListSerializer
        serializer = TeacherListSerializer(teacher)
        return Response({
            'message': f'Teacher {teacher.get_full_name()} updated successfully',
            'teacher': serializer.data
        })

    elif request.method == 'DELETE':
        teacher_name = teacher.get_full_name() or teacher.username
        # Soft delete: deactivate the user
        teacher.is_active = False
        teacher.save(update_fields=['is_active'])
        print(f"[teacher_detail] Deactivated teacher: {teacher.username}")
        return Response({
            'message': f'Teacher {teacher_name} has been deactivated'
        }, status=status.HTTP_200_OK)


# ============================================================
# STUDENT VIEWS
# ============================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_student_subjects(request):
    """
    Return ONLY subjects the student is enrolled in dynamically based on branch and semester.
    """
    if request.user.role != 'student':
        return Response({'error': 'Only students allowed'}, status=403)

    try:
        # Find the enrollment for the active session
        enrollment = StudentSemester.objects.filter(
            student=request.user,
            session__is_active=True,
            is_active=True
        ).select_related('branch', 'semester', 'session').first()
        
        if not enrollment:
            # Fallback to latest enrollment if no active session
            enrollment = StudentSemester.objects.filter(
                student=request.user
            ).select_related('branch', 'semester', 'session').order_by('-created_at').first()
            
    except Exception:
        return Response([], status=200)
    
    if not enrollment:
        return Response([], status=200)

    offerings = SubjectOffering.objects.filter(
        branch=enrollment.branch,
        semester=enrollment.semester,
        is_active=True
    ).select_related('subject', 'branch', 'semester')

    data = []
    for offering in offerings:
        given = Feedback.objects.filter(
            student=request.user, offering=offering
        ).exists()
        
        teacher_name = "Unassigned"
        try:
            assignment = offering.assignment if hasattr(offering, 'assignment') and offering.assignment.is_active else None
            teacher_name = (assignment.teacher.get_full_name() or assignment.teacher.username) if assignment else "Unassigned"
        except Exception:
            teacher_name = "Unassigned"

        data.append({
            "subject_id": offering.subject.id,
            "offering_id": offering.id,
            "id": offering.id,
            "subject_name": offering.subject.name,
            "subject_code": offering.subject.code,
            "teacher": teacher_name,
            "branch": offering.branch.name,
            "semester": offering.semester.number,
            "feedback_submitted": given
        })

    print(f"[student/subjects] Returning {len(data)} subjects for {request.user.username}")
    return Response(data)


# ============================================================
# TEACHER VIEWS
# ============================================================

def _get_performance_label(avg_rating):
    if avg_rating is None:
        return "No Feedback"
    if avg_rating >= 4:
        return "Excellent"
    if avg_rating >= 3:
        return "Good"
    if avg_rating >= 2:
        return "Average"
    return "Poor"


def _get_sentiment_summary(feedbacks):
    """Return counts of positive, neutral, negative for a queryset."""
    return {
        'positive': feedbacks.filter(sentiment='positive').count(),
        'neutral': feedbacks.filter(sentiment='neutral').count(),
        'negative': feedbacks.filter(sentiment='negative').count(),
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_dashboard(request):
    if request.user.role != 'teacher': return Response({'error': 'Only teachers allowed'}, status=403)
    
    # PARAMETERS
    view_mode = request.query_params.get('view', 'combined')
    curr_sem_id = request.query_params.get('curr_sem')
    prev_sem_id = request.query_params.get('prev_sem')
    
    # Determine current semester if not provided
    if not curr_sem_id:
        active_assign = SubjectAssignment.objects.filter(teacher=request.user, is_active=True).first()
        if active_assign:
            curr_sem_id = active_assign.offering.semester.id

    # Base offerings for comparison logic (for the teacher)
    teacher_all_offerings = SubjectOffering.objects.filter(assignment__teacher=request.user)
    
    # Filter current offerings based on semester
    if curr_sem_id:
        current_offerings = teacher_all_offerings.filter(semester_id=curr_sem_id)
    else:
        current_offerings = teacher_all_offerings.filter(assignment__is_active=True)

    data = []

    if view_mode == 'combined':
        # UNIQUE SUBJECTS in current semester
        subjects = Subject.objects.filter(offerings__in=current_offerings).distinct()
        
        for subject in subjects:
            # CURRENT DATA
            curr_feedbacks = Feedback.objects.filter(offering__in=current_offerings, offering__subject=subject)
            curr_agg = curr_feedbacks.aggregate(
                avg_punctuality=Avg('punctuality_rating'), avg_teaching=Avg('teaching_rating'),
                avg_clarity=Avg('clarity_rating'), avg_interaction=Avg('interaction_rating'),
                avg_behavior=Avg('behavior_rating'), avg_overall=Avg('overall_rating')
            )
            curr_avg = curr_agg['avg_overall'] or 0

            # PREVIOUS DATA
            prev_avg = 0
            if prev_sem_id:
                prev_offerings = teacher_all_offerings.filter(semester_id=prev_sem_id, subject=subject)
                prev_feedbacks = Feedback.objects.filter(offering__in=prev_offerings)
                prev_avg = prev_feedbacks.aggregate(avg=Avg('overall_rating'))['avg'] or 0

            # Calculate Trend
            diff = round(curr_avg - prev_avg, 2) if (curr_avg and prev_avg) else 0
            trend = "same"
            if not prev_avg and curr_avg: trend = "new"
            elif diff > 0.05: trend = "up"
            elif diff < -0.05: trend = "down"

            data.append({
                "subject_id": subject.id,
                "subject_name": subject.name, 
                "subject_code": subject.code,
                "feedback_count": curr_feedbacks.count(),
                "performance": _get_performance_label(curr_avg if curr_avg > 0 else None),
                "sentiment_summary": _get_sentiment_summary(curr_feedbacks),
                "prev_avg": round(prev_avg, 2),
                "difference": diff,
                "trend": trend,
                **{k: round(v or 0, 2) for k, v in curr_agg.items()}
            })
    else:
        # CLASS-WISE (per offering)
        for offering in current_offerings:
            # CURRENT DATA
            curr_feedbacks = Feedback.objects.filter(offering=offering)
            curr_agg = curr_feedbacks.aggregate(
                avg_punctuality=Avg('punctuality_rating'), avg_teaching=Avg('teaching_rating'),
                avg_clarity=Avg('clarity_rating'), avg_interaction=Avg('interaction_rating'),
                avg_behavior=Avg('behavior_rating'), avg_overall=Avg('overall_rating')
            )
            curr_avg = curr_agg['avg_overall'] or 0

            # PREVIOUS DATA (Match by Subject + Branch in Previous Semester)
            prev_avg = 0
            if prev_sem_id:
                prev_offering = teacher_all_offerings.filter(
                    semester_id=prev_sem_id, 
                    subject=offering.subject,
                    branch=offering.branch
                ).first()
                if prev_offering:
                    prev_avg = Feedback.objects.filter(offering=prev_offering).aggregate(avg=Avg('overall_rating'))['avg'] or 0

            # Calculate Trend
            diff = round(curr_avg - prev_avg, 2) if (curr_avg and prev_avg) else 0
            trend = "same"
            if not prev_avg and curr_avg: trend = "new"
            elif diff > 0.05: trend = "up"
            elif diff < -0.05: trend = "down"

            name_suffix = f" ({offering.branch.code} Sem {offering.semester.number})"
            data.append({
                "subject_id": offering.id,
                "subject_name": offering.subject.name + name_suffix, 
                "subject_code": offering.subject.code,
                "feedback_count": curr_feedbacks.count(),
                "performance": _get_performance_label(curr_avg if curr_avg > 0 else None),
                "sentiment_summary": _get_sentiment_summary(curr_feedbacks),
                "prev_avg": round(prev_avg, 2),
                "difference": diff,
                "trend": trend,
                **{k: round(v or 0, 2) for k, v in curr_agg.items()}
            })

    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_performance(request):
    if request.user.role != 'teacher': return Response({'error': 'Only teachers allowed'}, status=403)
    
    curr_sem_id = request.query_params.get('curr_sem')
    
    # Base filter
    offerings_query = SubjectOffering.objects.filter(assignment__teacher=request.user)
    
    if curr_sem_id:
        offerings = offerings_query.filter(semester_id=curr_sem_id)
    else:
        offerings = offerings_query.filter(assignment__is_active=True)
        
    all_feedback = Feedback.objects.filter(offering__in=offerings)
    
    overall_avg = round(all_feedback.aggregate(avg=Avg('overall_rating'))['avg'] or 0, 2)
    view_mode = request.query_params.get('view', 'combined')
    subject_performance = []
    
    if view_mode == 'combined':
        subjects = Subject.objects.filter(offerings__in=offerings).distinct()
        for subject in subjects:
            feedbacks = Feedback.objects.filter(offering__in=offerings, offering__subject=subject)
            avg = feedbacks.aggregate(avg=Avg('overall_rating'))['avg']
            subject_performance.append({
                "subject_name": subject.name, "subject_code": subject.code,
                "avg_overall": round(avg or 0, 2), "feedback_count": feedbacks.count(),
                "performance": _get_performance_label(avg),
            })
    else:
        for offering in offerings:
            feedbacks = Feedback.objects.filter(offering=offering)
            avg = feedbacks.aggregate(avg=Avg('overall_rating'))['avg']
            name_suffix = f" ({offering.branch.code} Sem {offering.semester.number})"
            subject_performance.append({
                "subject_name": offering.subject.name + name_suffix, "subject_code": offering.subject.code,
                "avg_overall": round(avg or 0, 2), "feedback_count": feedbacks.count(),
                "performance": _get_performance_label(avg),
            })

    return Response({
        "subject_performance": subject_performance,
        "overall_average": overall_avg,
        "overall_performance": _get_performance_label(overall_avg if overall_avg > 0 else None),
        "total_feedback": all_feedback.count(),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_analytics(request):
    if request.user.role != 'teacher': return Response({'error': 'Only teachers allowed'}, status=403)
    offerings = SubjectOffering.objects.filter(assignment__teacher=request.user, assignment__is_active=True)
    data = []
    for offering in offerings:
        feedbacks = Feedback.objects.filter(offering=offering)
        avg = feedbacks.aggregate(Avg('overall_rating'))['overall_rating__avg']
        data.append({
            "subject_name": f"{offering.subject.name} ({offering.branch.code} Sem {offering.semester.number})",
            "subject_code": offering.subject.code,
            "average_rating": round(avg, 2) if avg else None,
            "feedback_count": feedbacks.count()
        })
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_performance_charts(request):
    """Return chart-ready data for the teacher performance dashboard."""
    if request.user.role != 'teacher': return Response({'error': 'Only teachers allowed'}, status=403)
    
    curr_sem_id = request.query_params.get('curr_sem')
    offerings_query = SubjectOffering.objects.filter(assignment__teacher=request.user)
    
    if curr_sem_id:
        offerings = offerings_query.filter(semester_id=curr_sem_id)
    else:
        offerings = offerings_query.filter(assignment__is_active=True)
        
    all_feedback = Feedback.objects.filter(offering__in=offerings)
    view_mode = request.query_params.get('view', 'combined')

    subject_labels, subject_values = [], []
    if view_mode == 'combined':
        subjects = Subject.objects.filter(offerings__in=offerings).distinct()
        for subject in subjects:
            avg = Feedback.objects.filter(offering__in=offerings, offering__subject=subject).aggregate(avg=Avg('overall_rating'))['avg']
            subject_labels.append(subject.name)
            subject_values.append(round(avg or 0, 2))
    else:
        for offering in offerings:
            avg = Feedback.objects.filter(offering=offering).aggregate(avg=Avg('overall_rating'))['avg']
            name_suffix = f" {offering.branch.code} S{offering.semester.number}"
            subject_labels.append(offering.subject.name + name_suffix)
            subject_values.append(round(avg or 0, 2))

    cat_agg = all_feedback.aggregate(
        avg_punctuality=Avg('punctuality_rating'), avg_teaching=Avg('teaching_rating'),
        avg_clarity=Avg('clarity_rating'), avg_interaction=Avg('interaction_rating'),
        avg_behavior=Avg('behavior_rating')
    )
    category_labels = ['Punctuality', 'Teaching', 'Clarity', 'Interaction', 'Behavior']
    category_values = [round(cat_agg[f'avg_{k.lower()}'] or 0, 2) for k in category_labels]

    total = all_feedback.count()
    excellent = all_feedback.filter(overall_rating__gte=4).count()
    good = all_feedback.filter(overall_rating__gte=3, overall_rating__lt=4).count()
    average = all_feedback.filter(overall_rating__gte=2, overall_rating__lt=3).count()
    poor = all_feedback.filter(overall_rating__lt=2).count()

    try:
        monthly = all_feedback.annotate(month=TruncMonth('created_at')).values('month').annotate(avg_rating=Avg('overall_rating')).order_by('month')
        trend_labels = [entry['month'].strftime('%b %Y') for entry in monthly[-6:]]
        trend_values = [round(entry['avg_rating'] or 0, 2) for entry in monthly[-6:]]
    except Exception:
        trend_labels, trend_values = ['No Data'], [0]

    return Response({
        'subject_ratings': {'labels': subject_labels, 'values': subject_values},
        'category_averages': {'labels': category_labels, 'values': category_values},
        'rating_distribution': {'labels': ['Excellent (4-5)', 'Good (3-4)', 'Average (2-3)', 'Poor (1-2)'], 'values': [excellent, good, average, poor]},
        'monthly_trend': {'labels': trend_labels or ['No Data'], 'values': trend_values or [0]},
        'total_feedback': total,
    })


# ============================================================
# FEEDBACK WINDOW VIEWS
# ============================================================

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def feedback_window_manager(request):
    if request.user.role != 'hod':
        return Response({'error': 'Only HOD can manage feedback windows'}, status=403)

    if request.method == 'GET':
        windows = FeedbackWindow.objects.all().order_by('-start_date')
        serializer = FeedbackWindowSerializer(windows, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        FeedbackWindow.objects.all().update(is_active=False)
        serializer = FeedbackWindowSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(is_active=True)
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)


@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def feedback_window_detail(request, pk):
    if request.user.role != 'hod':
        return Response({'error': 'Only HOD can manage feedback windows'}, status=403)

    try:
        window = FeedbackWindow.objects.get(pk=pk)
    except FeedbackWindow.DoesNotExist:
        return Response({'error': 'Feedback window not found'}, status=404)

    if request.method == 'PUT':
        if request.data.get('is_active', False):
            FeedbackWindow.objects.exclude(pk=pk).update(is_active=False)
        serializer = FeedbackWindowSerializer(window, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    elif request.method == 'DELETE':
        window.delete()
        return Response(status=204)


@api_view(['GET'])
@permission_classes([AllowAny])
def current_feedback_window(request):
    try:
        window = FeedbackWindow.objects.filter(is_active=True).first()
        if not window:
            return Response({
                'active': False,
                'message': 'No active feedback window',
                'window': None
            }, status=status.HTTP_200_OK)
        
        now = timezone.now()
        if not (window.start_date <= now <= window.end_date):
            return Response({
                'active': False,
                'message': 'Feedback window is closed',
                'window': None
            }, status=status.HTTP_200_OK)
        
        serializer = FeedbackWindowSerializer(window)
        return Response({
            'active': True,
            'message': 'Feedback window is open',
            'window': serializer.data
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'active': False,
            'message': 'Server error',
            'window': None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================
# HOD VIEWS
# ============================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hod_dashboard_overview(request):
    if request.user.role != 'hod':
        return Response({'error': 'Only HOD allowed'}, status=403)

    total_feedback = Feedback.objects.count()
    total_teachers = User.objects.filter(role='teacher').count()
    total_subjects = Subject.objects.count()
    avg_rating = Feedback.objects.aggregate(
        avg=Avg('overall_rating')
    )['avg']

    # Top & lowest teacher
    teachers = User.objects.filter(role='teacher')
    teacher_ratings = []
    for teacher in teachers:
        t_avg = Feedback.objects.filter(
            offering__assignment__teacher=teacher,
            offering__assignment__is_active=True
        ).aggregate(avg=Avg('overall_rating'))['avg']
        if t_avg is not None:
            teacher_ratings.append({
                'id': teacher.id,
                'name': teacher.get_full_name() or teacher.username,
                'email': teacher.email,
                'avg_rating': round(t_avg, 2),
            })

    teacher_ratings.sort(key=lambda x: x['avg_rating'], reverse=True)

    return Response({
        "total_feedback": total_feedback,
        "total_teachers": total_teachers,
        "total_subjects": total_subjects,
        "average_rating": round(avg_rating, 2) if avg_rating else 0,
        "top_teacher": teacher_ratings[0] if teacher_ratings else None,
        "lowest_teacher": teacher_ratings[-1] if teacher_ratings else None,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hod_teachers(request):
    if request.user.role != 'hod':
        return Response({'error': 'Only HOD allowed'}, status=403)

    teachers = User.objects.filter(role='teacher')
    data = []

    for teacher in teachers:
        subjects = Subject.objects.filter(offerings__assignment__teacher=teacher, offerings__assignment__is_active=True).distinct()
        feedbacks = Feedback.objects.filter(offering__assignment__teacher=teacher, offering__assignment__is_active=True)
        avg = feedbacks.aggregate(avg=Avg('overall_rating'))['avg']

        data.append({
            'id': teacher.id,
            'name': teacher.get_full_name() or teacher.username,
            'username': teacher.username,
            'email': teacher.email,
            'subject_count': subjects.count(),
            'feedback_count': feedbacks.count(),
            'avg_rating': round(avg, 2) if avg else 0,
            'performance': _get_performance_label(avg),
        })

    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hod_teacher_detail(request, pk):
    if request.user.role != 'hod':
        return Response({'error': 'Only HOD allowed'}, status=403)

    try:
        teacher = User.objects.get(pk=pk, role='teacher')
    except User.DoesNotExist:
        return Response({'error': 'Teacher not found'}, status=404)

    subjects = Subject.objects.filter(offerings__assignment__teacher=teacher, offerings__assignment__is_active=True).distinct()
    subject_data = []

    all_feedback = Feedback.objects.filter(offering__assignment__teacher=teacher, offering__assignment__is_active=True)
    overall_avg = all_feedback.aggregate(avg=Avg('overall_rating'))['avg']

    for subject in subjects:
        feedbacks = Feedback.objects.filter(offering__subject=subject, offering__assignment__teacher=teacher, offering__assignment__is_active=True)
        agg = feedbacks.aggregate(
            avg_punctuality=Avg('punctuality_rating'),
            avg_teaching=Avg('teaching_rating'),
            avg_clarity=Avg('clarity_rating'),
            avg_interaction=Avg('interaction_rating'),
            avg_behavior=Avg('behavior_rating'),
            avg_overall=Avg('overall_rating'),
        )

        subject_data.append({
            'subject_id': subject.id,
            'subject_name': subject.name,
            'subject_code': subject.code,
            'feedback_count': feedbacks.count(),
            'avg_punctuality': round(agg['avg_punctuality'] or 0, 2),
            'avg_teaching': round(agg['avg_teaching'] or 0, 2),
            'avg_clarity': round(agg['avg_clarity'] or 0, 2),
            'avg_interaction': round(agg['avg_interaction'] or 0, 2),
            'avg_behavior': round(agg['avg_behavior'] or 0, 2),
            'avg_overall': round(agg['avg_overall'] or 0, 2),
            'performance': _get_performance_label(agg['avg_overall']),
            'sentiment_summary': _get_sentiment_summary(feedbacks),
        })

    return Response({
        'teacher': {
            'id': teacher.id,
            'name': teacher.get_full_name() or teacher.username,
            'username': teacher.username,
            'email': teacher.email,
        },
        'subjects': subject_data,
        'overall_avg': round(overall_avg, 2) if overall_avg else 0,
        'overall_performance': _get_performance_label(overall_avg),
        'total_feedback': all_feedback.count(),
        'sentiment_summary': _get_sentiment_summary(all_feedback),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def hod_send_report(request):
    if request.user.role != 'hod':
        return Response({'error': 'Only HOD allowed'}, status=403)

    teacher_id = request.data.get('teacher_id')
    if not teacher_id:
        return Response({'error': 'teacher_id is required'}, status=400)

    try:
        teacher = User.objects.get(pk=teacher_id, role='teacher')
    except User.DoesNotExist:
        return Response({'error': 'Teacher not found'}, status=404)

    subjects = Subject.objects.filter(offerings__assignment__teacher=teacher, offerings__assignment__is_active=True).distinct()
    all_feedback = Feedback.objects.filter(offering__assignment__teacher=teacher, offering__assignment__is_active=True)
    overall_avg = all_feedback.aggregate(avg=Avg('overall_rating'))['avg']

    # Build email body
    lines = [
        f"Dear {teacher.get_full_name() or teacher.username},\n",
        "This is your automated performance feedback report.\n",
        "=" * 50,
    ]

    for subject in subjects:
        feedbacks = Feedback.objects.filter(offering__subject=subject, offering__assignment__teacher=teacher, offering__assignment__is_active=True)
        avg = feedbacks.aggregate(avg=Avg('overall_rating'))['avg']
        sentiment = _get_sentiment_summary(feedbacks)
        performance = _get_performance_label(avg)

        lines.append(f"\nSubject: {subject.name} ({subject.code})")
        lines.append(f"  Average Rating: {round(avg, 2) if avg else 'N/A'} / 5.0")
        lines.append(f"  Feedback Count: {feedbacks.count()}")
        lines.append(f"  Performance: {performance}")
        lines.append(f"  Sentiment: 😊 {sentiment['positive']}  😐 {sentiment['neutral']}  😞 {sentiment['negative']}")

    lines.append(f"\n{'=' * 50}")
    lines.append(f"Overall Average: {round(overall_avg, 2) if overall_avg else 'N/A'} / 5.0")
    lines.append(f"Overall Performance: {_get_performance_label(overall_avg)}")

    suggestions = []
    if overall_avg and overall_avg < 3:
        suggestions.append("• Focus on improving clarity and interaction with students")
        suggestions.append("• Consider adopting more interactive teaching methods")
    elif overall_avg and overall_avg < 4:
        suggestions.append("• Good performance! Try to increase engagement further")
    else:
        suggestions.append("• Excellent work! Keep up the great teaching")

    lines.append("\nSuggestions:")
    lines.extend(suggestions)

    lines.append(f"\nGenerated on: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Sent by: {request.user.get_full_name() or request.user.username} (HOD)")

    email_body = "\n".join(lines)

    try:
        email = EmailMessage(
            f"Performance Feedback Report - {teacher.get_full_name() or teacher.username}",
            email_body,
            settings.DEFAULT_FROM_EMAIL,
            [teacher.email],
        )
        email.send()
        return Response({'message': f'Report sent successfully to {teacher.email}'})
    except Exception as e:
        return Response({'error': f'Failed to send email: {str(e)}'}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def hod_send_custom_email(request):
    """Send custom email from HOD to a teacher"""
    if request.user.role != 'hod':
        return Response({'error': 'Only HOD can send emails'}, status=403)

    teacher_id = request.data.get('teacher_id')
    subject = request.data.get('subject')
    message = request.data.get('message')
    
    if not teacher_id or not subject or not message:
        return Response({
            'error': 'teacher_id, subject, and message are required'
        }, status=400)

    teacher = User.objects.filter(pk=teacher_id, role='teacher').first()
    if not teacher:
        return Response({'error': 'Teacher not found'}, status=404)

    try:
        email = EmailMessage(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [teacher.email],
        )
        email.send()
        return Response({
            'message': f'Email sent successfully to {teacher.email}',
            'teacher_name': teacher.get_full_name() or teacher.username
        })
    except Exception as e:
        return Response({
            'error': f'Failed to send email: {str(e)}'
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hod_analytics(request):
    if request.user.role != 'hod':
        return Response({'error': 'Only HOD allowed'}, status=403)

    # Teacher ranking
    teachers = User.objects.filter(role='teacher')
    ranking = []
    for teacher in teachers:
        feedbacks = Feedback.objects.filter(offering__assignment__teacher=teacher, offering__assignment__is_active=True)
        avg = feedbacks.aggregate(avg=Avg('overall_rating'))['avg']
        if avg is not None:
            ranking.append({
                'id': teacher.id,
                'name': teacher.get_full_name() or teacher.username,
                'avg_rating': round(avg, 2),
                'feedback_count': feedbacks.count(),
                'performance': _get_performance_label(avg),
            })
    ranking.sort(key=lambda x: x['avg_rating'], reverse=True)

    # Subject performance
    subjects = Subject.objects.prefetch_related('offerings__assignment__teacher').all()
    subject_performance = []
    for subject in subjects:
        feedbacks = Feedback.objects.filter(offering__subject=subject)
        avg = feedbacks.aggregate(avg=Avg('overall_rating'))['avg']
        teachers = list(set(
            assign.teacher.get_full_name() or assign.teacher.username 
            for off in subject.offerings.all() 
            for assign in ([off.assignment] if hasattr(off, 'assignment') and off.assignment.is_active else [])
        ))
        teacher_names = ", ".join(teachers) if teachers else "Unassigned"
        subject_performance.append({
            'subject_name': subject.name,
            'subject_code': subject.code,
            'teacher': teacher_names,
            'avg_rating': round(avg, 2) if avg else 0,
            'feedback_count': feedbacks.count(),
        })

    # Rating distribution (1-5)
    all_feedback = Feedback.objects.all()
    rating_distribution = {}
    for i in range(1, 6):
        # Count based on rounded overall_rating
        rating_distribution[str(i)] = all_feedback.filter(
            overall_rating__gte=i - 0.5, overall_rating__lt=i + 0.5
        ).count()

    # Sentiment distribution
    sentiment_distribution = _get_sentiment_summary(all_feedback)

    # Department average
    dept_avg = all_feedback.aggregate(avg=Avg('overall_rating'))['avg']

    return Response({
        'teacher_ranking': ranking,
        'subject_performance': subject_performance,
        'rating_distribution': rating_distribution,
        'sentiment_distribution': sentiment_distribution,
        'department_average': round(dept_avg, 2) if dept_avg else 0,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hod_statistics(request):
    if request.user.role != 'hod':
        return Response({'error': 'Only HOD allowed'}, status=403)

    subjects = Subject.objects.prefetch_related('offerings__assignment__teacher').all()
    stats = []

    for subject in subjects:
        feedbacks = Feedback.objects.filter(offering__subject=subject)
        agg = feedbacks.aggregate(
            avg_overall=Avg('overall_rating'),
            avg_punctuality=Avg('punctuality_rating'),
            avg_teaching=Avg('teaching_rating'),
            avg_clarity=Avg('clarity_rating'),
            avg_interaction=Avg('interaction_rating'),
            avg_behavior=Avg('behavior_rating'),
        )
        teachers = list(set(
            assign.teacher.get_full_name() or assign.teacher.username 
            for off in subject.offerings.all() 
            for assign in ([off.assignment] if hasattr(off, 'assignment') and off.assignment.is_active else [])
        ))
        teacher_names = ", ".join(teachers) if teachers else "Unassigned"

        stats.append({
            "subject": subject.name,
            "subject_code": subject.code,
            "teacher": teacher_names,
            "total_feedback": feedbacks.count(),
            "avg_overall": round(agg['avg_overall'] or 0, 2),
            "avg_punctuality": round(agg['avg_punctuality'] or 0, 2),
            "avg_teaching": round(agg['avg_teaching'] or 0, 2),
            "avg_clarity": round(agg['avg_clarity'] or 0, 2),
            "avg_interaction": round(agg['avg_interaction'] or 0, 2),
            "avg_behavior": round(agg['avg_behavior'] or 0, 2),
            "sentiment_summary": _get_sentiment_summary(feedbacks),
        })

    # Calculate pending feedback (students who haven't submitted for all subjects)
    total_students = User.objects.filter(role='student').count()
    total_teachers = User.objects.filter(role='teacher').count()
    total_feedback = Feedback.objects.count()
    total_subjects = Subject.objects.count()
    # Pending = (total_students * total_subjects) - total_feedback
    pending_feedback = max((total_students * total_subjects) - total_feedback, 0)

    return Response({
        'summary': {
            'total_students': total_students,
            'total_teachers': total_teachers,
            'total_feedback': total_feedback,
            'total_subjects': total_subjects,
            'pending_feedback': pending_feedback,
        },
        'details': stats,
    })


# ============================================================
# LEGACY HOD VIEWS (updated)
# ============================================================

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def hod_report(request):
    if request.user.role != 'hod':
        return Response({'error': 'Only HOD allowed'}, status=403)

    offerings = SubjectOffering.objects.prefetch_related('assignment__teacher').all()
    report = []

    for offering in offerings:
        feedbacks = Feedback.objects.filter(offering=offering)
        avg = feedbacks.aggregate(avg=Avg('overall_rating'))['avg']
        assignment = offering.assignment if hasattr(offering, 'assignment') and offering.assignment.is_active else None
        teacher = assignment.teacher if assignment else None

        report.append({
            "subject": f"{offering.subject.name} ({offering.branch.code} Sem {offering.semester.number})",
            "subject_code": offering.subject.code,
            "teacher": teacher.get_full_name() or teacher.username if teacher else "Unassigned",
            "teacher_email": teacher.email if teacher else "",
            "feedback_count": feedbacks.count(),
            "average_rating": round(avg, 2) if avg else None,
            "performance": _get_performance_label(avg),
            "sentiment_summary": _get_sentiment_summary(feedbacks),
        })

    if request.method == 'POST':
        try:
            teacher_email = request.data.get('teacher_email')
            subject_name = request.data.get('subject_name')

            if not teacher_email or not subject_name:
                return Response({'error': 'Teacher email and subject name are required'}, status=400)

            teacher_report = next(
                (r for r in report if r['teacher_email'] == teacher_email and r['subject'] == subject_name),
                None
            )
            if not teacher_report:
                return Response({'error': 'No report found for the specified teacher and subject'}, status=404)

            email_subject = f"Feedback Report for {subject_name}"
            avg_display = f"{teacher_report['average_rating']:.2f}" if teacher_report['average_rating'] else 'N/A'
            email_body = f"""
Dear Teacher,

This is an automated feedback report for your subject: {subject_name}

Report Summary:
- Total Feedback Received: {teacher_report['feedback_count']}
- Average Rating: {avg_display} / 5.0
- Performance: {teacher_report['performance']}

Generated on: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}

Best regards,
HOD {request.user.first_name or request.user.username}
"""

            email = EmailMessage(
                email_subject,
                email_body,
                settings.DEFAULT_FROM_EMAIL,
                [teacher_email],
            )
            email.send()
            return Response({'message': f'Report sent successfully to {teacher_email}'})

        except Exception as e:
            return Response({'error': f'Failed to send email: {str(e)}'}, status=500)

    return Response(report)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def feedback_statistics(request):
    if request.user.role != 'hod':
        return Response({'error': 'Only HOD allowed'}, status=403)
    return hod_statistics(request)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def feedback_analysis(request):
    if request.user.role != 'hod':
        return Response({'error': 'Only HOD allowed'}, status=403)

    subjects = Subject.objects.prefetch_related('offerings__assignment__teacher').all()
    analysis = []

    for subject in subjects:
        feedbacks = Feedback.objects.filter(offering__subject=subject)
        avg = feedbacks.aggregate(Avg('overall_rating'))['overall_rating__avg']
        total = feedbacks.count()
        teachers = list(set(
            assign.teacher.get_full_name() or assign.teacher.username 
            for off in subject.offerings.all() 
            for assign in ([off.assignment] if hasattr(off, 'assignment') and off.assignment.is_active else [])
        ))
        teacher_names = ", ".join(teachers) if teachers else "Unassigned"

        analysis.append({
            "subject": subject.name,
            "subject_code": subject.code,
            "teacher": teacher_names,
            "total_feedback": total,
            "average_rating": round(avg, 2) if avg else None,
            "performance": _get_performance_label(avg),
        })

    return Response(analysis)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_ranking(request):
    if request.user.role != 'hod':
        return Response({'error': 'Only HOD allowed'}, status=403)

    teachers = User.objects.filter(role='teacher')
    ranking = []

    for teacher in teachers:
        avg = Feedback.objects.filter(
            subject__teacher=teacher
        ).aggregate(avg=Avg('overall_rating'))['avg']

        if avg is not None:
            ranking.append({
                "id": teacher.id,
                "teacher": teacher.get_full_name() or teacher.username,
                "average_rating": round(avg, 2),
            })

    if not ranking:
        return Response({"message": "No feedback available yet"})

    ranking_sorted = sorted(ranking, key=lambda x: x["average_rating"], reverse=True)

    return Response({
        "top_teacher": ranking_sorted[0],
        "lowest_teacher": ranking_sorted[-1],
        "all_teachers_ranking": ranking_sorted
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_analytics(request):
    if request.user.role != 'hod':
        return Response({'error': 'Only HOD allowed'}, status=403)
    return hod_dashboard_overview(request)


# ============================================================
# PDF EXPORT
# ============================================================

def get_improvement(avg_rating):
    if avg_rating is None:
        return "No feedback available"
    if avg_rating >= 4:
        return "Excellent teaching. Continue the same approach."
    elif avg_rating >= 3:
        return "Good performance but improve student interaction."
    elif avg_rating >= 2:
        return "Average performance. Improve explanation clarity."
    else:
        return "Poor rating. Needs improvement in teaching and communication."


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_report(request):
    if request.user.role != 'hod':
        return Response({'error': 'Only HOD allowed'}, status=403)

    report_type = request.GET.get('type')
    target_id = request.GET.get('id')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="feedback_report.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    # Title
    p.setFont("Helvetica-Bold", 18)
    p.drawCentredString(width / 2, height - 50, "Student Feedback Report")
    p.setFont("Helvetica", 10)
    p.drawCentredString(width / 2, height - 70, f"Generated: {timezone.now().strftime('%Y-%m-%d %H:%M')}")

    y = height - 110

    offerings = SubjectOffering.objects.prefetch_related('assignment__teacher')
    
    if report_type == 'teacher' and target_id:
        offerings = offerings.filter(assignment__teacher_id=target_id)
        
    offerings = offerings.all()

    for offering in offerings:
        feedbacks = Feedback.objects.filter(offering=offering)
        agg = feedbacks.aggregate(
            avg_overall=Avg('overall_rating'),
            avg_punctuality=Avg('punctuality_rating'),
            avg_teaching=Avg('teaching_rating'),
            avg_clarity=Avg('clarity_rating'),
            avg_interaction=Avg('interaction_rating'),
            avg_behavior=Avg('behavior_rating'),
        )
        count = feedbacks.count()
        sentiment = _get_sentiment_summary(feedbacks)
        
        # Removed get_improvement call to prevent crashing
        suggestion = "Focus on interactive methods" if (agg['avg_overall'] or 0) < 3.5 else "Keep up the good work"

        if y < 150:
            p.showPage()
            y = height - 50

        p.setFont("Helvetica-Bold", 12)
        suffix = f"({offering.branch.code} Sem {offering.semester.number})"
        p.drawString(60, y, f"Subject: {offering.subject.name} {suffix}")
        y -= 18

        assignment = offering.assignment if hasattr(offering, 'assignment') and offering.assignment.is_active else None
        teacher = assignment.teacher if assignment else None
        teacher_name = teacher.get_full_name() or teacher.username if teacher else "Unassigned"

        p.setFont("Helvetica", 10)
        p.drawString(80, y, f"Teacher: {teacher_name}")
        y -= 16
        p.drawString(80, y, f"Total Feedback: {count}")
        y -= 16
        p.drawString(80, y, f"Overall Avg: {round(agg['avg_overall'] or 0, 2)}")
        y -= 16
        p.drawString(80, y, f"Punctuality: {round(agg['avg_punctuality'] or 0, 2)}  |  "
                              f"Teaching: {round(agg['avg_teaching'] or 0, 2)}  |  "
                              f"Clarity: {round(agg['avg_clarity'] or 0, 2)}")
        y -= 16
        p.drawString(80, y, f"Interaction: {round(agg['avg_interaction'] or 0, 2)}  |  "
                              f"Behavior: {round(agg['avg_behavior'] or 0, 2)}")
        y -= 16
        p.drawString(80, y, f"Sentiment: Pos {sentiment['positive']}, "
                              f"Neu {sentiment['neutral']}, Neg {sentiment['negative']}")
        y -= 16
        p.drawString(80, y, f"Suggestion: {suggestion}")
        y -= 30

    p.showPage()
    p.save()
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hod_teacher_report(request, pk):
    """
    GPN-Format Teacher Report: Feedback Analysis & Action Taken Report
    Returns per-offering quantitative analysis with 5 category averages,
    total score (out of 25), and percentage.
    
    Query params:
      - session: FeedbackSession ID (optional, defaults to latest active)
    """
    if request.user.role != 'hod':
        return Response({'error': 'Only HOD allowed'}, status=403)
    
    try:
        teacher = User.objects.get(pk=pk, role__in=['teacher', 'hod'])
    except User.DoesNotExist:
        return Response({'error': 'Teacher not found'}, status=404)

    # Determine session
    session_id = request.GET.get('session')
    if session_id:
        try:
            session = FeedbackSession.objects.get(pk=session_id)
        except FeedbackSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=404)
    else:
        session = FeedbackSession.objects.filter(is_active=True).order_by('-year').first()

    # Get department info from HOD
    department = request.user.department
    dept_name = department.name if department else "Department"

    # Get offerings assigned to this teacher
    offerings_qs = SubjectOffering.objects.filter(
        assignment__teacher=teacher,
        assignment__is_active=True
    ).select_related('subject', 'branch', 'semester')

    # Build session date filter for feedback
    session_fb_filter = {}
    if session:
        session_fb_filter['created_at__gte'] = session.start_date
        session_fb_filter['created_at__lte'] = session.end_date

    offerings_data = []
    all_fb_for_teacher = Feedback.objects.none()

    for offering in offerings_qs:
        fbs = Feedback.objects.filter(offering=offering, **session_fb_filter)
        all_fb_for_teacher = all_fb_for_teacher | fbs

        agg = fbs.aggregate(
            punctuality=Avg('punctuality_rating'),
            domain_knowledge=Avg('teaching_rating'),
            presentation_skills=Avg('clarity_rating'),
            resolve_difficulties=Avg('interaction_rating'),
            teaching_aids=Avg('behavior_rating'),
        )

        p = round(agg['punctuality'] or 0, 4)
        d = round(agg['domain_knowledge'] or 0, 4)
        pr = round(agg['presentation_skills'] or 0, 4)
        r = round(agg['resolve_difficulties'] or 0, 4)
        t = round(agg['teaching_aids'] or 0, 4)
        score = round(p + d + pr + r + t, 4)
        percentage = round((score / 25) * 100, 2) if score > 0 else 0

        # 📈 30% Threshold Logic: Calculate feedback vs enrollment
        total_enrolled = StudentSemester.objects.filter(
            branch=offering.branch,
            semester=offering.semester,
            session=session
        ).count()
        
        feedback_count = fbs.count()
        feedback_percentage = (feedback_count / total_enrolled * 100) if total_enrolled > 0 else 0
        threshold_met = feedback_percentage >= 30

        # Include all offerings that have AT LEAST 1 feedback, but data is only valid if threshold met
        if feedback_count > 0:
            offerings_data.append({
                "offering_id": offering.id,
                "course_name": offering.subject.name,
                "course_code": offering.subject.code,
                "branch_code": offering.branch.code,
                "semester_number": offering.semester.number,
                "semester_name": offering.semester.name,
                "feedback_count": feedback_count,
                "total_enrolled": total_enrolled,
                "feedback_percentage": round(feedback_percentage, 2),
                "threshold_met": threshold_met,
                "punctuality": p if threshold_met else None,
                "domain_knowledge": d if threshold_met else None,
                "presentation_skills": pr if threshold_met else None,
                "resolve_difficulties": r if threshold_met else None,
                "teaching_aids": t if threshold_met else None,
                "score": round(score, 4) if threshold_met else 0,
                "percentage": percentage if threshold_met else 0,
            })

    # Check if any data exists for this session
    total_count = all_fb_for_teacher.count()
    data_available = total_count > 0

    # Past feedback comparison — find previous session
    past_percentage = None
    past_session_name = None
    if session:
        prev_sessions = FeedbackSession.objects.filter(
            year__lt=session.year
        ).order_by('-year', '-type')
        if not prev_sessions.exists():
            prev_sessions = FeedbackSession.objects.filter(
                year=session.year
            ).exclude(pk=session.pk).order_by('-type')
        
        prev_session = prev_sessions.first()
        if prev_session:
            past_session_name = prev_session.name
            # Check if there was feedback in the previous session period
            past_fb = Feedback.objects.filter(
                offering__assignment__teacher=teacher,
                offering__assignment__is_active=True,
                created_at__gte=prev_session.start_date,
                created_at__lte=prev_session.end_date,
            )
            if past_fb.exists():
                past_agg = past_fb.aggregate(
                    p=Avg('punctuality_rating'),
                    d=Avg('teaching_rating'),
                    c=Avg('clarity_rating'),
                    i=Avg('interaction_rating'),
                    b=Avg('behavior_rating'),
                )
                past_score = sum(round(v or 0, 4) for v in past_agg.values())
                past_percentage = round((past_score / 25) * 100, 2)

    # Determine semester label for session
    semester_label = ""
    if offerings_data:
        sem_nums = list(set(o['semester_number'] for o in offerings_data))
        if len(sem_nums) == 1:
            ordinals = {1: 'First', 2: 'Second', 3: 'Third', 4: 'Fourth', 5: 'Fifth', 6: 'Sixth', 7: 'Seventh', 8: 'Eighth'}
            semester_label = ordinals.get(sem_nums[0], f"Semester {sem_nums[0]}")
        else:
            semester_label = ", ".join(str(s) for s in sorted(sem_nums))

    # Strengths & Weaknesses
    cat_agg = all_fb_for_teacher.aggregate(
        punctuality=Avg('punctuality_rating'),
        teaching=Avg('teaching_rating'),
        clarity=Avg('clarity_rating'),
        interaction=Avg('interaction_rating'),
        behavior=Avg('behavior_rating'),
    )
    category_labels = {
        'punctuality': 'Punctuality & Discipline',
        'teaching': 'Domain Knowledge',
        'clarity': 'Presentation Skills',
        'interaction': 'Resolving Difficulties',
        'behavior': 'Teaching Aids',
    }
    categories = []
    for k, v in cat_agg.items():
        if v is not None:
            categories.append({"name": category_labels.get(k, k), "score": v})
    categories.sort(key=lambda x: x['score'], reverse=True)
    strengths = [c['name'] for c in categories[:2]] if categories else []
    weaknesses = [c['name'] for c in categories[-2:]] if len(categories) >= 3 else []

    return Response({
        "institution": "Government Polytechnic Nagpur",
        "department": f"{dept_name} Department",
        "session": session.name if session else "N/A",
        "session_type": session.type if session else "",
        "semester_label": semester_label,
        "data_available": data_available,
        "no_data_message": f"No feedback data available for session {session.name}." if (not data_available and session) else "",
        "teacher": {
            "id": teacher.id,
            "name": teacher.get_full_name() or teacher.username,
            "email": teacher.email,
        },
        "offerings": offerings_data,
        "total_feedback_count": total_count,
        "past_comparison": {
            "session_name": past_session_name,
            "percentage": past_percentage,
            "note": "Last Year, this subject was taught by other faculty." if past_percentage is None and past_session_name else "",
        },
        "strengths": strengths,
        "weaknesses": weaknesses,
        # Editable qualitative fields (defaults — HOD fills these in UI)
        # Automated Key Observations
        "key_observations": "\n".join(generate_key_observations(all_fb_for_teacher)),
        "corrective_action": "",
        "observation_status": "Pending",
        "faculty_response": "",
        "hod_comments": "",
        "conclusion": "",
        "report_date": timezone.now().strftime('%d/%m/%Y'),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hod_department_report(request):
    """
    GPN-Format Cumulative Class Report: All faculty for a branch+year
    
    Query params:
      - branch: Branch ID (optional)
      - year: Academic year number 1-4 (optional)
      - semester: Semester number (optional, overrides year)
      - session: FeedbackSession ID (optional, defaults to latest active)
    """
    if request.user.role != 'hod':
        return Response({'error': 'Only HOD allowed'}, status=403)

    # Determine session
    session_id = request.GET.get('session')
    if session_id:
        try:
            session = FeedbackSession.objects.get(pk=session_id)
        except FeedbackSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=404)
    else:
        session = FeedbackSession.objects.filter(is_active=True).order_by('-year').first()

    # Get department info
    department = request.user.department
    dept_name = department.name if department else "Department"

    # Build offering filters
    offering_filters = Q(assignment__is_active=True)
    
    branch_id = request.GET.get('branch')
    branch_obj = None
    if branch_id:
        try:
            branch_obj = Branch.objects.get(pk=branch_id)
            offering_filters &= Q(branch=branch_obj)
        except Branch.DoesNotExist:
            return Response({'error': 'Branch not found'}, status=404)

    semester_param = request.GET.get('semester')
    year_param = request.GET.get('year')
    
    if semester_param:
        offering_filters &= Q(semester__number=int(semester_param))
    elif year_param:
        year_num = int(year_param)
        sem_a = (year_num * 2) - 1
        sem_b = year_num * 2
        offering_filters &= Q(semester__number__in=[sem_a, sem_b])

    offerings_qs = SubjectOffering.objects.filter(
        offering_filters
    ).select_related(
        'subject', 'branch', 'semester', 'assignment__teacher'
    )

    teachers_data = []
    for offering in offerings_qs:
        try:
            assignment = offering.assignment
            if not assignment or not assignment.is_active:
                continue
            teacher = assignment.teacher
        except Exception:
            continue

        # Filter feedback by session date range
        fb_filter = {'offering': offering}
        if session:
            fb_filter['created_at__gte'] = session.start_date
            fb_filter['created_at__lte'] = session.end_date
        fbs = Feedback.objects.filter(**fb_filter)

        # Skip offerings with no feedback in this session
        if fbs.count() == 0:
            continue

        agg = fbs.aggregate(
            punctuality=Avg('punctuality_rating'),
            domain_knowledge=Avg('teaching_rating'),
            presentation_skills=Avg('clarity_rating'),
            resolve_difficulties=Avg('interaction_rating'),
            teaching_aids=Avg('behavior_rating'),
        )

        p = round(agg['punctuality'] or 0, 4)
        d = round(agg['domain_knowledge'] or 0, 4)
        pr = round(agg['presentation_skills'] or 0, 4)
        r = round(agg['resolve_difficulties'] or 0, 4)
        t = round(agg['teaching_aids'] or 0, 4)
        score = round(p + d + pr + r + t, 4)
        percentage = round((score / 25) * 100, 2) if score > 0 else 0

        # 📈 30% Threshold Logic: Calculate feedback vs enrollment
        total_enrolled = StudentSemester.objects.filter(
            branch=offering.branch,
            semester=offering.semester,
            session=session
        ).count()
        
        feedback_count = fbs.count()
        feedback_percentage = (feedback_count / total_enrolled * 100) if total_enrolled > 0 else 0
        threshold_met = feedback_percentage >= 30

        teachers_data.append({
            "faculty": teacher.get_full_name() or teacher.username,
            "teacher_id": teacher.id,
            "course_name": offering.subject.name,
            "course_code": offering.subject.code,
            "branch_code": offering.branch.code,
            "semester_number": offering.semester.number,
            "feedback_count": feedback_count,
            "total_enrolled": total_enrolled,
            "feedback_percentage": round(feedback_percentage, 2),
            "threshold_met": threshold_met,
            "punctuality": p if threshold_met else None,
            "domain_knowledge": d if threshold_met else None,
            "presentation_skills": pr if threshold_met else None,
            "resolve_difficulties": r if threshold_met else None,
            "teaching_aids": t if threshold_met else None,
            "score": round(score, 4) if threshold_met else 0,
            "percentage": percentage if threshold_met else 0,
        })

    # Sort by percentage descending
    teachers_data.sort(key=lambda x: x['percentage'], reverse=True)

    # Build class label
    class_label = ""
    if branch_obj and year_param:
        year_words = {1: 'First', 2: 'Second', 3: 'Third', 4: 'Fourth'}
        class_label = f"{branch_obj.name} {year_words.get(int(year_param), year_param)} Year"
    elif branch_obj:
        class_label = branch_obj.name
    elif year_param:
        year_words = {1: 'First', 2: 'Second', 3: 'Third', 4: 'Fourth'}
        class_label = f"{year_words.get(int(year_param), year_param)} Year"
    else:
        class_label = "All Classes"

    # Also return available branches and semesters for the filter dropdowns
    available_branches = list(Branch.objects.values('id', 'name', 'code').order_by('name'))
    available_sessions = list(FeedbackSession.objects.values('id', 'name', 'type', 'year').order_by('-year', '-type'))

    data_available = len(teachers_data) > 0
    
    # 🕵️ Aggregated Observations for the entire Department/Class list
    all_class_fbs = Feedback.objects.filter(offering__in=offerings_qs)
    if session:
        all_class_fbs = all_class_fbs.filter(
            created_at__gte=session.start_date,
            created_at__lte=session.end_date
        )
    overall_remarks = "\n".join(generate_key_observations(all_class_fbs)) if data_available else ""

    # 📊 Branch-wise comparison for the current department/session
    branch_performance = all_class_fbs.values(
        'offering__branch__id',
        'offering__branch__name',
        'offering__branch__code'
    ).annotate(
        avg=Avg('overall_rating'),
        count=Count('id')
    ).order_by('-avg')

    branch_comparisons = [
        {
            "branch_name": bp['offering__branch__name'],
            "branch_code": bp['offering__branch__code'],
            "average": round(bp['avg'] or 0, 2),
            "participation": bp['count']
        }
        for bp in branch_performance
    ]

    return Response({
        "institution": "Government Polytechnic Nagpur",
        "department": f"{dept_name} Department",
        "session": session.name if session else "N/A",
        "session_year": f"{session.type} {session.year}-{str(session.year + 1)[2:]}" if session else "",
        "class_label": class_label,
        "data_available": data_available,
        "no_data_message": f"No feedback data available for session {session.name}." if (not data_available and session) else "",
        "teachers": teachers_data,
        "branch_comparisons": branch_comparisons,
        "overall_remarks": overall_remarks,
        "report_date": timezone.now().strftime('%d/%m/%Y'),
        "available_branches": available_branches,
        "available_sessions": available_sessions,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def hod_send_report_emails(request):
    """Send emails to multiple recipients with a report summary or message"""
    if request.user.role != 'hod':
        return Response({'error': 'Only HOD can send emails'}, status=403)

    emails = request.data.get('emails', [])
    subject = request.data.get('subject')
    message = request.data.get('message')
    
    if not emails or not subject or not message:
        return Response({
            'error': 'emails, subject, and message are required'
        }, status=400)

    try:
        # Django send_mail can alternatively be used, but EmailMessage is better for multiple
        email_msg = EmailMessage(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            emails,
        )
        email_msg.content_subtype = "html" # Optional: allows HTML templates
        email_msg.send()
        return Response({
            'message': f'Email sent successfully to {len(emails)} recipients'
        })
    except Exception as e:
        return Response({
            'error': f'Failed to send email: {str(e)}'
        }, status=500)


# ============================================================
# ENROLLMENT VIEWS
# ============================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def enroll_student(request):
    if request.user.role not in ('hod', 'admin'):
        return Response({'error': 'Only HOD/Admin can assign enrollments'}, status=403)

    student_id = request.data.get('student')
    offering_id = request.data.get('subject') or request.data.get('offering')

    if not student_id or not offering_id:
        return Response({'error': 'student and subject (offering ID) are required'}, status=400)

    try:
        student = User.objects.get(pk=student_id, role='student')
        offering = SubjectOffering.objects.select_related('branch', 'semester').get(pk=offering_id)
    except (User.DoesNotExist, SubjectOffering.DoesNotExist):
        return Response({'error': 'Student or Subject offering not found'}, status=404)

    session = FeedbackSession.objects.filter(is_active=True).first()
    if not session:
        return Response({'error': 'No active feedback session found'}, status=400)

    profile = student.student_semesters.filter(session=session).first()
    if profile and profile.branch_id == offering.branch_id and profile.semester_id == offering.semester_id:
        return Response({'error': 'Student is already enrolled in this branch/semester'}, status=400)

    StudentSemester.objects.update_or_create(
        student=student,
        session=session,
        defaults={
            'branch': offering.branch,
            'semester': offering.semester,
            'is_active': True,
        }
    )
    return Response({'message': 'Successfully enrolled'}, status=201)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_enroll(request):
    if request.user.role not in ('hod', 'admin'):
        return Response({'error': 'Only HOD/Admin can assign enrollments'}, status=403)

    student_ids = request.data.get('students', [])
    offering_id = request.data.get('subject') or request.data.get('offering')

    if not student_ids or not offering_id:
        return Response({'error': 'students and subject are required'}, status=400)

    try:
        offering = SubjectOffering.objects.select_related('branch', 'semester').get(pk=offering_id)
    except SubjectOffering.DoesNotExist:
        return Response({'error': 'Subject offering not found'}, status=404)

    session = FeedbackSession.objects.filter(is_active=True).first()
    if not session:
        return Response({'error': 'No active feedback session found'}, status=400)

    created_count = 0
    errors = []

    for sid in student_ids:
        try:
            student = User.objects.get(pk=sid, role='student')
        except User.DoesNotExist:
            errors.append({'student_id': sid, 'error': 'Student not found'})
            continue

        profile = student.student_semesters.filter(session=session).first()
        if profile and profile.branch_id == offering.branch_id and profile.semester_id == offering.semester_id:
            errors.append({'student_id': sid, 'error': 'Already enrolled in this branch/semester'})
            continue

        StudentSemester.objects.update_or_create(
            student=student,
            session=session,
            defaults={
                'branch': offering.branch,
                'semester': offering.semester,
                'is_active': True,
            }
        )
        created_count += 1

    return Response({
        'created_count': created_count,
        'errors': errors,
        'error_count': len(errors),
    }, status=201 if created_count > 0 else 400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_enrollments(request):
    if request.user.role not in ('hod', 'admin'):
        return Response({'error': 'Only HOD/Admin can view enrollments'}, status=403)

    offering_filter = request.GET.get('subject')
    session_filter = request.GET.get('session')

    offerings_qs = SubjectOffering.objects.select_related(
        'subject', 'branch', 'semester'
    ).filter(is_active=True)
    if offering_filter:
        offerings_qs = offerings_qs.filter(id=offering_filter)

    semesters_qs = StudentSemester.objects.filter(is_active=True).select_related('student', 'branch', 'semester', 'session')
    if session_filter:
        semesters_qs = semesters_qs.filter(session_id=session_filter)
    else:
        semesters_qs = semesters_qs.filter(session__is_active=True)

    data = []
    now = timezone.now().isoformat()
    
    # Map sem_key -> list of students, to avoid repeated DB lookups
    # A sem_key is (branch_id, semester_id)
    sem_map = {}
    for ss in semesters_qs:
        key = (ss.branch_id, ss.semester_id)
        if key not in sem_map:
            sem_map[key] = []
        sem_map[key].append(ss.student)

    for offering in offerings_qs:
        key = (offering.branch_id, offering.semester_id)
        matching_students = sem_map.get(key, [])
        for student in matching_students:
            data.append({
                'id': f"{offering.id}-{student.id}",
                'student': student.id,
                'subject': offering.id,
                'student_name': student.get_full_name() or student.username,
                'student_enrollment_no': student.enrollment_no,
                'subject_name': f"{offering.subject.name} ({offering.branch.code} Sem {offering.semester.number})",
                'subject_code': offering.subject.code,
                'created_at': now,
            })

    return Response(data)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_enrollment(request, pk):
    if request.user.role not in ('hod', 'admin'):
        return Response({'error': 'Only HOD/Admin can remove enrollments'}, status=403)

    try:
        pk_str = str(pk)
        if '-' in pk_str:
            offering_id, student_id = pk_str.split('-')
            student = User.objects.get(pk=int(student_id), role='student')
            offering = SubjectOffering.objects.get(pk=int(offering_id))
        else:
            return Response({'error': 'Invalid format. Expected: offeringId-studentId'}, status=400)
    except (ValueError, User.DoesNotExist, SubjectOffering.DoesNotExist):
        return Response({'error': 'Enrollment not found'}, status=404)

    session = FeedbackSession.objects.filter(is_active=True).first()
    deleted, _ = student.student_semesters.filter(
        session=session,
        branch=offering.branch,
        semester=offering.semester
    ).delete()

    if not deleted:
        return Response({'error': 'Student has no active enrollment in this session to remove'}, status=404)

    return Response({'message': 'Enrollment removed successfully'}, status=200)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def enrollment_form_data(request):
    if request.user.role not in ('hod', 'admin'):
        return Response({'error': 'Only HOD/Admin allowed'}, status=403)

    # Determine session
    session_id = request.GET.get('session_id')
    if session_id:
        try:
            session = FeedbackSession.objects.get(pk=session_id)
        except FeedbackSession.DoesNotExist:
            session = FeedbackSession.objects.filter(is_active=True).first()
    else:
        session = FeedbackSession.objects.filter(is_active=True).first()
    
    students_qs = User.objects.filter(role='student').prefetch_related('student_semesters').order_by('username')
    students_data = []
    
    for s in students_qs:
        profile = None
        # get active semester for the session, or the latest
        sp = s.student_semesters.filter(session=session).first() if session else s.student_semesters.first()
        if sp:
            profile = {
                'branch_code': sp.branch.code if sp.branch else None,
                'semester_number': sp.semester.number if sp.semester else None,
            }
        
        full_name = f"{s.first_name} {s.last_name}".strip() if s.first_name else s.username
        students_data.append({
            'id': s.id,
            'username': s.username,
            'first_name': s.first_name,
            'last_name': s.last_name,
            'full_name': full_name,
            'email': s.email,
            'enrollment_no': s.enrollment_no,
            'is_first_login': s.is_first_login,
            'student_profile': profile,
            'branch_code': profile['branch_code'] if profile else None,
            'semester_number': profile['semester_number'] if profile else None,
        })

    offerings = SubjectOffering.objects.select_related('subject', 'branch', 'semester').filter(is_active=True)
    offering_data = []
    for o in offerings:
        teacher_name = "-"
        try:
            if hasattr(o, 'assignment') and o.assignment.is_active and o.assignment.teacher:
                teacher_name = o.assignment.teacher.get_full_name() or o.assignment.teacher.username
        except Exception:
            pass

        offering_data.append({
            'id': o.id,
            'name': f"{o.subject.name} ({o.branch.code} Sem {o.semester.number})",
            'code': o.subject.code,
            'subject_name': o.subject.name,
            'subject_code': o.subject.code,
            'teacher_name': teacher_name,
            'branch_id': o.branch.id,
            'branch_code': o.branch.code,
            'semester_id': o.semester.id,
            'semester_number': o.semester.number,
        })

    return Response({
        'students': students_data,
        'subjects': offering_data,
    })


# ============================================================
# BULK OPERATIONS
# ============================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_upload_students(request):
    """
    HOD/Admin: Upload students via CSV
    CSV Format: full_name, email, enrollment_no, department_name
    """
    if request.user.role not in ['hod', 'admin']:
        return Response({'error': 'Only HOD/Admin can upload students'}, status=403)
    
    file = request.FILES.get('file')
    if not file:
        return Response({'error': 'Please provide a CSV file'}, status=400)
    
    try:
        decoded_file = file.read().decode('utf-8')
        io_string = io.StringIO(decoded_file)
        reader = csv.DictReader(io_string)
        
        created_count = 0
        skipped_count = 0
        errors = []
        
        for row in reader:
            try:
                enrollment_no = row.get('enrollment_no')
                email = row.get('email')
                full_name = row.get('full_name', '')
                dept_name = row.get('department_name')
                
                if not enrollment_no:
                    errors.append({'row': row, 'error': 'Enrollment number is required'})
                    continue
                
                if User.objects.filter(enrollment_no=enrollment_no).exists():
                    skipped_count += 1
                    continue
                
                # Split name
                name_parts = full_name.split(' ', 1)
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ''
                
                # Get department
                dept = None
                if dept_name:
                    dept = Department.objects.filter(name__iexact=dept_name).first()
                
                user = User.objects.create_user(
                    username=enrollment_no,
                    email=email if email else f"{enrollment_no}@student.com",
                    password=enrollment_no, # Default password
                    first_name=first_name,
                    last_name=last_name,
                    role='student',
                    enrollment_no=enrollment_no,
                    department=dept,
                    is_first_login=True
                )
                created_count += 1
            except Exception as e:
                errors.append({'row': row, 'error': str(e)})
        
        return Response({
            'message': f'Successfully processed students',
            'created': created_count,
            'skipped': skipped_count,
            'errors': errors
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({'error': f'Failed to parse CSV: {str(e)}'}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_delete_students(request):
    """
    HOD/Admin: Delete multiple students
    """
    if request.user.role not in ['hod', 'admin']:
        return Response({'error': 'Only HOD/Admin can delete students'}, status=403)
    
    student_ids = request.data.get('student_ids', [])
    if not student_ids:
        return Response({'error': 'Please provide a list of student IDs'}, status=400)
    
    deleted_count, _ = User.objects.filter(id__in=student_ids, role='student').delete()
    return Response({'message': f'Successfully deleted {deleted_count} students'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_enroll_students_semester(request):
    """
    HOD/Admin: Assign multiple students to a branch and semester (StudentSemester)
    """
    if request.user.role not in ['hod', 'admin']:
        return Response({'error': 'Only HOD/Admin can enroll students'}, status=403)
    
    student_ids = request.data.get('student_ids', [])
    branch_id = request.data.get('branch_id')
    semester_id = request.data.get('semester_id')
    session_id = request.data.get('session_id')
    
    if not all([student_ids, branch_id, semester_id]):
        return Response({'error': 'student_ids, branch_id, and semester_id are required'}, status=400)
    
    try:
        branch = Branch.objects.get(pk=branch_id)
        semester = Semester.objects.get(pk=semester_id)
        
        # Determine session
        if session_id:
            try:
                session = FeedbackSession.objects.get(pk=session_id)
            except FeedbackSession.DoesNotExist:
                session = FeedbackSession.objects.filter(is_active=True).first()
        else:
            session = FeedbackSession.objects.filter(is_active=True).first()
        
        if not session:
            return Response({'error': 'No active session found for enrollment'}, status=400)
        
        enrolled_count = 0
        for sid in student_ids:
            try:
                student = User.objects.get(pk=sid, role='student')
                StudentSemester.objects.update_or_create(
                    student=student,
                    session=session,
                    defaults={'branch': branch, 'semester': semester}
                )
                enrolled_count += 1
            except Exception:
                continue
                
        return Response({'message': f'Successfully enrolled {enrolled_count} students in {branch.code} Semester {semester.number}'})
    except (Branch.DoesNotExist, Semester.DoesNotExist):
        return Response({'error': 'Invalid branch or semester'}, status=400)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


# ============================================================
# NEW ACADEMIC MODEL VIEWS
# ============================================================

class BranchViewSet(viewsets.ModelViewSet):
    """CRUD for academic branches"""
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """Only HOD/Admin can modify branches"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            if self.request.user.role not in ['hod', 'admin']:
                raise PermissionDenied("Only HOD/Admin can manage branches")
        return [permission() for permission in self.permission_classes]


class SemesterViewSet(viewsets.ModelViewSet):
    """CRUD for academic semesters"""
    queryset = Semester.objects.all()
    serializer_class = SemesterSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """Only HOD/Admin can modify semesters"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            if self.request.user.role not in ['hod', 'admin']:
                raise PermissionDenied("Only HOD/Admin can manage semesters")
        return [permission() for permission in self.permission_classes]


class SubjectOfferingViewSet(viewsets.ModelViewSet):
    """CRITICAL: Subject + Branch + Semester combinations"""
    queryset = SubjectOffering.objects.select_related(
        'subject', 'branch', 'semester'
    ).prefetch_related('assignment__teacher')
    serializer_class = SubjectOfferingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter based on user role"""
        if getattr(self, 'swagger_fake_view', False):
            return self.queryset.none()
            
        user = self.request.user
        queryset = super().get_queryset()
        
        if user.role == 'student':
            # Students see offerings for their branch + semester
            # Check if student_profile exists
            if hasattr(user, 'student_profile') and user.student_profile:
                return queryset.filter(
                    branch=user.student_profile.branch,
                    semester=user.student_profile.semester,
                    is_active=True
                )
            else:
                # If no student profile, return empty queryset
                return queryset.none()
        elif user.role == 'teacher':
            # Teachers see offerings they're assigned to
            return queryset.filter(
                assignment__teacher=user,
                assignment__is_active=True,
                is_active=True
            ).distinct()
        elif user.role in ['hod', 'admin']:
            # HOD/Admin see all offerings, with optional filtering
            semester_id = self.request.query_params.get('semester')
            branch_id = self.request.query_params.get('branch')
            
            if semester_id:
                queryset = queryset.filter(semester_id=semester_id)
            if branch_id:
                queryset = queryset.filter(branch_id=branch_id)
                
            return queryset
        
        return queryset.none()

    def get_permissions(self):
        """Only HOD/Admin can modify offerings"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            if self.request.user.role not in ['hod', 'admin']:
                raise PermissionDenied("Only HOD/Admin can manage subject offerings")
        return [permission() for permission in self.permission_classes]

    def create(self, request, *args, **kwargs):
        """Use special serializer for creation with validation"""
        if request.user.role not in ['hod', 'admin']:
            raise PermissionDenied("Only HOD/Admin can create subject offerings")
        
        serializer = SubjectOfferingCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SubjectAssignmentViewSet(viewsets.ModelViewSet):
    """Teacher assignments to subject offerings"""
    queryset = SubjectAssignment.objects.select_related(
        'offering__subject', 'offering__branch', 'offering__semester', 'teacher'
    )
    serializer_class = SubjectAssignmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter based on user role"""
        if getattr(self, 'swagger_fake_view', False):
            return self.queryset.none()
            
        user = self.request.user
        queryset = super().get_queryset()
        
        if user.role == 'teacher':
            # Teachers see their own assignments
            return queryset.filter(teacher=user)
        elif user.role == 'student':
            # Students shouldn't see assignments
            return queryset.none()
        elif user.role in ['hod', 'admin']:
            # HOD/Admin see all assignments
            return queryset
        
        return queryset.none()

    def get_permissions(self):
        """Only HOD/Admin can manage assignments"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            if self.request.user.role not in ['hod', 'admin']:
                raise PermissionDenied("Only HOD/Admin can manage teacher assignments")
        return [permission() for permission in self.permission_classes]

    def create(self, request, *args, **kwargs):
        """Use special serializer for assignment with validation"""
        if request.user.role not in ['hod', 'admin']:
            raise PermissionDenied("Only HOD/Admin can assign teachers")
        
        serializer = TeacherAssignmentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_subjects_v2(request):
    """
    CRITICAL: Student sees subjects for THEIR branch + semester ONLY
    Query: SubjectOffering.objects.filter(
        branch=student.student_profile.branch,
        semester=student.student_profile.semester
    )
    """
    if request.user.role != 'student':
        return Response({'error': 'Only students can access their subjects'}, status=403)
    
    try:
        profile = request.user.student_profile
    except StudentSemester.DoesNotExist:
        return Response({'error': 'Student academic profile not found. Please contact HOD.'}, status=400)
    
    if not profile.branch or not profile.semester:
        return Response({'error': 'Student branch or semester not set'}, status=400)
    
    # CORE QUERY: Get offerings for student's branch + semester
    offerings = SubjectOffering.objects.filter(
        branch=profile.branch,
        semester=profile.semester,
        is_active=True
    ).select_related(
        'subject', 'branch', 'semester'
    ).prefetch_related(
        'assignment__teacher'
    )
    
    # Format response with teacher information
    subjects_data = []
    for offering in offerings:
        # Get teacher from assignment
        teacher_name = "Unassigned"
        assignment = offering.assignment if hasattr(offering, 'assignment') and offering.assignment.is_active else None
        if assignment and assignment.teacher:
            teacher_name = assignment.teacher.get_full_name() or assignment.teacher.username
        
        # Check if feedback already submitted
        feedback_submitted = Feedback.objects.filter(
            student=request.user,
            offering=offering
        ).exists()
        
        subjects_data.append({
            'id': offering.id,
            'offering_id': offering.id,
            'subject_id': offering.subject.id,
            'subject_name': offering.subject.name,
            'subject_code': offering.subject.code,
            'subject_credits': offering.subject.credits,
            'branch_name': offering.branch.name,
            'branch_code': offering.branch.code,
            'branch': offering.branch.name,
            'semester_number': offering.semester.number,
            'semester': offering.semester.number,
            'semester_name': offering.semester.name,
            'teacher': teacher_name,
            'max_students': offering.max_students,
            'feedback_submitted': feedback_submitted
        })
    
    # Return FLAT ARRAY - the frontend expects response.data to be an array
    print(f"[student-subjects] Returning {len(subjects_data)} subjects for {request.user.username} ({profile.branch.code} Sem {profile.semester.number})")
    return Response(subjects_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_dashboard(request):
    """
    Student dashboard with subjects and summary information
    """
    if request.user.role != 'student':
        return Response({'error': 'Only students can access dashboard'}, status=403)
    
    try:
        profile = request.user.student_profile
    except StudentSemester.DoesNotExist:
        return Response({'error': 'Student academic profile not found. Please contact HOD.'}, status=400)
    
    if not profile.branch or not profile.semester:
        return Response({'error': 'Student branch or semester not set'}, status=400)
    
    # Get subjects for student
    offerings = SubjectOffering.objects.filter(
        branch=profile.branch,
        semester=profile.semester,
        is_active=True
    ).select_related(
        'subject', 'branch', 'semester'
    ).prefetch_related(
        'assignment__teacher'
    )
    
    # Format response
    subjects_data = []
    total_subjects = 0
    subjects_with_teacher = 0
    
    for offering in offerings:
        total_subjects += 1
        teacher_info = None
        assignment = offering.assignments.filter(is_active=True).first()
        if assignment and assignment.teacher:
            subjects_with_teacher += 1
            teacher_info = {
                'id': assignment.teacher.id,
                'name': assignment.teacher.get_full_name() or assignment.teacher.username,
                'username': assignment.teacher.username
            }
        
        subjects_data.append({
            'id': offering.id,
            'subject_name': offering.subject.name,
            'subject_code': offering.subject.code,
            'teacher': teacher_info,
        })
    
    return Response({
        'subjects': subjects_data,
        'summary': {
            'total_subjects': total_subjects,
            'subjects_with_teacher': subjects_with_teacher,
            'branch': profile.branch.name,
            'semester': profile.semester.number,
            'enrollment_no': request.user.enrollment_no
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_assignments(request):
    """
    Teacher sees subjects they're assigned to teach
    """
    if request.user.role != 'teacher':
        return Response({'error': 'Only teachers can access their assignments'}, status=403)
    
    # Get teacher's active assignments
    assignments = SubjectAssignment.objects.filter(
        teacher=request.user,
        is_active=True
    ).select_related(
        'offering__subject', 'offering__branch', 'offering__semester'
    )
    
    assignments_data = []
    for assignment in assignments:
        offering = assignment.offering
        
        # Get feedback count for this offering
        feedback_count = Feedback.objects.filter(offering=offering).count()
        
        assignments_data.append({
            'id': assignment.id,
            'offering_id': offering.id,
            'subject_name': offering.subject.name,
            'subject_code': offering.subject.code,
            'branch_name': offering.branch.name,
            'semester_number': offering.semester.number,
            'assigned_date': assignment.assigned_date,
            'feedback_count': feedback_count,
            'max_students': offering.max_students
        })
    
    return Response({
        'assignments': assignments_data,
        'teacher_info': {
            'name': request.user.get_full_name() or request.user.username,
            'username': request.user.username
        }
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assign_teacher(request):
    """
    HOD/Admin: Assign teacher to SubjectOffering
    Validation: Prevent duplicate assignments
    """
    if request.user.role not in ['hod', 'admin']:
        return Response({'error': 'Only HOD/Admin can assign teachers'}, status=403)
    
    serializer = TeacherAssignmentSerializer(data=request.data)
    if serializer.is_valid():
        assignment = serializer.save()
        return Response({
            'message': 'Teacher assigned successfully',
            'assignment': TeacherAssignmentSerializer(assignment).data
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_offering_details(request, pk):
    """
    Get detailed information about a subject offering
    """
    try:
        offering = SubjectOffering.objects.get(pk=pk)
    except SubjectOffering.DoesNotExist:
        return Response({'error': 'Subject offering not found'}, status=404)
    
    # Check permissions
    user = request.user
    if user.role == 'student':
        # Students can only see offerings for their branch + semester
        if offering.branch != user.student_profile.branch or offering.semester != user.student_profile.semester:
            return Response({'error': 'Access denied'}, status=403)
    elif user.role == 'teacher':
        # Teachers can only see offerings they're assigned to
        if not (hasattr(offering, 'assignment') and offering.assignment.teacher == user and offering.assignment.is_active):
            return Response({'error': 'Access denied'}, status=403)
    
    # Get detailed information
    serializer = SubjectOfferingSerializer(offering)
    
    # Additional stats
    feedback_count = Feedback.objects.filter(offering=offering).count()
    enrolled_students = User.objects.filter(
        role='student',
        student_profile__branch=offering.branch,
        student_profile__semester=offering.semester
    ).count()
    
    return Response({
        'offering': serializer.data,
        'stats': {
            'feedback_count': feedback_count,
            'enrolled_students': enrolled_students,
            'capacity_percentage': round((enrolled_students / offering.max_students) * 100, 1) if offering.max_students > 0 else 0
        }
    })


# ============================================================
# DEPARTMENT ANALYTICS
# ============================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@swagger_auto_schema(
    operation_description="Compare department-wise feedback performance across semesters",
    manual_parameters=[
        openapi.Parameter(
            'department_id',
            openapi.IN_QUERY,
            description="ID of the department",
            type=openapi.TYPE_INTEGER,
            required=True
        ),
        openapi.Parameter(
            'current_semester',
            openapi.IN_QUERY,
            description="Current semester number",
            type=openapi.TYPE_INTEGER,
            required=True
        ),
        openapi.Parameter(
            'previous_semester',
            openapi.IN_QUERY,
            description="Previous semester number",
            type=openapi.TYPE_INTEGER,
            required=True
        ),
    ],
    responses={
        200: openapi.Response(
            description="Department performance comparison data",
            examples={
                "application/json": {
                    "department": "Information Technology",
                    "department_id": 1,
                    "current_semester": 4,
                    "previous_semester": 3,
                    "current_avg": 4.2,
                    "previous_avg": 3.8,
                    "improvement": 0.4,
                    "total_feedback_current": 120,
                    "total_feedback_previous": 98
                }
            }
        ),
        400: openapi.Response(
            description="Bad request - missing or invalid parameters"
        ),
        403: openapi.Response(
            description="Forbidden - only HOD or Admin allowed"
        ),
        404: openapi.Response(
            description="Department not found"
        )
    }
)
def department_analytics(request):
    """
    Compare department-wise feedback performance across semesters.
    
    Query Params:
    - department_id: ID of the department
    - current_semester: Current semester number
    - previous_semester: Previous semester number
    
    Returns department performance comparison between two semesters.
    """
    # Only HOD or Admin can access
    if request.user.role not in ('hod', 'admin'):
        return Response(
            {'error': 'Only HOD or Admin allowed'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get query parameters
    department_id = request.query_params.get('department_id')
    current_semester = request.query_params.get('current_semester')
    previous_semester = request.query_params.get('previous_semester')
    
    # Validate required parameters
    if not all([department_id, current_semester, previous_semester]):
        return Response(
            {
                'error': 'Missing required parameters',
                'required': ['department_id', 'current_semester', 'previous_semester']
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Convert to integers
        department_id = int(department_id)
        current_semester = int(current_semester)
        previous_semester = int(previous_semester)
    except ValueError:
        return Response(
            {'error': 'All parameters must be integers'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get department name
    try:
        department = Department.objects.get(id=department_id)
        department_name = department.name
    except Department.DoesNotExist:
        return Response(
            {'error': f'Department with id {department_id} not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Filter feedback for the department with optimization
    feedbacks = Feedback.objects.filter(
        offering__branch__department_id=department_id
    ).select_related(
        'offering__branch__department', 
        'offering__semester'
    )
    
    # Separate current and previous semester feedbacks
    current_feedback = feedbacks.filter(offering__semester__number=current_semester)
    previous_feedback = feedbacks.filter(offering__semester__number=previous_semester)
    
    # Aggregate data for current semester
    current_data = current_feedback.aggregate(
        avg_rating=Avg('overall_rating'),
        total_feedback=Count('id')
    )
    
    # Aggregate data for previous semester
    previous_data = previous_feedback.aggregate(
        avg_rating=Avg('overall_rating'),
        total_feedback=Count('id')
    )
    
    # Calculate improvement
    current_avg = current_data['avg_rating'] or 0
    previous_avg = previous_data['avg_rating'] or 0
    improvement = round(current_avg - previous_avg, 2) if current_avg and previous_avg else 0
    
    # Prepare response
    response_data = {
        'department': department_name,
        'department_id': department_id,
        'current_semester': current_semester,
        'previous_semester': previous_semester,
        'current_avg': round(current_avg, 2) if current_avg else 0,
        'previous_avg': round(previous_avg, 2) if previous_avg else 0,
        'improvement': improvement,
        'total_feedback_current': current_data['total_feedback'] or 0,
        'total_feedback_previous': previous_data['total_feedback'] or 0
    }
    
    return Response(response_data)


# ============================================================
# BRANCH COMPARISON ANALYTICS
# ============================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@swagger_auto_schema(
    operation_description="Compare branch-wise feedback performance across semesters within a department",
    manual_parameters=[
        openapi.Parameter(
            'department_id',
            openapi.IN_QUERY,
            description="ID of the department",
            type=openapi.TYPE_INTEGER,
            required=True
        ),
        openapi.Parameter(
            'current_semester',
            openapi.IN_QUERY,
            description="Current semester number",
            type=openapi.TYPE_INTEGER,
            required=True
        ),
        openapi.Parameter(
            'previous_semester',
            openapi.IN_QUERY,
            description="Previous semester number",
            type=openapi.TYPE_INTEGER,
            required=True
        ),
    ],
    responses={
        200: openapi.Response(
            description="Branch-wise performance comparison data",
            examples={
                "application/json": [
                    {
                        "branch": "IT",
                        "current_avg": 4.2,
                        "previous_avg": 3.8,
                        "improvement": 0.4,
                        "current_total": 120,
                        "previous_total": 98
                    },
                    {
                        "branch": "CSE",
                        "current_avg": 3.9,
                        "previous_avg": 4.0,
                        "improvement": -0.1,
                        "current_total": 85,
                        "previous_total": 92
                    }
                ]
            }
        ),
        400: openapi.Response(
            description="Bad request - missing or invalid parameters"
        ),
        403: openapi.Response(
            description="Forbidden - only HOD or Admin allowed"
        ),
        404: openapi.Response(
            description="Department not found"
        )
    }
)
def branch_comparison_analytics(request):
    """
    Compare branch-wise feedback performance across semesters within a department.
    
    Query Params:
    - department_id: ID of the department
    - current_semester: Current semester number
    - previous_semester: Previous semester number
    
    Returns branch-wise performance comparison between two semesters.
    """
    # Only HOD or Admin can access
    if request.user.role not in ('hod', 'admin'):
        return Response(
            {'error': 'Only HOD or Admin allowed'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get query parameters
    department_id = request.query_params.get('department_id')
    current_semester = request.query_params.get('current_semester')
    previous_semester = request.query_params.get('previous_semester')
    
    # Validate required parameters
    if not all([department_id, current_semester, previous_semester]):
        return Response(
            {
                'error': 'Missing required parameters',
                'required': ['department_id', 'current_semester', 'previous_semester']
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Convert to integers
        department_id = int(department_id)
        current_semester = int(current_semester)
        previous_semester = int(previous_semester)
    except ValueError:
        return Response(
            {'error': 'All parameters must be integers'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get department name
    try:
        department = Department.objects.get(id=department_id)
        department_name = department.name
    except Department.DoesNotExist:
        return Response(
            {'error': f'Department with id {department_id} not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Filter all feedback for the department with optimization
    feedbacks = Feedback.objects.filter(
        offering__branch__department_id=department_id
    ).select_related(
        'offering__branch',
        'offering__semester'
    )
    
    # Group by branch
    branches_data = feedbacks.values(
        'offering__branch__id',
        'offering__branch__name'
    ).distinct()
    
    comparison_data = []
    
    for branch_info in branches_data:
        branch_id = branch_info['offering__branch__id']
        branch_name = branch_info['offering__branch__name']
        
        # Filter feedbacks for this branch
        branch_feedbacks = feedbacks.filter(offering__branch__id=branch_id)
        
        # Calculate current semester data
        current_data = branch_feedbacks.filter(
            offering__semester__number=current_semester
        ).aggregate(
            avg=Avg('overall_rating'),
            total=Count('id')
        )
        
        # Calculate previous semester data
        previous_data = branch_feedbacks.filter(
            offering__semester__number=previous_semester
        ).aggregate(
            avg=Avg('overall_rating'),
            total=Count('id')
        )
        
        # Handle null values and round to 2 decimal places
        current_avg = round(current_data['avg'] or 0, 2)
        previous_avg = round(previous_data['avg'] or 0, 2)
        current_total = current_data['total'] or 0
        previous_total = previous_data['total'] or 0
        
        # Calculate improvement
        improvement = round(current_avg - previous_avg, 2) if current_avg and previous_avg else 0
        
        # Prepare branch data
        branch_comparison = {
            "branch": branch_name,
            "branch_id": branch_id,
            "current_avg": current_avg,
            "previous_avg": previous_avg,
            "improvement": improvement,
            "current_total": current_total,
            "previous_total": previous_total
        }
        
        comparison_data.append(branch_comparison)
    
    # Sort by branch name for consistency
    comparison_data.sort(key=lambda x: x['branch'])
    
    # Prepare final response
    response_data = {
        'department': department_name,
        'department_id': department_id,
        'current_semester': current_semester,
        'previous_semester': previous_semester,
        'branches': comparison_data,
        'summary': {
            'total_branches': len(comparison_data),
            'branches_with_improvement': len([b for b in comparison_data if b['improvement'] > 0]),
            'branches_with_decline': len([b for b in comparison_data if b['improvement'] < 0]),
            'branches_no_change': len([b for b in comparison_data if b['improvement'] == 0])
        }
    }
    
    return Response(response_data)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def close_feedback_session(request, pk):
    """
    Mark a feedback session as archived/closed.
    This sets is_active=False and closes all linked feedback windows.
    """
    if request.user.role != 'hod':
        return Response({'error': 'Only HOD allowed'}, status=403)
        
    session = get_object_or_404(FeedbackSession, pk=pk)
    
    # Close the session
    session.is_active = False
    session.save()
    
    # Close all windows associated with this session (if they exist)
    # We close windows that are active and fall within the session's date range
    FeedbackWindow.objects.filter(
        start_date__gte=session.start_date,
        end_date__lte=session.end_date
    ).update(is_active=False)
    
    return Response({
        "message": f"Session '{session.name}' has been successfully closed and archived.",
        "session_id": session.id
    })
