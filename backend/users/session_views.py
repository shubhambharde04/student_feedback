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
    User, SubjectOffering, FeedbackResponse
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


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def hod_comprehensive_report(request, teacher_id):
    """
    Comprehensive HOD report using the new session-based feedback tables.
    Includes qualitative fields logic exactly as defined by the user.
    """
    if request.user.role not in ['hod', 'admin']:
        return Response({'error': 'Only HOD or Admin allowed'}, status=403)
        
    try:
        teacher = User.objects.get(pk=teacher_id, role__in=['teacher', 'hod'])
    except User.DoesNotExist:
        return Response({'error': 'Teacher not found'}, status=404)
        
    session_id = request.query_params.get('session')
    if session_id:
        session = get_object_or_404(FeedbackSession, pk=session_id)
    else:
        session = FeedbackSession.objects.filter(is_active=True).order_by('-year').first()
        
    if not session:
        return Response({'error': 'No active session found'}, status=404)
        
    # Get offerings for this teacher in this session
    offerings = SessionOffering.objects.filter(
        session=session,
        teacher=teacher,
        is_active=True
    ).select_related('base_offering__subject', 'base_offering__branch', 'base_offering__semester')
    
    # Get all responses for this teacher in this session
    responses = FeedbackResponse.objects.filter(
        session=session,
        offering__in=offerings
    )
    
    # Quantitative Analytics
    rating_responses = responses.filter(question__question_type='RATING')
    
    # Category-wise averages
    cat_agg = {}
    for category in Question.QUESTION_CATEGORIES:
        cat_responses = rating_responses.filter(question__category=category[0])
        if cat_responses.exists():
            avg = cat_responses.aggregate(avg=Avg('rating'))['avg'] or 0
            cat_agg[category[0]] = round(avg, 2)
            
    # Calculate overall metrics
    overall_score = sum(v for v in cat_agg.values())
    overall_percentage = round((overall_score / 25) * 100, 2) if len(cat_agg) > 0 else 0
    overall_avg = overall_score / 5 if len(cat_agg) > 0 else 0
    
    # Question-wise averages
    question_averages = {}
    for qa in rating_responses.values('question__text').annotate(avg_rating=Avg('rating')).order_by('-avg_rating'):
        question_averages[qa['question__text']] = round(qa['avg_rating'] or 0, 2)

    
    # Qualitative Analytics - Most frequent comment
    text_responses = responses.filter(question__question_type='TEXT').exclude(text_response__isnull=True).exclude(text_response='')
    
    from collections import Counter
    if text_responses.exists():
        comments = text_responses.values_list('text_response', flat=True)
        most_common = Counter(comments).most_common(1)
        key_observations = most_common[0][0] if most_common else "No specific observations derived from student comments."
    else:
        key_observations = "No specific observations derived from student comments."
        
    # Find past session comparison
    past_percentage = None
    prev_sessions = FeedbackSession.objects.filter(
        year__lt=session.year,
        type=session.type
    ).order_by('-year')
    
    if prev_sessions.exists():
        prev_session = prev_sessions.first()
        past_responses = FeedbackResponse.objects.filter(
            session=prev_session,
            offering__teacher=teacher,
            question__question_type='RATING'
        )
        if past_responses.exists():
            past_score = 0
            for category in Question.QUESTION_CATEGORIES:
                cat_responses = past_responses.filter(question__category=category[0])
                if cat_responses.exists():
                    avg = cat_responses.aggregate(avg=Avg('rating'))['avg'] or 0
                    past_score += avg
            past_percentage = round((past_score / 25) * 100, 2)
            
    # Logic for Qualitative Fields
    obs_status = "Pending"
    if overall_percentage >= 90:
        obs_status = "Completed"
    elif overall_percentage >= 70:
        obs_status = "Ongoing"
        
    faculty_resp = ""
    if obs_status == "Completed":
        faculty_resp = "Faculty member have acknowledged student feedback."
        
    trend = ""
    if past_percentage is not None and overall_percentage > past_percentage:
        trend = "FeedbackResponse is improved as compared to previous year. Excellent teaching."

    hod_comments = ""
    if trend:
        hod_comments = trend
    elif overall_avg >= 4.5:
        hod_comments = "FeedbackResponse is excellent. Students are satisfied with the faculty member."
    elif overall_avg >= 3.5:
        hod_comments = "FeedbackResponse is good. Students are satisfied with the faculty member."
    else:
        hod_comments = "FeedbackResponse is poor. Students are not satisfied, need improvements (domain...)."
        
    return Response({
        "teacher": {
            "id": teacher.id,
            "name": teacher.get_full_name() or teacher.username,
            "department": teacher.department.name if getattr(teacher, 'department', None) else "N/A"
        },
        "session": {
            "id": session.id,
            "name": session.name
        },
        "quantitative": {
            "category_averages": cat_agg,
            "question_averages": question_averages,
            "overall_percentage": overall_percentage,
            "overall_average": overall_avg,
            "total_responses": responses.values('student').distinct().count()
        },
        "qualitative": {
            "key_observations": key_observations,
            "corrective_action": "Appreciated the faculty.",
            "observation_status": obs_status,
            "faculty_response": faculty_resp,
            "hod_comments": hod_comments,
            "conclusion": "Student feedback is collected, analyzed and corrective action has been taken. Future plans includes regularly reviewing feedback to ensure continuous improvement."
        }
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
    
    offerings = SessionOffering.objects.filter(session=session, is_active=True).select_related(
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
        
    teachers_data = []
    total_answers = Answer.objects.filter(response_parent__session=session)
    
    for offering in offerings:
        offering_answers = total_answers.filter(response_parent__offering=offering)
        total_resp = offering_answers.values('response_parent').distinct().count()
        
        # Calculate threshold
        max_students = offering.max_students or 60
        threshold_met = bypass or (total_resp >= (max_students * 0.3))
        
        # calculate category averages
        cat_aggs = offering_answers.values('question__category').annotate(avg_rating=Avg('rating'))
        cats = {item['question__category']: item['avg_rating'] for item in cat_aggs}
        
        punctuality = cats.get('PUNCTUALITY', 0)
        domain = cats.get('TEACHING', 0)
        presentation = cats.get('CLARITY', 0)
        resolve = cats.get('INTERACTION', 0)
        teaching_aids = cats.get('BEHAVIOR', 0)
        
        avg_score = offering_answers.aggregate(overall=Avg('rating'))['overall'] or 0
        score_25 = float(avg_score) * 5
        percentage = (float(avg_score) / 5.0) * 100
        
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
    
    return Response({
        'department': 'Information Technology',
        'class_label': class_label,
        'session_year': f"Session: {session.name}",
        'sample_size': sample_size,
        'participation_rate': 0,
        'teachers': teachers_data,
        'overall_remarks': "Feedback is generally positive.",
        'available_branches': list(branches)
    })

