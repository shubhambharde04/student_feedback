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
    User, SubjectOffering, Answer, SubmissionTracker
)
from .serializers import (
    FeedbackSessionSerializer, QuestionSerializer, FeedbackFormSerializer,
    FormQuestionMappingSerializer, SessionOfferingSerializer,
    FeedbackResponseSerializer, 
     AnalyticsSerializer,
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
            'message': f'FeedbackResponse for session {session.name} has been ended. No further submissions allowed.',
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
            # Students see offerings for their branch and semester via StudentSemester
            from .models import StudentSemester
            student_sem = StudentSemester.objects.filter(
                student=user, is_active=True
            ).select_related('branch', 'semester').order_by('-session__year').first()
            if student_sem:
                queryset = queryset.filter(
                    base_offering__branch=student_sem.branch,
                    base_offering__semester=student_sem.semester,
                    is_active=True,
                    teacher__isnull=False  # Only show subjects with assigned teachers
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
    """Get the active feedback form for the current session.
    
    Auto-syncs SessionOffering records from SubjectOffering + SubjectAssignment
    when they don't exist yet for the student's branch/semester, so students
    see every subject the HOD has assigned to a teacher.
    """
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
            'message': 'FeedbackResponse collection is currently closed'
        }, status=404)
    
    # Check if session allows feedback submission
    if not current_session.can_submit_feedback:
        return Response({
            'error': 'FeedbackResponse submission is not allowed at this time',
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
    
    # Get student's enrollment for this session via StudentSemester
    from .models import StudentSemester, SubjectAssignment
    student_semester = StudentSemester.objects.filter(
        student=user,
        session=current_session,
        is_active=True
    ).select_related('branch', 'semester').first()
    
    if not student_semester:
        return Response({
            'error': 'You are not enrolled in the current feedback session',
            'message': 'Please contact your HOD to enroll you in this session.'
        }, status=404)
    
    student_branch = student_semester.branch
    student_sem = student_semester.semester
    
    # --- RESOLVE BRANCH: handle duplicate/variant branches ---
    # If the student's exact branch has no SubjectOffering records,
    # look for a related branch that DOES have offerings for this semester.
    # This handles cases where students are imported under "IT" (id=13)
    # but offerings exist under "Information Technology" (IT101, id=1).
    from .models import Branch as BranchModel
    
    offering_branch = student_branch  # default: use student's own branch
    
    has_direct_offerings = SubjectOffering.objects.filter(
        branch=student_branch,
        semester=student_sem,
        is_active=True,
    ).exists()
    
    if not has_direct_offerings:
        # Try to find a related branch that has offerings for this semester
        branch_name_lower = student_branch.name.lower()
        branch_code_lower = student_branch.code.lower()
        
        candidate_branches = BranchModel.objects.exclude(id=student_branch.id)
        
        for candidate in candidate_branches:
            # Match by: branch code is a prefix/substring of candidate name,
            # or candidate code is a prefix/substring of student branch name,
            # or they share the same department
            name_match = (
                branch_code_lower in candidate.name.lower() or
                branch_name_lower in candidate.name.lower() or
                candidate.code.lower() in branch_name_lower or
                candidate.name.lower() in branch_name_lower
            )
            dept_match = (
                student_branch.department_id and 
                candidate.department_id and 
                student_branch.department_id == candidate.department_id
            )
            
            if name_match or dept_match:
                has_offerings = SubjectOffering.objects.filter(
                    branch=candidate,
                    semester=student_sem,
                    is_active=True,
                ).exists()
                if has_offerings:
                    print(f"[active-form] Branch resolve: student branch "
                          f"'{student_branch.code}' (id={student_branch.id}) -> "
                          f"offering branch '{candidate.code}' (id={candidate.id})")
                    offering_branch = candidate
                    break
    
    # --- AUTO-SYNC: Create SessionOffering records from SubjectOffering ---
    # Find SubjectOfferings for the resolved branch+semester that have a teacher
    # assigned but do NOT yet have a SessionOffering for the active session.
    base_offerings_with_teacher = SubjectOffering.objects.filter(
        branch=offering_branch,
        semester=student_sem,
        is_active=True,
        assignment__is_active=True,     # has an active teacher assignment
    ).select_related('assignment__teacher').exclude(
        session_offerings__session=current_session  # not already linked
    )
    
    created_count = 0
    for offering in base_offerings_with_teacher:
        teacher = offering.assignment.teacher
        SessionOffering.objects.get_or_create(
            session=current_session,
            base_offering=offering,
            defaults={
                'teacher': teacher,
                'max_students': offering.max_students,
                'is_active': True,
            }
        )
        created_count += 1
    
    if created_count:
        print(f"[active-form] Auto-created {created_count} SessionOfferings "
              f"for {offering_branch.code} Sem {student_sem.number}")
    
    # --- QUERY: Get all SessionOfferings for this student ---
    # Query using the resolved offering_branch
    student_offerings = SessionOffering.objects.filter(
        session=current_session,
        base_offering__branch=offering_branch,
        base_offering__semester=student_sem,
        is_active=True,
        teacher__isnull=False  # Only show subjects with assigned teachers
    ).select_related(
        'base_offering__subject', 'base_offering__branch',
        'base_offering__semester', 'teacher', 'session'
    )
    
    # Check which offerings the student has already submitted feedback for
    from .models import SubmissionTracker
    submitted_offerings = set(SubmissionTracker.objects.filter(
        student=user,
        session=current_session
    ).values_list('offering_id', flat=True))
    
    # Serialize all offerings and add feedback_submitted flag
    serialized_offerings = SessionOfferingSerializer(student_offerings, many=True).data
    for offering in serialized_offerings:
        offering['feedback_submitted'] = offering['id'] in submitted_offerings
    
    return Response({
        'session': FeedbackSessionSerializer(current_session).data,
        'form': FeedbackFormSerializer(active_form).data,
        'subjects': serialized_offerings,
        'submitted_count': len(submitted_offerings),
        'total_offerings': student_offerings.count(),
        'can_submit_feedback': current_session.can_submit_feedback
    })


from django_ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='5/m', block=True)
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
    
    from .models import SubmissionTracker, FeedbackResponse, Answer
    
    # Check if student has already submitted feedback for this offering
    existing_submission = SubmissionTracker.objects.filter(
        student=user,
        offering=offering
    ).first()
    
    if existing_submission:
        return Response({'error': 'Feedback already submitted for this offering'}, status=400)
    
    from django.db import transaction
    
    try:
        with transaction.atomic():
            overall_remark = request.data.get('overall_remark', '')
            
            # 1. Create the ANONYMOUS FeedbackResponse Wrapper
            form = offering.session.forms.filter(is_active=True).first()
            if not form:
                raise Exception("No active form found for this session")
            
            feedback_wrapper = FeedbackResponse.objects.create(
                session=offering.session,
                form=form,
                offering=offering,
                teacher=offering.teacher,
                overall_remark=overall_remark
            )
            
            # 2. Process responses and create Answer objects
            total_rating = 0
            rating_count = 0
            created_responses = []
            
            for response_data in responses:
                question_id = response_data.get('question_id')
                question = get_object_or_404(Question, pk=question_id)
                rating = response_data.get('rating')
                
                if rating is not None:
                    try:
                        rating = int(rating)
                        total_rating += rating
                        rating_count += 1
                    except (ValueError, TypeError):
                        pass

                answer = Answer.objects.create(
                    response_parent=feedback_wrapper,
                    question=question,
                    rating=rating,
                    text_response=response_data.get('text_response', ''),
                    choice_response=response_data.get('multiple_choice_response', '')
                )
                created_responses.append({
                    'question_id': question.id,
                    'rating': rating
                })
            
            # Update sentiment based on overall rating
            if rating_count > 0:
                overall_avg = total_rating / rating_count
                feedback_wrapper.sentiment_score = overall_avg
                if overall_avg >= 4.5:
                    feedback_wrapper.sentiment_label = 'positive'
                elif overall_avg < 3.0:
                    feedback_wrapper.sentiment_label = 'negative'
                else:
                    feedback_wrapper.sentiment_label = 'neutral'
                feedback_wrapper.save()
            
            # 3. Create SECURE Tracker linking Student to the Wrapper
            # This prevents duplicates without exposing student identity directly in reports
            SubmissionTracker.objects.create(
                student=user,
                session=offering.session,
                offering=offering,
                response_set=feedback_wrapper
            )

            # 🔥 SYNC TO LEGACY FEEDBACK TABLE (for user's SQL tool visibility)
            category_map = {
                'PUNCTUALITY': 'punctuality_rating',
                'TEACHING': 'teaching_rating',
                'CLARITY': 'clarity_rating',
                'INTERACTION': 'interaction_rating',
                'BEHAVIOR': 'behavior_rating'
            }
            
            legacy_data = {
                'punctuality_rating': 5,
                'teaching_rating': 5,
                'clarity_rating': 5,
                'interaction_rating': 5,
                'behavior_rating': 5,
                'comment': overall_remark,
                'sentiment': feedback_wrapper.sentiment_label,
                'overall_rating': round(feedback_wrapper.sentiment_score, 2)
            }
            
            from django.db.models import Avg
            # Calculate averages for each category from the newly created Answers
            for cat, field in category_map.items():
                cat_avg = Answer.objects.filter(
                    response_parent=feedback_wrapper, 
                    question__category=cat
                ).aggregate(Avg('rating'))['rating__avg']
                if cat_avg:
                    legacy_data[field] = int(round(cat_avg))
            
            from .models import FeedbackSubmission
            # Store in the legacy model (FeedbackSubmission)
            legacy_sub, _ = FeedbackSubmission.objects.update_or_create(
                student=user,
                offering=offering,
                session=offering.session,
                form=form,
                defaults={'is_completed': True, 'overall_remark': overall_remark}
            )

        return Response({
            'message': 'Feedback submitted successfully',
            'responses_saved': len(created_responses),
            'wrapper_id': str(feedback_wrapper.id)
        }, status=201)

    except Exception as e:
        print(f"Error submitting feedback securely: {e}")
        return Response({'error': f'Failed to store feedback: {str(e)}'}, status=500)


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
    
    # Force focus on the ACTIVE session only
    active_session = FeedbackSession.objects.filter(is_active=True).last()
    if not active_session:
        return Response({'error': 'No active session found'}, status=404)
    
    offering_id = request.query_params.get('offering')
    
    # Base queryset for responses (Filtered by active session)
    responses = FeedbackResponse.objects.filter(session=active_session)
    
    if offering_id:
        responses = responses.filter(offering_id=offering_id)
    elif user.role == 'teacher':
        # Teachers see only their offerings
        responses = responses.filter(offering__teacher=user)
    
    # Calculate analytics
    total_responses = responses.count()
    
    # Correct way: Filter Answers, not FeedbackResponse
    answers = Answer.objects.filter(response_parent__in=responses)
    rating_answers = answers.filter(question__question_type='RATING')
    
    if rating_answers.exists():
        average_rating = rating_answers.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0
    else:
        average_rating = 0
    
    # Question-wise averages
    question_averages = {}
    for question in Question.objects.filter(question_type='RATING'):
        question_responses = rating_answers.filter(question=question)
        if question_responses.exists():
            avg = question_responses.aggregate(avg=Avg('rating'))['avg'] or 0
            question_averages[str(question.id)] = {
                'text': question.text,
                'category': question.category,
                'average': round(avg, 2)
            }
    
    # Category-wise averages
    category_averages = {}
    for category in Question.QUESTION_CATEGORIES:
        category_responses = rating_answers.filter(question__category=category[0])
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
    
    # Force focus on the ACTIVE session only
    current_session = FeedbackSession.objects.filter(is_active=True).last()
    
    if not current_session:
        return Response({'error': 'No active session found'}, status=404)
    
    current_session_id = current_session.id
    
    # Calculate current session analytics (Strictly current)
    current_responses = FeedbackResponse.objects.filter(session_id=current_session_id)
    current_analytics = _calculate_session_analytics(current_responses)
    
    return Response({
        'current_session': current_analytics,
        'message': f"Showing analytics for active session: {current_session.name}",
        'session_info': {
            'id': current_session.id,
            'name': current_session.name,
            'year': current_session.year
        }
    })


def _calculate_session_analytics(responses):
    """Helper function to calculate analytics for a session"""
    total_responses = responses.count()
    
    # Correct way: Filter Answers
    answers = Answer.objects.filter(response_parent__in=responses)
    rating_answers = answers.filter(question__question_type='RATING')
    
    average_rating = rating_answers.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0
    
    # Question-wise averages
    question_averages = {}
    for question in Question.objects.filter(question_type='RATING'):
        question_responses = rating_answers.filter(question=question)
        if question_responses.exists():
            avg = question_responses.aggregate(avg=Avg('rating'))['avg'] or 0
            question_averages[str(question.id)] = round(avg, 2)
    
    # Category-wise averages
    category_averages = {}
    for category in Question.QUESTION_CATEGORIES:
        category_responses = rating_answers.filter(question__category=category[0])
        if category_responses.exists():
            avg = category_responses.aggregate(avg=Avg('rating'))['avg'] or 0
            category_averages[category[0]] = round(avg, 2)
    
    # Sentiment distribution (for text responses)
    text_responses = answers.filter(question__question_type='TEXT')
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


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def hod_comprehensive_report(request, teacher_id):
    """
    Comprehensive HOD report using the new session-based feedback tables.
    Returns per-offering quantitative data + qualitative fields for the GPN report format.
    """
    if request.user.role not in ['hod', 'admin']:
        return Response({'error': 'Only HOD or Admin allowed'}, status=403)
        
    try:
        teacher = User.objects.get(pk=teacher_id, role__in=['teacher', 'hod'])
    except User.DoesNotExist:
        return Response({'error': 'Teacher not found'}, status=404)
        
    # Accept both 'session_id' (frontend) and 'session' (legacy) query params
    session_id = request.query_params.get('session_id') or request.query_params.get('session')
    if session_id:
        session = get_object_or_404(FeedbackSession, pk=session_id)
    else:
        session = FeedbackSession.objects.filter(is_active=True).order_by('-year').first()
        
    if not session:
        return Response({'error': 'No active session found'}, status=404)

    bypass = request.query_params.get('bypass_threshold') == 'true'
        
    # Get offerings for this teacher in this session
    offerings = SessionOffering.objects.filter(
        session=session,
        teacher=teacher,
        is_active=True
    ).select_related('base_offering__subject', 'base_offering__branch', 'base_offering__semester')

    if not offerings.exists():
        return Response({
            'data_available': False,
            'session': session.name,
            'no_data_message': f'No subject offerings found for {teacher.get_full_name() or teacher.username} in session {session.name}.'
        })
    
    # ================================================================
    # BUILD PER-OFFERING ROWS (one row per subject the teacher teaches)
    # ================================================================
    from collections import Counter
    from datetime import date

    all_answers = Answer.objects.filter(
        response_parent__session=session,
        response_parent__offering__in=offerings
    )
    all_rating_answers = all_answers.filter(question__question_type='RATING')
    all_responses = FeedbackResponse.objects.filter(session=session, offering__in=offerings)

    offerings_data = []
    semester_labels = set()

    for offering in offerings:
        sem = offering.base_offering.semester
        semester_labels.add(sem.name if hasattr(sem, 'name') else f"Semester {sem.number}")

        # Get rating answers for this specific offering
        offering_answers = all_rating_answers.filter(response_parent__offering=offering)
        total_resp = offering_answers.values('response_parent').distinct().count()

        # Calculate threshold based on branch capacity
        branch_name = offering.base_offering.branch.name.upper() if offering.base_offering.branch else ''
        if 'AI' in branch_name or 'ARTIFICIAL' in branch_name:
            max_students = 40
        elif 'IT' in branch_name or 'INFORMATION' in branch_name:
            max_students = 80
        else:
            max_students = offering.max_students or 60
            
        threshold_met = bypass or (total_resp >= (max_students * 0.3))

        # Category averages for this offering
        cat_aggs = offering_answers.values('question__category').annotate(avg_rating=Avg('rating'))
        cats = {item['question__category']: round(float(item['avg_rating'] or 0), 4) for item in cat_aggs}

        punctuality = cats.get('PUNCTUALITY', 0)
        domain_knowledge = cats.get('TEACHING', 0)
        presentation_skills = cats.get('CLARITY', 0)
        resolve_difficulties = cats.get('INTERACTION', 0)
        teaching_aids = cats.get('BEHAVIOR', 0)

        # Score out of 25 is exactly the sum of the 5 categories (each out of 5)
        sum_categories = punctuality + domain_knowledge + presentation_skills + resolve_difficulties + teaching_aids
        score_25 = float(sum_categories)
        percentage = (score_25 / 25.0) * 100

        offerings_data.append({
            'course_name': offering.base_offering.subject.name,
            'course_code': offering.base_offering.subject.code,
            'punctuality': punctuality,
            'domain_knowledge': domain_knowledge,
            'presentation_skills': presentation_skills,
            'resolve_difficulties': resolve_difficulties,
            'teaching_aids': teaching_aids,
            'score': round(score_25, 4),
            'percentage': round(percentage, 2),
            'threshold_met': threshold_met,
            'feedback_percentage': int((total_resp / max_students) * 100) if max_students > 0 else 0
        })

    # ================================================================
    # OVERALL PERCENTAGE across all offerings
    # ================================================================
    overall_avg_val = all_rating_answers.aggregate(overall=Avg('rating'))['overall'] or 0
    overall_avg = float(overall_avg_val)
    overall_percentage = round((overall_avg / 5.0) * 100, 2)

    # ================================================================
    # SECTION 2: PAST FEEDBACK (Comparative Study)
    # ================================================================
    past_comparison = None
    prev_session = FeedbackSession.objects.filter(
        year__lt=session.year,
        type=session.type
    ).order_by('-year').first()

    if prev_session:
        past_answers = Answer.objects.filter(
            response_parent__session=prev_session,
            response_parent__offering__teacher=teacher,
            question__question_type='RATING'
        )
        if past_answers.exists():
            past_avg = past_answers.aggregate(avg=Avg('rating'))['avg'] or 0
            past_pct = round((float(past_avg) / 5.0) * 100, 2)
            past_comparison = {
                'percentage': past_pct,
                'session_name': prev_session.name,
            }
        else:
            past_comparison = {
                'percentage': None,
                'note': 'No past data available for this teacher.',
                'session_name': prev_session.name,
            }

    # ================================================================
    # SECTION 3: KEY OBSERVATIONS (most frequent student comment/remark)
    # ================================================================
    # Check overall remarks from FeedbackResponse first
    remark_responses = all_responses.exclude(
        overall_remark__isnull=True
    ).exclude(overall_remark='')

    if remark_responses.exists():
        remarks = remark_responses.values_list('overall_remark', flat=True)
        most_common = Counter(remarks).most_common(1)
        key_observations = most_common[0][0] if most_common else "Good Teaching"
    else:
        # Fallback to text answers
        text_answers = all_answers.filter(
            question__question_type='TEXT'
        ).exclude(text_response__isnull=True).exclude(text_response='')
        if text_answers.exists():
            comments = text_answers.values_list('text_response', flat=True)
            most_common = Counter(comments).most_common(1)
            key_observations = most_common[0][0] if most_common else "Good Teaching"
        else:
            key_observations = "Good Teaching"

    # Corrective action: most frequent positive remark (exact words)
    corrective_action = "Appreciated the faculty."
    if remark_responses.exists():
        all_remarks = list(remark_responses.values_list('overall_remark', flat=True))
        positive_keywords = ['good', 'excellent', 'great', 'best', 'nice', 'appreciated', 'helpful', 'clear']
        positive_remarks = [r for r in all_remarks if any(kw in r.lower() for kw in positive_keywords)]
        if positive_remarks:
            most_common_positive = Counter(positive_remarks).most_common(1)
            corrective_action = most_common_positive[0][0]

    # ================================================================
    # STATUS based on overall percentage thresholds
    # <70% = Pending, 70-90% = Ongoing, >=90% = Completed (only if feedback threshold is met)
    # ================================================================
    any_threshold_met = any(o['threshold_met'] for o in offerings_data)
    
    if overall_percentage >= 90 and any_threshold_met:
        obs_status = "Completed"
    elif overall_percentage >= 70 and any_threshold_met:
        obs_status = "Ongoing"
    else:
        obs_status = "Pending"

    # ================================================================
    # SECTION 4: FACULTY RESPONSE (exact words)
    # ================================================================
    faculty_resp = "Faculty member have acknowledged student feedback."

    # ================================================================
    # SECTION 5: HOD COMMENTS
    # ================================================================
    past_pct_value = past_comparison['percentage'] if past_comparison and past_comparison.get('percentage') is not None else None

    hod_comments = ""
    # If feedback is excellent AND improved from past session
    if overall_avg >= 4.5 and past_pct_value is not None and overall_percentage > past_pct_value:
        hod_comments = (
            "Feedback is excellent Students are satisfied with the faculty member.\n"
            "Feedback is improved as compared to previous year. Excellent teaching."
        )
    elif past_pct_value is not None and overall_percentage > past_pct_value:
        hod_comments = "Feedback is improved as compared to previous year. Excellent teaching."
    elif overall_avg >= 4.5:
        hod_comments = "Feedback is excellent Students are satisfied with the faculty member."
    elif overall_avg >= 3.5:
        hod_comments = "Feedback is good. Students are satisfied with the faculty member."
    else:
        hod_comments = "Feedback needs improvement. Students have raised concerns."

    # ================================================================
    # SECTION 6: CONCLUSION (exact words)
    # ================================================================
    conclusion = (
        "Student feedback is collected, analyzed and corrective action has been taken. "
        "Future plans includes regularly reviewing feedback to ensure continuous improvement."
    )

    # ================================================================
    # METADATA
    # ================================================================
    department_name = "N/A"
    if getattr(teacher, 'department', None) and teacher.department:
        department_name = teacher.department.name
    elif getattr(request.user, 'department', None) and request.user.department:
        department_name = request.user.department.name

    semester_label = ', '.join(sorted(semester_labels)) if semester_labels else 'N/A'

    return Response({
        "data_available": True,
        "teacher": {
            "id": teacher.id,
            "name": teacher.get_full_name() or teacher.username,
            "department": department_name
        },
        "session": session.name,
        "session_info": {
            "id": session.id,
            "name": session.name,
            "year": session.year,
            "type": session.type
        },
        "department": department_name + " Department",
        "semester_label": semester_label,
        "report_date": date.today().strftime('%d/%m/%Y'),
        "offerings": offerings_data,
        "overall_percentage": overall_percentage,
        "past_comparison": past_comparison,
        # Flat qualitative fields for direct frontend binding
        "key_observations": key_observations,
        "corrective_action": corrective_action,
        "observation_status": obs_status,
        "faculty_response": faculty_resp,
        "hod_comments": hod_comments,
        "conclusion": conclusion,
    })



@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def hod_department_comprehensive_report(request):
    """Class Report (Cumulative) for HOD"""
    if request.user.role not in ['hod', 'admin']:
        return Response({'error': 'Only HOD or Admin allowed'}, status=403)
        
    session_id = request.query_params.get('session_id')
    branch_id = request.query_params.get('branch')
    year = request.query_params.get('year')
    bypass = request.query_params.get('bypass_threshold') == 'true'
    
    if session_id:
        session = get_object_or_404(FeedbackSession, pk=session_id)
    else:
        session = FeedbackSession.objects.filter(is_active=True).order_by('-year').first()
        if not session:
            return Response({'error': 'No active session found'}, status=404)
            
    # Base filter for offerings in this session
    from .models import SessionOffering, Answer, Branch
    from django.db.models import Avg, Count
    
    offerings = SessionOffering.objects.filter(
        session=session, is_active=True, teacher__isnull=False
    ).select_related(
        'teacher', 'base_offering__subject', 'base_offering__branch', 'base_offering__semester'
    )
    
    if branch_id:
        offerings = offerings.filter(base_offering__branch_id=branch_id)
    if year:
        # year 1 = sem 1,2; year 2 = sem 3,4; year 3 = sem 5,6
        sem_nums = [int(year)*2 - 1, int(year)*2]
        offerings = offerings.filter(base_offering__semester__number__in=sem_nums)
        
    if not offerings.exists():
        return Response({
            'data_available': False,
            'session': session.name,
            'no_data_message': 'No subjects found for the selected criteria.'
        })
        
    from datetime import date

    teachers_data = []
    total_answers = Answer.objects.filter(response_parent__session=session)
    total_max_students = 0
    total_respondents = 0
    
    for offering in offerings:
        offering_answers = total_answers.filter(response_parent__offering=offering)
        total_resp = offering_answers.values('response_parent').distinct().count()
        
        # Calculate threshold based on branch capacity
        branch_name = offering.base_offering.branch.name.upper() if offering.base_offering.branch else ''
        if 'AI' in branch_name or 'ARTIFICIAL' in branch_name:
            max_students = 40
        elif 'IT' in branch_name or 'INFORMATION' in branch_name:
            max_students = 80
        else:
            max_students = offering.max_students or 60
            
        threshold_met = bypass or (total_resp >= (max_students * 0.3))

        # Track totals for participation rate
        total_max_students += max_students
        total_respondents += total_resp
        
        # calculate category averages
        cat_aggs = offering_answers.values('question__category').annotate(avg_rating=Avg('rating'))
        cats = {item['question__category']: round(float(item['avg_rating'] or 0), 4) for item in cat_aggs}
        
        punctuality = cats.get('PUNCTUALITY', 0)
        domain = cats.get('TEACHING', 0)
        presentation = cats.get('CLARITY', 0)
        resolve = cats.get('INTERACTION', 0)
        teaching_aids = cats.get('BEHAVIOR', 0)
        
        # Score out of 25 is exactly the sum of the 5 categories (each out of 5)
        sum_categories = punctuality + domain + presentation + resolve + teaching_aids
        score_25 = round(float(sum_categories), 4)
        percentage = round((score_25 / 25.0) * 100, 2)
        
        teachers_data.append({
            'faculty': offering.teacher.get_full_name() if offering.teacher else 'Unassigned',
            'course_name': offering.base_offering.subject.name,
            'course_code': offering.base_offering.subject.code,
            'punctuality': float(punctuality),
            'domain_knowledge': float(domain),
            'presentation_skills': float(presentation),
            'resolve_difficulties': float(resolve),
            'teaching_aids': float(teaching_aids),
            'score': score_25,
            'percentage': percentage,
            'threshold_met': threshold_met,
            'feedback_percentage': int((total_resp / max_students) * 100) if max_students > 0 else 0
        })
        
    class_label = "All Branches, All Years"
    if branch_id and year:
        b = Branch.objects.get(pk=branch_id)
        class_label = f"{b.name} - Year {year}"
    elif branch_id:
        b = Branch.objects.get(pk=branch_id)
        class_label = f"{b.name} - All Years"
    elif year:
        class_label = f"All Branches - Year {year}"
        
    branches = Branch.objects.all().values('id', 'name', 'code')
    sample_size = total_answers.filter(response_parent__offering__in=offerings).values('response_parent').distinct().count()

    # Calculate actual participation rate
    participation_rate = round((total_respondents / total_max_students) * 100, 1) if total_max_students > 0 else 0

    # Use HOD's actual department
    department_name = "Information Technology"
    if getattr(request.user, 'department', None) and request.user.department:
        department_name = request.user.department.name

    # Dynamic overall remarks based on data
    if teachers_data:
        avg_pct = sum(t['percentage'] for t in teachers_data) / len(teachers_data)
        if avg_pct >= 90:
            overall_remarks = "Feedback is excellent. Students are highly satisfied with the faculty members."
        elif avg_pct >= 75:
            overall_remarks = "Feedback is good. Students are generally satisfied with the faculty members."
        elif avg_pct >= 60:
            overall_remarks = "Feedback is satisfactory. Some areas need improvement."
        else:
            overall_remarks = "Feedback needs improvement. Faculty members should address student concerns."
    else:
        overall_remarks = "No feedback data available."
    
    return Response({
        'data_available': True,
        'department': department_name + " Department",
        'class_label': class_label,
        'session_year': f"Session: {session.name}",
        'sample_size': sample_size,
        'participation_rate': participation_rate,
        'teachers': teachers_data,
        'overall_remarks': overall_remarks,
        'available_branches': list(branches),
        'report_date': date.today().strftime('%d/%m/%Y'),
    })

