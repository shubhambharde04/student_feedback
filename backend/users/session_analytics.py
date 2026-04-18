from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, NotFound
from django.db.models import Avg, Count, Q, F, FloatField
from django.db.models.functions import Cast
from django.shortcuts import get_object_or_404

from .models import (
    FeedbackSession, FeedbackResponse, SessionOffering, FeedbackSubmission,
    User, Question
)
from .serializers import (
    FeedbackSessionSerializer, SessionOfferingSerializer, AnalyticsSerializer
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def session_comparison_analytics(request):
    """
    Core session comparison analytics - compares current session with previous session
    This is the main analytics endpoint that implements the session-based comparison logic
    """
    user = request.user
    
    if user.role not in ['hod', 'admin', 'teacher']:
        raise PermissionDenied("Access denied")
    
    current_session_id = request.query_params.get('current_session')
    comparison_type = request.query_params.get('type', 'overview')  # overview, subject, teacher, class
    
    if not current_session_id:
        # Get the most recent active session
        current_session = FeedbackSession.objects.filter(
            is_active=True
        ).order_by('-year', '-type').first()
        
        if not current_session:
            return Response({'error': 'No active session found'}, status=404)
    else:
        current_session = get_object_or_404(FeedbackSession, pk=current_session_id)
    
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
    
    # Generate comparison based on type
    if comparison_type == 'overview':
        return generate_overview_comparison(current_session, previous_session, user)
    elif comparison_type == 'subject':
        return generate_subject_comparison(current_session, previous_session, user)
    elif comparison_type == 'teacher':
        return generate_teacher_comparison(current_session, previous_session, user)
    elif comparison_type == 'class':
        return generate_class_comparison(current_session, previous_session, user)
    else:
        return Response({'error': 'Invalid comparison type'}, status=400)


def generate_overview_comparison(current_session, previous_session, user):
    """Generate overall session comparison"""
    
    # Current session analytics
    current_data = calculate_session_overview(current_session, user)
    
    # Previous session analytics
    previous_data = calculate_session_overview(previous_session, user)
    
    # Calculate improvements
    improvements = calculate_improvements(current_data, previous_data)
    
    return Response({
        'comparison_type': 'overview',
        'current_session': {
            'session': FeedbackSessionSerializer(current_session).data,
            'analytics': current_data
        },
        'previous_session': {
            'session': FeedbackSessionSerializer(previous_session).data,
            'analytics': previous_data
        },
        'improvements': improvements,
        'trend_analysis': generate_trend_text(improvements)
    })


def generate_subject_comparison(current_session, previous_session, user):
    """Generate subject-wise comparison"""
    
    # Get subjects for both sessions
    current_subjects = get_session_subject_data(current_session, user)
    previous_subjects = get_session_subject_data(previous_session, user)
    
    # Compare subjects
    subject_comparisons = []
    for current_subj in current_subjects:
        subject_name = current_subj['subject_name']
        previous_subj = next((s for s in previous_subjects if s['subject_name'] == subject_name), None)
        
        if previous_subj:
            comparison = {
                'subject_name': subject_name,
                'subject_code': current_subj['subject_code'],
                'current': current_subj,
                'previous': previous_subj,
                'improvement': calculate_rating_improvement(current_subj['average_rating'], previous_subj['average_rating']),
                'response_change': current_subj['total_responses'] - previous_subj['total_responses']
            }
        else:
            comparison = {
                'subject_name': subject_name,
                'subject_code': current_subj['subject_code'],
                'current': current_subj,
                'previous': None,
                'improvement': None,
                'response_change': None
            }
        
        subject_comparisons.append(comparison)
    
    return Response({
        'comparison_type': 'subject',
        'current_session': FeedbackSessionSerializer(current_session).data,
        'previous_session': FeedbackSessionSerializer(previous_session).data,
        'subject_comparisons': subject_comparisons
    })


def generate_teacher_comparison(current_session, previous_session, user):
    """Generate teacher-wise comparison"""
    
    # Get teachers for both sessions
    current_teachers = get_session_teacher_data(current_session, user)
    previous_teachers = get_session_teacher_data(previous_session, user)
    
    # Compare teachers
    teacher_comparisons = []
    for current_teacher in current_teachers:
        teacher_name = current_teacher['teacher_name']
        previous_teacher = next((t for t in previous_teachers if t['teacher_name'] == teacher_name), None)
        
        if previous_teacher:
            comparison = {
                'teacher_name': teacher_name,
                'current': current_teacher,
                'previous': previous_teacher,
                'improvement': calculate_rating_improvement(current_teacher['average_rating'], previous_teacher['average_rating']),
                'response_change': current_teacher['total_responses'] - previous_teacher['total_responses']
            }
        else:
            comparison = {
                'teacher_name': teacher_name,
                'current': current_teacher,
                'previous': None,
                'improvement': None,
                'response_change': None
            }
        
        teacher_comparisons.append(comparison)
    
    return Response({
        'comparison_type': 'teacher',
        'current_session': FeedbackSessionSerializer(current_session).data,
        'previous_session': FeedbackSessionSerializer(previous_session).data,
        'teacher_comparisons': teacher_comparisons
    })


def generate_class_comparison(current_session, previous_session, user):
    """Generate class-wise comparison"""
    
    # Get classes for both sessions
    current_classes = get_session_class_data(current_session, user)
    previous_classes = get_session_class_data(previous_session, user)
    
    # Compare classes
    class_comparisons = []
    for current_class in current_classes:
        class_name = current_class['class_name']
        previous_class = next((c for c in previous_classes if c['class_name'] == class_name), None)
        
        if previous_class:
            comparison = {
                'class_name': class_name,
                'current': current_class,
                'previous': previous_class,
                'improvement': calculate_rating_improvement(current_class['average_rating'], previous_class['average_rating']),
                'response_change': current_class['total_responses'] - previous_class['total_responses']
            }
        else:
            comparison = {
                'class_name': class_name,
                'current': current_class,
                'previous': None,
                'improvement': None,
                'response_change': None
            }
        
        class_comparisons.append(comparison)
    
    return Response({
        'comparison_type': 'class',
        'current_session': FeedbackSessionSerializer(current_session).data,
        'previous_session': FeedbackSessionSerializer(previous_session).data,
        'class_comparisons': class_comparisons
    })


# Helper functions for data calculation

def calculate_session_overview(session, user):
    """Calculate overview analytics for a session"""
    
    # Base queryset for responses
    responses = FeedbackResponse.objects.filter(session=session)
    
    if user.role == 'teacher':
        # Teachers see only their data
        responses = responses.filter(offering__teacher=user)
    
    # Calculate basic metrics
    total_responses = responses.count()
    rating_responses = responses.filter(question__question_type='RATING')
    
    if rating_responses.exists():
        average_rating = rating_responses.aggregate(
            avg_rating=Avg('rating')
        )['avg_rating'] or 0
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
    
    # Completion metrics
    total_offerings = SessionOffering.objects.filter(session=session)
    if user.role == 'teacher':
        total_offerings = total_offerings.filter(teacher=user)
    
    total_possible_submissions = total_offerings.count()
    completed_submissions = FeedbackSubmission.objects.filter(
        session=session,
        is_completed=True
    )
    
    if user.role == 'teacher':
        completed_submissions = completed_submissions.filter(offering__teacher=user)
    
    completion_rate = (completed_submissions.count() / total_possible_submissions * 100) if total_possible_submissions > 0 else 0
    
    return {
        'total_responses': total_responses,
        'average_rating': round(average_rating, 2),
        'question_averages': question_averages,
        'category_averages': category_averages,
        'completion_rate': round(completion_rate, 2),
        'total_submissions': completed_submissions.count(),
        'total_offerings': total_possible_submissions
    }


def get_session_subject_data(session, user):
    """Get subject-wise data for a session"""
    
    # SQL Query equivalent: 
    # SELECT subject_id, AVG(rating) as avg_rating, COUNT(*) as total_responses
    # FROM feedback_response fr
    # JOIN session_offering so ON fr.offering_id = so.id
    # JOIN subject_offering bo ON so.base_offering_id = bo.id
    # JOIN subject s ON bo.subject_id = s.id
    # WHERE fr.session_id = session_id AND fr.question_type = 'RATING'
    # GROUP BY subject_id
    
    subject_data = []
    
    # Get subjects with their offerings
    offerings = SessionOffering.objects.filter(session=session)
    if user.role == 'teacher':
        offerings = offerings.filter(teacher=user)
    
    subjects = {}
    for offering in offerings:
        subject_key = offering.base_offering.subject.id
        if subject_key not in subjects:
            subjects[subject_key] = {
                'subject_id': subject_key,
                'subject_name': offering.base_offering.subject.name,
                'subject_code': offering.base_offering.subject.code,
                'offerings': []
            }
        subjects[subject_key]['offerings'].append(offering)
    
    # Calculate metrics for each subject
    for subject_id, subject_info in subjects.items():
        offerings = subject_info['offerings']
        
        # Get all rating responses for this subject
        responses = FeedbackResponse.objects.filter(
            session=session,
            offering__in=offerings,
            question__question_type='RATING'
        )
        
        if responses.exists():
            average_rating = responses.aggregate(avg=Avg('rating'))['avg'] or 0
        else:
            average_rating = 0
        
        subject_data.append({
            'subject_id': subject_id,
            'subject_name': subject_info['subject_name'],
            'subject_code': subject_info['subject_code'],
            'average_rating': round(average_rating, 2),
            'total_responses': responses.count(),
            'total_offerings': len(offerings)
        })
    
    return subject_data


def get_session_teacher_data(session, user):
    """Get teacher-wise data for a session"""
    
    teacher_data = []
    
    # Get teachers with their offerings
    offerings = SessionOffering.objects.filter(session=session)
    if user.role == 'teacher':
        offerings = offerings.filter(teacher=user)
    
    teachers = {}
    for offering in offerings:
        teacher_key = offering.teacher.id
        if teacher_key not in teachers:
            teachers[teacher_key] = {
                'teacher_id': teacher_key,
                'teacher_name': offering.teacher.get_full_name() or offering.teacher.username,
                'offerings': []
            }
        teachers[teacher_key]['offerings'].append(offering)
    
    # Calculate metrics for each teacher
    for teacher_id, teacher_info in teachers.items():
        offerings = teacher_info['offerings']
        
        # Get all rating responses for this teacher
        responses = FeedbackResponse.objects.filter(
            session=session,
            offering__in=offerings,
            question__question_type='RATING'
        )
        
        if responses.exists():
            average_rating = responses.aggregate(avg=Avg('rating'))['avg'] or 0
        else:
            average_rating = 0
        
        teacher_data.append({
            'teacher_id': teacher_id,
            'teacher_name': teacher_info['teacher_name'],
            'average_rating': round(average_rating, 2),
            'total_responses': responses.count(),
            'total_offerings': len(offerings)
        })
    
    return teacher_data


def get_session_class_data(session, user):
    """Get class-wise data for a session"""
    
    class_data = []
    
    # Get classes with their offerings
    offerings = SessionOffering.objects.filter(session=session)
    if user.role == 'teacher':
        offerings = offerings.filter(teacher=user)
    
    classes = {}
    for offering in offerings:
        class_key = f"{offering.base_offering.branch.code}-Sem{offering.base_offering.semester.number}"
        if class_key not in classes:
            classes[class_key] = {
                'class_name': class_key,
                'branch': offering.base_offering.branch.name,
                'semester': offering.base_offering.semester.number,
                'offerings': []
            }
        classes[class_key]['offerings'].append(offering)
    
    # Calculate metrics for each class
    for class_key, class_info in classes.items():
        offerings = class_info['offerings']
        
        # Get all rating responses for this class
        responses = FeedbackResponse.objects.filter(
            session=session,
            offering__in=offerings,
            question__question_type='RATING'
        )
        
        if responses.exists():
            average_rating = responses.aggregate(avg=Avg('rating'))['avg'] or 0
        else:
            average_rating = 0
        
        class_data.append({
            'class_name': class_key,
            'branch': class_info['branch'],
            'semester': class_info['semester'],
            'average_rating': round(average_rating, 2),
            'total_responses': responses.count(),
            'total_offerings': len(offerings)
        })
    
    return class_data


def calculate_improvements(current_data, previous_data):
    """Calculate improvements between current and previous data"""
    
    return {
        'overall_rating_improvement': calculate_rating_improvement(
            current_data['average_rating'], 
            previous_data['average_rating']
        ),
        'total_responses_change': current_data['total_responses'] - previous_data['total_responses'],
        'completion_rate_change': current_data['completion_rate'] - previous_data['completion_rate'],
        'category_improvements': {
            category: calculate_rating_improvement(
                current_data['category_averages'].get(category, 0),
                previous_data['category_averages'].get(category, 0)
            )
            for category in current_data['category_averages']
        }
    }


def calculate_rating_improvement(current, previous):
    """Calculate rating improvement between two values"""
    if previous == 0:
        return None
    return round(current - previous, 2)


def generate_trend_text(improvements):
    """Generate human-readable trend analysis"""
    
    rating_improvement = improvements['overall_rating_improvement']
    
    if rating_improvement is None:
        return "No previous data available for comparison"
    elif rating_improvement > 0.5:
        return f"Significant improvement (+{rating_improvement}) in overall ratings"
    elif rating_improvement > 0:
        return f"Slight improvement (+{rating_improvement}) in overall ratings"
    elif rating_improvement < -0.5:
        return f"Significant decline ({rating_improvement}) in overall ratings"
    elif rating_improvement < 0:
        return f"Slight decline ({rating_improvement}) in overall ratings"
    else:
        return "Performance remained stable compared to previous session"
