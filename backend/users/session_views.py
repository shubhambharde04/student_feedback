from rest_framework import viewsets, status, permissions
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, NotFound
from django.db.models import Avg, Count, Q, F
from django.utils import timezone
from django.shortcuts import get_object_or_404

from .models import (
    FeedbackSession, Question, FeedbackForm, FormQuestionMapping,
    SessionOffering, FeedbackResponse, FeedbackSubmission,
    User, SubjectOffering
)
from .serializers import (
    FeedbackSessionSerializer, QuestionSerializer, FeedbackFormSerializer,
    FormQuestionMappingSerializer, SessionOfferingSerializer,
    FeedbackResponseSerializer, FeedbackSubmissionSerializer,
    FeedbackSubmissionCreateSerializer, AnalyticsSerializer,
    SessionComparisonSerializer
)


# ============================================================
# SESSION MANAGEMENT VIEWS
# ============================================================

class FeedbackSessionViewSet(viewsets.ModelViewSet):
    """CRUD operations for feedback sessions"""
    queryset = FeedbackSession.objects.all()
    serializer_class = FeedbackSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_permissions(self):
        """Only HOD and Admin can manage sessions"""
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'start_session', 'end_feedback']:
            self.permission_classes = [permissions.IsAuthenticated]
            # Check if user is HOD or Admin
            if self.request.user.role not in ['hod', 'admin']:
                raise PermissionDenied("Only HOD or Admin can manage sessions")
        return super().get_permissions()
    
    def get_queryset(self):
        """Filter sessions based on user role"""
        user = self.request.user
        if user.role in ['hod', 'admin']:
            return FeedbackSession.objects.all()
        else:
            # Teachers and students see only active sessions
            return FeedbackSession.objects.filter(is_active=True)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def lock_session(self, request, pk=None):
        """Lock a session to prevent further modifications"""
        if request.user.role not in ['hod', 'admin']:
            raise PermissionDenied("Only HOD or Admin can lock sessions")
        
        session = get_object_or_404(FeedbackSession, pk=pk)
        session.is_locked = True
        session.save()
        
        return Response({
            'message': f'Session {session.name} has been locked',
            'session': FeedbackSessionSerializer(session).data
        })
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def start_session(self, request, pk=None):
        """Start a feedback session"""
        if request.user.role not in ['hod', 'admin']:
            raise PermissionDenied("Only HOD or Admin can start sessions")
        
        session = get_object_or_404(FeedbackSession, pk=pk)
        
        if session.is_closed:
            return Response({
                'error': 'Cannot start a closed session',
                'session': FeedbackSessionSerializer(session).data
            }, status=400)
        
        session.start_session()
        
        return Response({
            'message': f'Session {session.name} has been started',
            'session': FeedbackSessionSerializer(session).data
        })
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def end_feedback(self, request, pk=None):
        """End feedback for a session - CRITICAL BUTTON"""
        if request.user.role not in ['hod', 'admin']:
            raise PermissionDenied("Only HOD or Admin can end feedback")
        
        session = get_object_or_404(FeedbackSession, pk=pk)
        
        if session.is_closed:
            return Response({
                'error': 'Session is already closed',
                'session': FeedbackSessionSerializer(session).data
            }, status=400)
        
        # Close the session - this locks all feedback submissions
        session.close_session()
        
        return Response({
            'message': f'Feedback for session {session.name} has been ended. No further submissions allowed.',
            'session': FeedbackSessionSerializer(session).data
        })
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def get_current_session(self, request):
        """Get the current active session for feedback"""
        current_session = FeedbackSession.objects.filter(
            is_active=True,
            is_closed=False
        ).order_by('-created_at').first()
        
        if not current_session:
            return Response({
                'error': 'No active feedback session found',
                'sessions': FeedbackSessionSerializer(
                    FeedbackSession.objects.all().order_by('-year'), many=True
                ).data
            }, status=404)
        
        return Response({
            'current_session': FeedbackSessionSerializer(current_session).data,
            'can_submit_feedback': current_session.can_submit_feedback
        })
    
    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def get_previous_session(self, request, pk=None):
        """Get the previous session for comparison"""
        current_session = get_object_or_404(FeedbackSession, pk=pk)
        
        # Find previous session of same type
        previous_session = FeedbackSession.objects.filter(
            type=current_session.type,
            year__lt=current_session.year
        ).order_by('-year').first()
        
        if not previous_session:
            return Response({
                'error': 'No previous session found for comparison',
                'current_session': FeedbackSessionSerializer(current_session).data
            }, status=404)
        
        return Response({
            'current_session': FeedbackSessionSerializer(current_session).data,
            'previous_session': FeedbackSessionSerializer(previous_session).data
        })


