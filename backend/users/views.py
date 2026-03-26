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
from django.conf import settings
import csv
import io
from drf_yasg.utils import swagger_auto_schema
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from django.db.models import Manager

from .models import (
    User, Subject, SubjectOffering, SubjectAssignment, 
    Feedback, FeedbackWindow, Branch, Semester,
    Department, StudentSemester
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

    serializer = FeedbackSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        comment = serializer.validated_data.get('comment', '')
        sentiment = analyze_sentiment(comment)
        
        # Save feedback (Logic for student assignment is in serializer.validate)
        feedback = serializer.save(sentiment=sentiment)
        
        return Response({
            "message": "Feedback submitted successfully",
            "data": {
                "subject": feedback.offering.subject.name,
                "teacher": serializer.get_teacher_name(feedback),
                "overall_rating": feedback.overall_rating
            }
        }, status=status.HTTP_201_CREATED)
        
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
# AUTH VIEWS
# ============================================================

@swagger_auto_schema(method='post', request_body=LoginSerializer)
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response(
            {'error': 'Please provide username and password'},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = authenticate(request, username=username, password=password)

    if user:
        refresh = RefreshToken.for_user(user)
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

    return Response(
        {'error': 'Invalid credentials'},
        status=status.HTTP_401_UNAUTHORIZED
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    try:
        # Get refresh token from request data or Authorization header
        refresh_token = request.data.get('refresh')
        
        # If no refresh token in body, try to get it from cookies
        if not refresh_token and hasattr(request, 'COOKIES'):
            refresh_token = request.COOKIES.get('refresh_token')
        
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'message': 'Successfully logged out'})
        else:
            # If no refresh token provided, just clear session
            return Response({'message': 'Successfully logged out (session cleared)'})
            
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

    if not old_password or not new_password:
        return Response(
            {'error': 'Please provide both old and new passwords'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not user.check_password(old_password):
        return Response(
            {'error': 'Incorrect old password'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if len(new_password) < 6:
        return Response(
            {'error': 'Password must be at least 6 characters long.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    user.set_password(new_password)
    user.is_first_login = False
    user.save()

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
        profile = request.user.student_profile
    except StudentSemester.DoesNotExist:
        return Response([], status=200)  # Return empty array, not error
    
    if not profile.branch or not profile.semester:
        return Response([], status=200)

    offerings = SubjectOffering.objects.filter(
        branch=profile.branch,
        semester=profile.semester,
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
    offerings = SubjectOffering.objects.filter(assignment__teacher=request.user, assignment__is_active=True)
    view_mode = request.query_params.get('view', 'combined')
    data = []

    if view_mode == 'combined':
        subjects = Subject.objects.filter(offerings__in=offerings).distinct()
        for subject in subjects:
            feedbacks = Feedback.objects.filter(offering__in=offerings, offering__subject=subject)
            agg = feedbacks.aggregate(
                avg_punctuality=Avg('punctuality_rating'), avg_teaching=Avg('teaching_rating'),
                avg_clarity=Avg('clarity_rating'), avg_interaction=Avg('interaction_rating'),
                avg_behavior=Avg('behavior_rating'), avg_overall=Avg('overall_rating')
            )
            data.append({
                "subject_id": subject.id,
                "subject_name": subject.name, "subject_code": subject.code,
                "feedback_count": feedbacks.count(), "performance": _get_performance_label(agg['avg_overall']),
                "sentiment_summary": _get_sentiment_summary(feedbacks),
                **{k: round(v or 0, 2) for k, v in agg.items()}
            })
    else:
        for offering in offerings:
            feedbacks = Feedback.objects.filter(offering=offering)
            agg = feedbacks.aggregate(
                avg_punctuality=Avg('punctuality_rating'), avg_teaching=Avg('teaching_rating'),
                avg_clarity=Avg('clarity_rating'), avg_interaction=Avg('interaction_rating'),
                avg_behavior=Avg('behavior_rating'), avg_overall=Avg('overall_rating')
            )
            name_suffix = f" ({offering.branch.code} Sem {offering.semester.number})"
            data.append({
                "subject_id": offering.id,
                "subject_name": offering.subject.name + name_suffix, "subject_code": offering.subject.code,
                "feedback_count": feedbacks.count(), "performance": _get_performance_label(agg['avg_overall']),
                "sentiment_summary": _get_sentiment_summary(feedbacks),
                **{k: round(v or 0, 2) for k, v in agg.items()}
            })

    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_performance(request):
    if request.user.role != 'teacher': return Response({'error': 'Only teachers allowed'}, status=403)
    offerings = SubjectOffering.objects.filter(assignment__teacher=request.user, assignment__is_active=True)
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
    offerings = SubjectOffering.objects.filter(assignment__teacher=request.user, assignment__is_active=True)
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
            return Response(
                {'message': 'No active feedback window'},
                status=status.HTTP_404_NOT_FOUND
            )
        now = timezone.now()
        if not (window.start_date <= now <= window.end_date):
            return Response(
                {'message': 'Feedback window is closed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = FeedbackWindowSerializer(window)
        return Response(serializer.data)
    except Exception as e:
        return Response(
            {'message': 'Server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


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

    offerings = SubjectOffering.objects.prefetch_related('assignment__teacher').all()

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
        suggestion = get_improvement(agg['avg_overall'])

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
    if request.user.role != 'hod':
        return Response({'error': 'Only HOD allowed'}, status=403)
    
    try:
        teacher = User.objects.get(pk=pk, role='teacher')
    except User.DoesNotExist:
        return Response({'error': 'Teacher not found'}, status=404)

    subjects = Subject.objects.filter(offerings__assignment__teacher=teacher, offerings__assignment__is_active=True).distinct()
    all_feedback = Feedback.objects.filter(offering__assignment__teacher=teacher, offering__assignment__is_active=True)
    
    overall_avg = all_feedback.aggregate(avg=Avg('overall_rating'))['avg']
    total_feedback = all_feedback.count()
    
    # Rating distribution
    rating_dist = {}
    for i in range(1, 6):
        rating_dist[str(i)] = all_feedback.filter(
            overall_rating__gte=i - 0.5, overall_rating__lt=i + 0.5
        ).count()
        
    # Performance trend (monthly)
    try:
        monthly = (
            all_feedback
            .annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(avg_rating=Avg('overall_rating'))
            .order_by('month')
        )
        trend_labels = []
        trend_values = []
        for entry in monthly[-6:]:
            if entry['month']:
                trend_labels.append(entry['month'].strftime('%b %Y'))
                trend_values.append(round(entry['avg_rating'] or 0, 2))
    except Exception:
        trend_labels = []
        trend_values = []

    # Strengths & Weaknesses based on category averages
    cat_agg = all_feedback.aggregate(
        punctuality=Avg('punctuality_rating'),
        teaching=Avg('teaching_rating'),
        clarity=Avg('clarity_rating'),
        interaction=Avg('interaction_rating'),
        behavior=Avg('behavior_rating'),
    )
    
    categories = []
    for k, v in cat_agg.items():
        if v is not None:
            categories.append({"name": k.replace('_rating', '').capitalize(), "score": v})
            
    categories.sort(key=lambda x: x['score'], reverse=True)
    strengths = [c['name'] for c in categories[:2]] if categories else []
    weaknesses = [c['name'] for c in categories[-2:]] if len(categories) >= 3 else []
    
    return Response({
        "teacher": {
            "name": teacher.get_full_name() or teacher.username,
            "email": teacher.email,
        },
        "subjects": [{"name": s.name, "code": s.code} for s in subjects],
        "total_feedback_count": total_feedback,
        "average_rating": round(overall_avg, 2) if overall_avg else 0,
        "performance_label": _get_performance_label(overall_avg),
        "rating_distribution": rating_dist,
        "performance_trend": {
            "labels": trend_labels,
            "values": trend_values,
        },
        "strengths": strengths,
        "weaknesses": weaknesses,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hod_department_report(request):
    if request.user.role != 'hod':
        return Response({'error': 'Only HOD allowed'}, status=403)
        
    all_feedback = Feedback.objects.all()
    teachers = User.objects.filter(role='teacher')
    
    # Teachers list with avg rating
    teachers_list = []
    for teacher in teachers:
        fbs = Feedback.objects.filter(offering__assignment__teacher=teacher, offering__assignment__is_active=True)
        avg = fbs.aggregate(avg=Avg('overall_rating'))['avg']
        teachers_list.append({
            "name": teacher.get_full_name() or teacher.username,
            "email": teacher.email,
            "avg_rating": round(avg, 2) if avg else 0,
            "feedback_count": fbs.count(),
        })
        
    teachers_list.sort(key=lambda x: x['avg_rating'], reverse=True)
    
    dept_avg = all_feedback.aggregate(avg=Avg('overall_rating'))['avg']
    total_feedback = all_feedback.count()
    
    # Year Performance
    year_perf = {}
    for sem in Semester.objects.all():
        year_num = (sem.number + 1) // 2
        fbs = all_feedback.filter(offering__semester=sem)
        avg = fbs.aggregate(avg=Avg('overall_rating'))['avg']
        count = fbs.count()
        if count > 0:
            key = str(year_num)
            if key not in year_perf:
                year_perf[key] = {"total_rating": 0, "count": 0}
            year_perf[key]["total_rating"] += (avg or 0) * count
            year_perf[key]["count"] += count
            
    year_performance = []
    for y, data in year_perf.items():
        year_performance.append({
            "year": f"Year {y}",
            "avg_rating": round(data["total_rating"] / data["count"], 2),
            "feedback_count": data["count"]
        })
    year_performance.sort(key=lambda x: x["year"])

    # Branch Performance
    branches = Branch.objects.all()
    branch_performance = []
    for branch in branches:
        fbs = all_feedback.filter(offering__branch=branch)
        avg = fbs.aggregate(avg=Avg('overall_rating'))['avg']
        if fbs.exists():
            branch_performance.append({
                "name": branch.code,
                "avg_rating": round(avg or 0, 2),
                "feedback_count": fbs.count()
            })

    # Subject-wise
    subjects = Subject.objects.all()
    subject_perf = []
    for subject in subjects:
        fbs = Feedback.objects.filter(offering__subject=subject)
        avg = fbs.aggregate(avg=Avg('overall_rating'))['avg']
        subject_perf.append({
            "name": subject.name,
            "code": subject.code,
            "avg_rating": round(avg, 2) if avg else 0,
            "feedback_count": fbs.count(),
        })
        
    # Sentiment
    sentiment = _get_sentiment_summary(all_feedback)
    
    # Growth Indicator
    now = timezone.now()
    last_month = now - timezone.timedelta(days=30)
    
    recent_feedbacks = all_feedback.filter(created_at__gte=last_month)
    older_feedbacks = all_feedback.filter(created_at__lt=last_month)
    
    recent_avg = recent_feedbacks.aggregate(avg=Avg('overall_rating'))['avg'] or 0
    older_avg = older_feedbacks.aggregate(avg=Avg('overall_rating'))['avg'] or 0
    
    if older_avg > 0:
        if recent_avg > older_avg + 0.1:
            growth = "Improving"
        elif recent_avg < older_avg - 0.1:
            growth = "Declining"
        else:
            growth = "Stable"
    else:
        growth = "Stable"
        
    return Response({
        "teachers": teachers_list,
        "department_average": round(dept_avg, 2) if dept_avg else 0,
        "total_feedback": total_feedback,
        "subject_performance": subject_perf,
        "sentiment_analysis": sentiment,
        "growth_indicator": growth,
        "recent_avg": round(recent_avg, 2),
        "older_avg": round(older_avg, 2),
        "year_performance": year_performance,
        "branch_performance": branch_performance,
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
    """Enroll a single student in a subject (HOD/Admin only)."""
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
    if student.student_profile.branch and subject.branches.exists() and not subject.branches.filter(id=student.student_profile.branch.id).exists():
        return Response(
            {'error': f'Branch mismatch: student is in {student.student_profile.branch.name} but subject is not offered to this branch'},
            status=400
        )
    if subject.semester and student.student_profile.semester and student.student_profile.semester != subject.semester:
        return Response(
            {'error': f'Semester mismatch: student is in semester {student.student_profile.semester.number} but subject belongs to semester {subject.semester.number}'},
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
    """Enroll multiple students in one subject (HOD/Admin only)."""
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
        if student.student_profile.branch and subject.branches.exists() and not subject.branches.filter(id=student.student_profile.branch.id).exists():
            errors.append({
                'student_id': sid,
                'error': f'Branch mismatch ({student.student_profile.branch.name} vs subject branches)'
            })
            continue

        # Semester validation
        if subject.semester and student.student_profile.semester and student.student_profile.semester != subject.semester:
            errors.append({
                'student_id': sid,
                'error': f'Semester mismatch (sem {student.student_profile.semester.number} vs sem {subject.semester.number})'
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
    """List all enrollments (HOD/Admin only)."""
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
    """Remove an enrollment (HOD/Admin only). pk is format: subject_id-student_id"""
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
    """Return students and subjects for the enrollment form (HOD/Admin only)."""
    if request.user.role not in ('hod', 'admin'):
        return Response({'error': 'Only HOD/Admin allowed'}, status=403)

    # Build student list with nested student_profile
    students_qs = User.objects.filter(role='student').select_related(
        'student_profile__branch', 'student_profile__semester'
    ).order_by('username')
    
    students_data = []
    for s in students_qs:
        profile = None
        if hasattr(s, 'student_profile'):
            try:
                sp = s.student_profile
                profile = {
                    'branch_code': sp.branch.code if sp.branch else None,
                    'semester_number': sp.semester.number if sp.semester else None,
                }
            except Exception:
                profile = None
        
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
            # Also keep flat keys for backward compat
            'branch_code': profile['branch_code'] if profile else None,
            'semester_number': profile['semester_number'] if profile else None,
        })

    offerings = SubjectOffering.objects.select_related('subject', 'branch', 'semester').all()
    offering_data = []
    for o in offerings:
        teacher_name = "-"
        try:
            if hasattr(o, 'assignment') and o.assignment.is_active and o.assignment.teacher:
                teacher_name = o.assignment.teacher.get_full_name() or o.assignment.teacher.username
        except Exception:
            teacher_name = "-"

        offering_data.append({
            'id': o.id,
            'subject_name': o.subject.name,
            'subject_code': o.subject.code,
            'teacher_name': teacher_name,
            'branch_id': o.branch.id,
            'branch_code': o.branch.code,
            'semester_id': o.semester.id,
            'semester_number': o.semester.number,
        })

    print(f"[enrollment_form_data] Returning {len(students_data)} students, {len(offering_data)} offerings")
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
    
    if not all([student_ids, branch_id, semester_id]):
        return Response({'error': 'student_ids, branch_id, and semester_id are required'}, status=400)
    
    try:
        branch = Branch.objects.get(pk=branch_id)
        semester = Semester.objects.get(pk=semester_id)
        
        enrolled_count = 0
        for sid in student_ids:
            try:
                student = User.objects.get(pk=sid, role='student')
                StudentSemester.objects.update_or_create(
                    student=student,
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
        user = self.request.user
        queryset = super().get_queryset()
        
        if user.role == 'student':
            # Students see offerings for their branch + semester
            return queryset.filter(
                branch=user.student_profile.branch,
                semester=user.student_profile.semester,
                is_active=True
            )
        elif user.role == 'teacher':
            # Teachers see offerings they're assigned to
            return queryset.filter(
                assignment__teacher=user,
                assignment__is_active=True,
                is_active=True
            ).distinct()
        elif user.role in ['hod', 'admin']:
            # HOD/Admin see all offerings
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
