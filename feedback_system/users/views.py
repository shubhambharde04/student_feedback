from rest_framework import viewsets, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.db import connection
from django.db.models import Avg, Count
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.http import HttpResponse
from django.core.mail import EmailMessage
from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from django.db.models import Manager

from .models import User, Subject, Feedback, FeedbackWindow, Enrollment
from .serializers import (
    SubjectSerializer, FeedbackSerializer,
    LoginSerializer, FeedbackWindowSerializer,
    ChangePasswordSerializer, EnrollmentSerializer
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
            return Feedback.objects.filter(subject__teacher=user).order_by('-created_at')
        if user.role == 'student':
            return Feedback.objects.filter(student=user).order_by('-created_at')
        return Feedback.objects.none()

    def create(self, request, *args, **kwargs):
        if request.user.role != 'student':
            return Response(
                {'error': 'Only students can submit feedback'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check feedback window
        window = FeedbackWindow.objects.filter(is_active=True).first()
        now = timezone.now()
        if not window:
            return Response(
                {"error": "No feedback window is currently active"},
                status=400
            )
        if not (window.start_date <= now <= window.end_date):
            return Response(
                {"error": f"Feedback submission is only allowed from "
                          f"{window.start_date.strftime('%Y-%m-%d %H:%M')} to "
                          f"{window.end_date.strftime('%Y-%m-%d %H:%M')}"},
                status=400
            )

        # Check enrollment — student must be enrolled in this subject
        subject_id = request.data.get('subject')
        if not Enrollment.objects.filter(student=request.user, subject_id=subject_id).exists():
            return Response(
                {'error': 'You are not enrolled in this subject'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check duplicate
        if Feedback.objects.filter(student=request.user, subject_id=subject_id).exists():
            return Response(
                {'error': 'You have already submitted feedback for this subject'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        comment = serializer.validated_data.get('comment', '')
        sentiment = analyze_sentiment(comment)
        serializer.save(student=self.request.user, sentiment=sentiment)

    def perform_update(self, serializer):
        raise PermissionDenied("Feedback cannot be edited once submitted")

    def destroy(self, request, *args, **kwargs):
        raise PermissionDenied("Feedback cannot be deleted")


# ============================================================
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
def student_subjects(request):
    """Return ONLY subjects the student is enrolled in."""
    if request.user.role != 'student':
        return Response({'error': 'Only students allowed'}, status=403)

    enrollments = Enrollment.objects.filter(
        student=request.user
    ).select_related('subject__teacher')

    data = []
    for enrollment in enrollments:
        subject = enrollment.subject
        given = Feedback.objects.filter(
            student=request.user, subject=subject
        ).exists()
        data.append({
            "subject_id": subject.id,
            "subject_name": subject.name,
            "subject_code": subject.code,
            "teacher": subject.teacher.get_full_name() or subject.teacher.username,
            "feedback_submitted": given
        })

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
    if request.user.role != 'teacher':
        return Response({'error': 'Only teachers allowed'}, status=403)

    subjects = Subject.objects.filter(teacher=request.user)
    data = []

    for subject in subjects:
        feedbacks = Feedback.objects.filter(subject=subject)
        agg = feedbacks.aggregate(
            avg_punctuality=Avg('punctuality_rating'),
            avg_teaching=Avg('teaching_rating'),
            avg_clarity=Avg('clarity_rating'),
            avg_interaction=Avg('interaction_rating'),
            avg_behavior=Avg('behavior_rating'),
            avg_overall=Avg('overall_rating'),
        )

        data.append({
            "subject_id": subject.id,
            "subject_name": subject.name,
            "subject_code": subject.code,
            "feedback_count": feedbacks.count(),
            "avg_punctuality": round(agg['avg_punctuality'] or 0, 2),
            "avg_teaching": round(agg['avg_teaching'] or 0, 2),
            "avg_clarity": round(agg['avg_clarity'] or 0, 2),
            "avg_interaction": round(agg['avg_interaction'] or 0, 2),
            "avg_behavior": round(agg['avg_behavior'] or 0, 2),
            "avg_overall": round(agg['avg_overall'] or 0, 2),
            "performance": _get_performance_label(agg['avg_overall']),
            "sentiment_summary": _get_sentiment_summary(feedbacks),
        })

    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_performance(request):
    if request.user.role != 'teacher':
        return Response({'error': 'Only teachers allowed'}, status=403)

    subjects = Subject.objects.filter(teacher=request.user)
    subject_performance = []

    all_feedback = Feedback.objects.filter(subject__teacher=request.user)
    overall_agg = all_feedback.aggregate(avg_overall=Avg('overall_rating'))
    overall_avg = round(overall_agg['avg_overall'] or 0, 2)

    for subject in subjects:
        feedbacks = Feedback.objects.filter(subject=subject)
        avg = feedbacks.aggregate(avg_overall=Avg('overall_rating'))['avg_overall']
        subject_performance.append({
            "subject_name": subject.name,
            "subject_code": subject.code,
            "avg_overall": round(avg or 0, 2),
            "feedback_count": feedbacks.count(),
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
    if request.user.role != 'teacher':
        return Response({'error': 'Only teachers allowed'}, status=403)

    subjects = Subject.objects.filter(teacher=request.user)
    data = []

    for subject in subjects:
        feedbacks = Feedback.objects.filter(subject=subject)
        avg = feedbacks.aggregate(Avg('overall_rating'))['overall_rating__avg']
        data.append({
            "subject_name": subject.name,
            "subject_code": subject.code,
            "average_rating": round(avg, 2) if avg else None,
            "feedback_count": feedbacks.count()
        })

    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_performance_charts(request):
    """Return chart-ready data for the teacher performance dashboard."""
    if request.user.role != 'teacher':
        return Response({'error': 'Only teachers allowed'}, status=403)



    subjects = Subject.objects.filter(teacher=request.user)
    all_feedback = Feedback.objects.filter(subject__teacher=request.user)

    # 1. Subject-wise average ratings (bar chart)
    subject_labels = []
    subject_values = []
    for subject in subjects:
        feedbacks = Feedback.objects.filter(subject=subject)
        avg = feedbacks.aggregate(avg=Avg('overall_rating'))['avg']
        subject_labels.append(subject.name)
        subject_values.append(round(avg or 0, 2))

    # 2. Category-wise averages across all subjects (radar/bar)
    cat_agg = all_feedback.aggregate(
        avg_punctuality=Avg('punctuality_rating'),
        avg_teaching=Avg('teaching_rating'),
        avg_clarity=Avg('clarity_rating'),
        avg_interaction=Avg('interaction_rating'),
        avg_behavior=Avg('behavior_rating'),
    )
    category_labels = ['Punctuality', 'Teaching', 'Clarity', 'Interaction', 'Behavior']
    category_values = [
        round(cat_agg['avg_punctuality'] or 0, 2),
        round(cat_agg['avg_teaching'] or 0, 2),
        round(cat_agg['avg_clarity'] or 0, 2),
        round(cat_agg['avg_interaction'] or 0, 2),
        round(cat_agg['avg_behavior'] or 0, 2),
    ]

    # 3. Rating distribution (pie chart: Excellent/Good/Average/Poor)
    total = all_feedback.count()
    excellent = all_feedback.filter(overall_rating__gte=4).count()
    good = all_feedback.filter(overall_rating__gte=3, overall_rating__lt=4).count()
    average = all_feedback.filter(overall_rating__gte=2, overall_rating__lt=3).count()
    poor = all_feedback.filter(overall_rating__lt=2).count()

    # 4. Monthly trend (last 6 months)
    try:
        monthly = (
            all_feedback
            .annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(avg_rating=Avg('overall_rating'), count=Count('id'))
            .order_by('month')
        )
        trend_labels = []
        trend_values = []
        for entry in monthly[-6:]:
            trend_labels.append(entry['month'].strftime('%b %Y'))
            trend_values.append(round(entry['avg_rating'] or 0, 2))
    except Exception:
        # Fallback if there's any issue with the monthly query
        trend_labels = ['No Data']
        trend_values = [0]

    # Handle empty data gracefully
    if not trend_labels:
        trend_labels = ['No Data']
        trend_values = [0]

    return Response({
        'subject_ratings': {
            'labels': subject_labels,
            'values': subject_values,
        },
        'category_averages': {
            'labels': category_labels,
            'values': category_values,
        },
        'rating_distribution': {
            'labels': ['Excellent (4-5)', 'Good (3-4)', 'Average (2-3)', 'Poor (1-2)'],
            'values': [excellent, good, average, poor],
        },
        'monthly_trend': {
            'labels': trend_labels,
            'values': trend_values,
        },
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
            subject__teacher=teacher
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
        subjects = Subject.objects.filter(teacher=teacher)
        feedbacks = Feedback.objects.filter(subject__teacher=teacher)
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

    subjects = Subject.objects.filter(teacher=teacher)
    subject_data = []

    all_feedback = Feedback.objects.filter(subject__teacher=teacher)
    overall_avg = all_feedback.aggregate(avg=Avg('overall_rating'))['avg']

    for subject in subjects:
        feedbacks = Feedback.objects.filter(subject=subject)
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

    subjects = Subject.objects.filter(teacher=teacher)
    all_feedback = Feedback.objects.filter(subject__teacher=teacher)
    overall_avg = all_feedback.aggregate(avg=Avg('overall_rating'))['avg']

    # Build email body
    lines = [
        f"Dear {teacher.get_full_name() or teacher.username},\n",
        "This is your automated performance feedback report.\n",
        "=" * 50,
    ]

    for subject in subjects:
        feedbacks = Feedback.objects.filter(subject=subject)
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
        feedbacks = Feedback.objects.filter(subject__teacher=teacher)
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
    subjects = Subject.objects.all()
    subject_performance = []
    for subject in subjects:
        feedbacks = Feedback.objects.filter(subject=subject)
        avg = feedbacks.aggregate(avg=Avg('overall_rating'))['avg']
        subject_performance.append({
            'subject_name': subject.name,
            'subject_code': subject.code,
            'teacher': subject.teacher.get_full_name() or subject.teacher.username,
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

    subjects = Subject.objects.all()
    stats = []

    for subject in subjects:
        feedbacks = Feedback.objects.filter(subject=subject)
        agg = feedbacks.aggregate(
            avg_overall=Avg('overall_rating'),
            avg_punctuality=Avg('punctuality_rating'),
            avg_teaching=Avg('teaching_rating'),
            avg_clarity=Avg('clarity_rating'),
            avg_interaction=Avg('interaction_rating'),
            avg_behavior=Avg('behavior_rating'),
        )

        stats.append({
            "subject": subject.name,
            "subject_code": subject.code,
            "teacher": subject.teacher.get_full_name() or subject.teacher.username,
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

    subjects = Subject.objects.select_related('teacher').all()
    report = []

    for subject in subjects:
        feedbacks = Feedback.objects.filter(subject=subject)
        avg = feedbacks.aggregate(avg=Avg('overall_rating'))['avg']

        report.append({
            "subject": subject.name,
            "subject_code": subject.code,
            "teacher": subject.teacher.get_full_name() or subject.teacher.username,
            "teacher_email": subject.teacher.email,
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

    subjects = Subject.objects.all()
    analysis = []

    for subject in subjects:
        feedbacks = Feedback.objects.filter(subject=subject)
        avg = feedbacks.aggregate(Avg('overall_rating'))['overall_rating__avg']
        total = feedbacks.count()

        analysis.append({
            "subject": subject.name,
            "subject_code": subject.code,
            "teacher": subject.teacher.get_full_name() or subject.teacher.username,
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

    subjects = Subject.objects.select_related('teacher').all()

    for subject in subjects:
        feedbacks = Feedback.objects.filter(subject=subject)
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
        p.drawString(60, y, f"Subject: {subject.name} ({subject.code})")
        y -= 18

        p.setFont("Helvetica", 10)
        p.drawString(80, y, f"Teacher: {subject.teacher.get_full_name() or subject.teacher.username}")
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

    subjects = Subject.objects.filter(teacher=teacher)
    all_feedback = Feedback.objects.filter(subject__teacher=teacher)
    
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
        fbs = Feedback.objects.filter(subject__teacher=teacher)
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
    
    # Subject-wise
    subjects = Subject.objects.all()
    subject_perf = []
    for subject in subjects:
        fbs = Feedback.objects.filter(subject=subject)
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
    if subject.branch and student.branch and student.branch != subject.branch:
        return Response(
            {'error': f'Branch mismatch: student is in {student.branch.name} but subject belongs to {subject.branch.name}'},
            status=400
        )
    if subject.semester and student.semester and student.semester != subject.semester:
        return Response(
            {'error': f'Semester mismatch: student is in semester {student.semester.number} but subject belongs to semester {subject.semester.number}'},
            status=400
        )

    # Duplicate check
    if Enrollment.objects.filter(student=student, subject=subject).exists():
        return Response({'error': 'Student is already enrolled in this subject'}, status=400)

    enrollment = Enrollment.objects.create(
        student=student,
        subject=subject,
        assigned_by=request.user,
    )
    serializer = EnrollmentSerializer(enrollment)
    return Response(serializer.data, status=201)


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

    created = []
    errors = []

    for sid in student_ids:
        try:
            student = User.objects.get(pk=sid, role='student')
        except User.DoesNotExist:
            errors.append({'student_id': sid, 'error': 'Student not found'})
            continue

        # Branch validation
        if subject.branch and student.branch and student.branch != subject.branch:
            errors.append({
                'student_id': sid,
                'error': f'Branch mismatch ({student.branch.name} vs {subject.branch.name})'
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
        if Enrollment.objects.filter(student=student, subject=subject).exists():
            errors.append({'student_id': sid, 'error': 'Already enrolled'})
            continue

        enrollment = Enrollment.objects.create(
            student=student,
            subject=subject,
            assigned_by=request.user,
        )
        created.append(EnrollmentSerializer(enrollment).data)

    return Response({
        'created': created,
        'errors': errors,
        'created_count': len(created),
        'error_count': len(errors),
    }, status=201 if created else 400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_enrollments(request):
    """List all enrollments (HOD/Admin only)."""
    if request.user.role not in ('hod', 'admin'):
        return Response({'error': 'Only HOD/Admin can view enrollments'}, status=403)

    subject_id = request.GET.get('subject')
    queryset = Enrollment.objects.select_related(
        'student', 'subject', 'assigned_by'
    ).all()

    if subject_id:
        queryset = queryset.filter(subject_id=subject_id)

    serializer = EnrollmentSerializer(queryset, many=True)
    return Response(serializer.data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_enrollment(request, pk):
    """Remove an enrollment (HOD/Admin only)."""
    if request.user.role not in ('hod', 'admin'):
        return Response({'error': 'Only HOD/Admin can remove enrollments'}, status=403)

    try:
        enrollment = Enrollment.objects.get(pk=pk)
    except Enrollment.DoesNotExist:
        return Response({'error': 'Enrollment not found'}, status=404)

    enrollment.delete()
    return Response({'message': 'Enrollment removed successfully'}, status=200)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def enrollment_form_data(request):
    """Return students and subjects for the enrollment form (HOD/Admin only)."""
    if request.user.role not in ('hod', 'admin'):
        return Response({'error': 'Only HOD/Admin allowed'}, status=403)

    students = User.objects.filter(role='student').values(
        'id', 'username', 'first_name', 'last_name',
        'enrollment_no', 'branch_id', 'semester_id'
    )
    subjects = Subject.objects.select_related('teacher', 'branch', 'semester').all()
    subject_data = []
    for s in subjects:
        subject_data.append({
            'id': s.id,
            'name': s.name,
            'code': s.code,
            'teacher_name': s.teacher.get_full_name() or s.teacher.username,
            'branch_id': s.branch_id,
            'branch_name': s.branch.name if s.branch else None,
            'semester_id': s.semester_id,
            'semester_number': s.semester.number if s.semester else None,
        })

    return Response({
        'students': list(students),
        'subjects': subject_data,
    })