# ============================================================
# QUESTION MANAGEMENT VIEWS
# ============================================================

class QuestionViewSet(viewsets.ModelViewSet):
    """CRUD operations for dynamic questions"""
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_permissions(self):
        """Only HOD can manage questions"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            if self.request.user.role != 'hod':
                raise PermissionDenied("Only HOD can manage questions")
        return super().get_permissions()
    
    def get_queryset(self):
        """Filter questions based on active status"""
        is_active = self.request.query_params.get('is_active')
        queryset = Question.objects.all()
        
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset.order_by('order', 'category')


# ============================================================
# FORM MANAGEMENT VIEWS
# ============================================================

class FeedbackFormViewSet(viewsets.ModelViewSet):
    """CRUD operations for feedback forms"""
    queryset = FeedbackForm.objects.all()
    serializer_class = FeedbackFormSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_permissions(self):
        """Only HOD can manage forms"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            if self.request.user.role != 'hod':
                raise PermissionDenied("Only HOD can manage forms")
        return super().get_permissions()
    
    def get_queryset(self):
        """Filter forms based on session"""
        session_id = self.request.query_params.get('session')
        queryset = FeedbackForm.objects.all()
        
        if session_id:
            queryset = queryset.filter(session_id=session_id)
        
        return queryset.select_related('session').order_by('-session__year', 'name')
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def assign_questions(self, request, pk=None):
        """Assign questions to a form"""
        if request.user.role != 'hod':
            raise PermissionDenied("Only HOD can assign questions")
        
        form = get_object_or_404(FeedbackForm, pk=pk)
        question_ids = request.data.get('question_ids', [])
        
        # Clear existing mappings
        FormQuestionMapping.objects.filter(form=form).delete()
        
        # Create new mappings
        for order, question_id in enumerate(question_ids):
            question = get_object_or_404(Question, pk=question_id)
            FormQuestionMapping.objects.create(
                form=form,
                question=question,
                order=order
            )
        
        return Response({
            'message': f'Assigned {len(question_ids)} questions to form {form.name}',
            'form': FeedbackFormSerializer(form).data
        })


# ============================================================
# SESSION OFFERING VIEWS
# ============================================================

class SessionOfferingViewSet(viewsets.ModelViewSet):
    """CRUD operations for session-specific offerings"""
    queryset = SessionOffering.objects.all()
    serializer_class = SessionOfferingSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter offerings based on user role and session"""
        user = self.request.user
        session_id = self.request.query_params.get('session')
        queryset = SessionOffering.objects.select_related(
            'session', 'base_offering', 'teacher',
            'base_offering__subject', 'base_offering__branch', 'base_offering__semester'
        )
        
        if session_id:
            queryset = queryset.filter(session_id=session_id)
            
        branch_id = self.request.query_params.get('branch')
        semester_id = self.request.query_params.get('semester')
        
        if branch_id:
            queryset = queryset.filter(base_offering__branch_id=branch_id)
        if semester_id:
            queryset = queryset.filter(base_offering__semester_id=semester_id)
        
        if user.role == 'student':
            # Students see offerings for their branch and semester
            if hasattr(user, 'student_profile') and user.student_profile:
                queryset = queryset.filter(
                    base_offering__branch=user.student_profile.branch,
                    base_offering__semester=user.student_profile.semester,
                    is_active=True
                )
            else:
                queryset = queryset.none()
        elif user.role == 'teacher':
            # Teachers see their assigned offerings
            queryset = queryset.filter(teacher=user, is_active=True)
        
        return queryset.order_by('-session__year', 'base_offering__branch__name', 'base_offering__semester__number')


# ============================================================
# FEEDBACK SUBMISSION VIEWS
# ============================================================

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_active_feedback_form(request):
    """Get the active feedback form for the current session"""
    user = request.user
    
    if user.role != 'student':
        return Response({'error': 'Only students can access feedback forms'}, status=403)
    
    # Get current active session that allows feedback
    current_session = FeedbackSession.objects.filter(
        is_active=True,
        is_closed=False
    ).order_by('-created_at').first()
    
    if not current_session:
        return Response({
            'error': 'No active feedback session available',
            'message': 'Feedback collection is currently closed'
        }, status=404)
    
    # Check if session allows feedback submission
    if not current_session.can_submit_feedback:
        return Response({
            'error': 'Feedback submission is not allowed at this time',
            'message': 'The feedback period has ended or not yet started',
            'session': FeedbackSessionSerializer(current_session).data
        }, status=403)
    
    # Get active form for the session
    active_form = FeedbackForm.objects.filter(
        session=current_session,
        is_active=True
    ).first()
    
    if not active_form:
        return Response({
            'error': 'No active feedback form available for this session',
            'session': FeedbackSessionSerializer(current_session).data
        }, status=404)
    
    # Get student's offerings for this session
    if not hasattr(user, 'student_profile') or not user.student_profile:
        return Response({'error': 'Student profile not found'}, status=404)
    
    student_offerings = SessionOffering.objects.filter(
        session=current_session,
        base_offering__branch=user.student_profile.branch,
        base_offering__semester=user.student_profile.semester,
        is_active=True
    )
    
    # Check which offerings the student has already submitted feedback for
    submitted_offerings = FeedbackSubmission.objects.filter(
        student=user,
        session=current_session,
        is_completed=True
    ).values_list('offering_id', flat=True)
    
    available_offerings = student_offerings.exclude(id__in=submitted_offerings)
    
    return Response({
        'session': FeedbackSessionSerializer(current_session).data,
        'form': FeedbackFormSerializer(active_form).data,
        'available_offerings': SessionOfferingSerializer(available_offerings, many=True).data,
        'submitted_count': len(submitted_offerings),
        'total_offerings': student_offerings.count(),
        'can_submit_feedback': current_session.can_submit_feedback
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def submit_feedback(request):
    """Submit feedback for a specific offering"""
    user = request.user
    
    if user.role != 'student':
        return Response({'error': 'Only students can submit feedback'}, status=403)
    
    offering_id = request.data.get('offering_id')
    responses = request.data.get('responses', [])
    
    if not offering_id or not responses:
        return Response({'error': 'offering_id and responses are required'}, status=400)
    
    # Get offering and validate
    offering = get_object_or_404(SessionOffering, pk=offering_id)
    
    # CRITICAL: Check if session allows feedback submission
    if not offering.session.can_submit_feedback:
        return Response({
            'error': 'Feedback submission is not allowed for this session',
            'message': f'Session {offering.session.name} is closed or not active',
            'session': FeedbackSessionSerializer(offering.session).data
        }, status=403)
    
    # Check if student has already submitted feedback for this offering
    existing_submission = FeedbackSubmission.objects.filter(
        student=user,
        offering=offering
    ).first()
    
    if existing_submission and existing_submission.is_completed:
        return Response({'error': 'Feedback already submitted for this offering'}, status=400)
    
    # Create or update submission
    if existing_submission:
        submission = existing_submission
    else:
        submission = FeedbackSubmission.objects.create(
            session=offering.session,
            form=offering.session.forms.filter(is_active=True).first(),
            offering=offering,
            student=user,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
    
    # Process responses
    created_responses = []
    for response_data in responses:
        question_id = response_data.get('question_id')
        
        question = get_object_or_404(Question, pk=question_id)
        
        # Validate response based on question type
        if question.question_type == 'RATING' and 'rating' not in response_data:
            return Response({'error': f'Rating required for question {question_id}'}, status=400)
        elif question.question_type == 'TEXT' and 'text_response' not in response_data:
            return Response({'error': f'Text response required for question {question_id}'}, status=400)
        elif question.question_type == 'MULTIPLE_CHOICE' and 'multiple_choice_response' not in response_data:
            return Response({'error': f'Choice required for question {question_id}'}, status=400)
        
        # Create or update response
        response, created = FeedbackResponse.objects.update_or_create(
            submission=submission,
            session=offering.session,
            form=submission.form,
            offering=offering,
            student=user,
            question=question,
            defaults={
                'rating': response_data.get('rating'),
                'text_response': response_data.get('text_response', ''),
                'multiple_choice_response': response_data.get('multiple_choice_response', ''),
                'ip_address': request.META.get('REMOTE_ADDR'),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')
            }
        )
        
        created_responses.append(FeedbackResponseSerializer(response).data)
    
    # Update completion status
    submission.update_completion()
    
    return Response({
        'message': 'Feedback submitted successfully',
        'submission': FeedbackSubmissionSerializer(submission).data,
        'responses': created_responses,
        'session_status': {
            'name': offering.session.name,
            'can_submit_feedback': offering.session.can_submit_feedback,
            'is_closed': offering.session.is_closed
        }
    })


# ============================================================
# ANALYTICS VIEWS
# ============================================================

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def teacher_analytics(request):
    """Get analytics for teacher dashboard"""
    user = request.user
    
    if user.role not in ['teacher', 'hod', 'admin']:
        return Response({'error': 'Access denied'}, status=403)
    
    session_id = request.query_params.get('session')
    offering_id = request.query_params.get('offering')
    
    # Base queryset for responses
    responses = FeedbackResponse.objects.all()
    
    if session_id:
        responses = responses.filter(session_id=session_id)
    
    if offering_id:
        responses = responses.filter(offering_id=offering_id)
    elif user.role == 'teacher':
        # Teachers see only their offerings
        responses = responses.filter(offering__teacher=user)
    
    # Calculate analytics
    total_responses = responses.count()
    rating_responses = responses.filter(question__question_type='RATING')
    
    if rating_responses.exists():
        average_rating = rating_responses.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0
    else:
        average_rating = 0
    
    # Question-wise averages
    question_averages = {}
    for question in Question.objects.filter(question_type='RATING'):
        question_responses = rating_responses.filter(question=question)
        if question_responses.exists():
            avg = question_responses.aggregate(avg=Avg('rating'))['avg'] or 0
            question_averages[question.id] = {
                'text': question.text,
                'category': question.category,
                'average': round(avg, 2)
            }
    
    # Category-wise averages
    category_averages = {}
    for category in Question.QUESTION_CATEGORIES:
        category_responses = rating_responses.filter(question__category=category[0])
        if category_responses.exists():
            avg = category_responses.aggregate(avg=Avg('rating'))['avg'] or 0
            category_averages[category[0]] = round(avg, 2)
    
    # Completion rate
    total_possible_submissions = SessionOffering.objects.filter(
        session_id=session_id if session_id else None
    ).count()
    completion_rate = (total_responses / total_possible_submissions * 100) if total_possible_submissions > 0 else 0
    
    return Response({
        'total_responses': total_responses,
        'average_rating': round(average_rating, 2),
        'question_averages': question_averages,
        'category_averages': category_averages,
        'completion_rate': round(completion_rate, 2)
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def hod_analytics(request):
    """Get comprehensive analytics for HOD dashboard"""
    user = request.user
    
    if user.role not in ['hod', 'admin']:
        return Response({'error': 'Access denied'}, status=403)
    
    current_session_id = request.query_params.get('current_session')
    previous_session_id = request.query_params.get('previous_session')
    
    if not current_session_id:
        # Get latest session
        current_session = FeedbackSession.objects.filter(is_active=True).last()
        if current_session:
            current_session_id = current_session.id
    
    if not current_session_id:
        return Response({'error': 'No session specified'}, status=400)
    
    # Get current session analytics
    current_responses = FeedbackResponse.objects.filter(session_id=current_session_id)
    current_analytics = _calculate_session_analytics(current_responses)
    
    # Get previous session analytics for comparison
    previous_analytics = None
    improvement_percentage = 0
    
    if previous_session_id:
        previous_responses = FeedbackResponse.objects.filter(session_id=previous_session_id)
        previous_analytics = _calculate_session_analytics(previous_responses)
        
        # Calculate improvement percentage
        if previous_analytics['average_rating'] > 0:
            improvement_percentage = (
                (current_analytics['average_rating'] - previous_analytics['average_rating']) /
                previous_analytics['average_rating'] * 100
            )
    
    # Generate trend analysis
    trend_analysis = _generate_trend_analysis(current_analytics, previous_analytics)
    
    return Response({
        'current_session': current_analytics,
        'previous_session': previous_analytics,
        'improvement_percentage': round(improvement_percentage, 2),
        'trend_analysis': trend_analysis
    })


def _calculate_session_analytics(responses):
    """Helper function to calculate analytics for a session"""
    rating_responses = responses.filter(question__question_type='RATING')
    
    total_responses = responses.count()
    average_rating = rating_responses.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0
    
    # Question-wise averages
    question_averages = {}
    for question in Question.objects.filter(question_type='RATING'):
        question_responses = rating_responses.filter(question=question)
        if question_responses.exists():
            avg = question_responses.aggregate(avg=Avg('rating'))['avg'] or 0
            question_averages[question.id] = round(avg, 2)
    
    # Category-wise averages
    category_averages = {}
    for category in Question.QUESTION_CATEGORIES:
        category_responses = rating_responses.filter(question__category=category[0])
        if category_responses.exists():
            avg = category_responses.aggregate(avg=Avg('rating'))['avg'] or 0
            category_averages[category[0]] = round(avg, 2)
    
    # Sentiment distribution (for text responses)
    text_responses = responses.filter(question__question_type='TEXT')
    sentiment_distribution = {'positive': 0, 'neutral': 0, 'negative': 0}
    
    # This would require sentiment analysis integration
    # For now, return empty distribution
    
    return {
        'total_responses': total_responses,
        'average_rating': round(average_rating, 2),
        'question_averages': question_averages,
        'category_averages': category_averages,
        'sentiment_distribution': sentiment_distribution
    }


def _generate_trend_analysis(current, previous):
    """Generate trend analysis text"""
    if not previous:
        return "No previous session data available for comparison"
    
    if current['average_rating'] > previous['average_rating']:
        return f"Performance improved by {current['average_rating'] - previous['average_rating']:.2f} points"
    elif current['average_rating'] < previous['average_rating']:
        return f"Performance declined by {previous['average_rating'] - current['average_rating']:.2f} points"
    else:
        return "Performance remained stable compared to previous session"


# ============================================================
# REPORT GENERATION VIEWS
# ============================================================

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def generate_report(request):
    """Generate feedback report in PDF or CSV format"""
    user = request.user
    
    if user.role not in ['hod', 'admin', 'teacher']:
        return Response({'error': 'Access denied'}, status=403)
    
    report_type = request.query_params.get('type', 'teacher')
    session_id = request.query_params.get('session')
    offering_id = request.query_params.get('offering')
    format_type = request.query_params.get('format', 'pdf')
    
    # This would integrate with reportlab for PDF generation
    # For now, return a placeholder response
    
    return Response({
        'message': 'Report generation not yet implemented',
        'report_type': report_type,
        'session_id': session_id,
        'offering_id': offering_id,
        'format': format_type
    })
