from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, NotFound
from django.db.models import Avg, Count, Q, F, FloatField, Sum, Max, Min
from django.db.models.functions import Cast, Coalesce
from django.db.models import Case, When, Value, IntegerField
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import datetime

from .models import (
    FeedbackSession, FeedbackResponse, SessionOffering, FeedbackSubmission,
    User, Question, SubjectOffering, Branch, Semester
)
from .serializers import (
    FeedbackSessionSerializer, SessionOfferingSerializer, UserSerializer
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def comprehensive_analytics(request):
    """
    Main analytics endpoint that provides all three types of analysis:
    1. Quantitative Analysis
    2. Cumulative Analysis  
    3. Comparative Study
    """
    user = request.user
    session_id = request.query_params.get('session_id')
    analysis_type = request.query_params.get('type', 'all')  # quantitative, cumulative, comparative, all
    
    if not session_id:
        # Get current active session if not specified
        current_session = FeedbackSession.objects.filter(
            is_active=True,
            is_closed=False
        ).order_by('-created_at').first()
        
        if not current_session:
            return Response({'error': 'No active session found'}, status=404)
        session_id = current_session.id
    
    # Get the target session
    session = get_object_or_404(FeedbackSession, pk=session_id)
    
    # Role-based filtering
    if user.role == 'teacher':
        # Teachers can only see their own data
        offerings_filter = Q(teacher=user)
    elif user.role in ['hod', 'admin']:
        # HOD/Admin can see all data
        offerings_filter = Q()
    else:
        raise PermissionDenied("Access denied")
    
    results = {}
    
    if analysis_type in ['quantitative', 'all']:
        results['quantitative_analysis'] = generate_quantitative_analysis(session, offerings_filter, user)
    
    if analysis_type in ['cumulative', 'all']:
        results['cumulative_analysis'] = generate_cumulative_analysis(session, offerings_filter, user)
    
    if analysis_type in ['comparative', 'all']:
        results['comparative_study'] = generate_comparative_study(session, offerings_filter, user)
    
    return Response({
        'session': FeedbackSessionSerializer(session).data,
        'analysis_type': analysis_type,
        'generated_at': timezone.now().isoformat(),
        'user_role': user.role,
        **results
    })


def generate_quantitative_analysis(session, offerings_filter, user):
    """
    Quantitative Analysis: Calculate average ratings per subject, teacher, and question
    SQL Equivalent:
    SELECT subject_id, teacher_id, question_id, AVG(rating) as avg_rating, COUNT(*) as total_responses
    FROM feedback_response fr
    JOIN session_offering so ON fr.offering_id = so.id
    WHERE fr.session_id = session_id AND fr.question_type = 'RATING'
    GROUP BY subject_id, teacher_id, question_id
    """
    
    # Base queryset for rating responses
    rating_responses = FeedbackResponse.objects.filter(
        session=session,
        question__question_type='RATING'
    ).filter(
        Q(offering__teacher=user) if user.role == 'teacher' else Q()
    )
    
    # 1. Subject-wise quantitative analysis
    subject_analysis = []
    subjects_data = {}
    
    # Get all offerings for this session
    offerings = SessionOffering.objects.filter(session=session).filter(offerings_filter)
    
    for offering in offerings:
        subject_key = offering.base_offering.subject.id
        if subject_key not in subjects_data:
            subjects_data[subject_key] = {
                'subject_id': subject_key,
                'subject_name': offering.base_offering.subject.name,
                'subject_code': offering.base_offering.subject.code,
                'offerings': []
            }
        subjects_data[subject_key]['offerings'].append(offering)
    
    # Calculate metrics for each subject
    for subject_id, subject_info in subjects_data.items():
        offerings = subject_info['offerings']
        
        # Get rating responses for this subject
        subject_responses = rating_responses.filter(offering__in=offerings)
        
        if subject_responses.exists():
            avg_rating = subject_responses.aggregate(avg=Avg('rating'))['avg'] or 0
            total_responses = subject_responses.count()
            
            # Question-wise breakdown for this subject
            question_breakdown = []
            for question in Question.objects.filter(question_type='RATING'):
                question_responses = subject_responses.filter(question=question)
                if question_responses.exists():
                    question_avg = question_responses.aggregate(avg=Avg('rating'))['avg'] or 0
                    question_breakdown.append({
                        'question_id': question.id,
                        'question_text': question.text,
                        'category': question.category,
                        'average_rating': round(question_avg, 2),
                        'response_count': question_responses.count()
                    })
            
            subject_analysis.append({
                'subject_id': subject_id,
                'subject_name': subject_info['subject_name'],
                'subject_code': subject_info['subject_code'],
                'average_rating': round(avg_rating, 2),
                'total_responses': total_responses,
                'total_offerings': len(offerings),
                'question_breakdown': question_breakdown
            })
    
    # 2. Teacher-wise quantitative analysis
    teacher_analysis = []
    teachers_data = {}
    
    for offering in offerings:
        teacher_key = offering.teacher.id
        if teacher_key not in teachers_data:
            teachers_data[teacher_key] = {
                'teacher_id': teacher_key,
                'teacher_name': offering.teacher.get_full_name() or offering.teacher.username,
                'offerings': []
            }
        teachers_data[teacher_key]['offerings'].append(offering)
    
    # Calculate metrics for each teacher
    for teacher_id, teacher_info in teachers_data.items():
        offerings = teacher_info['offerings']
        
        # Get rating responses for this teacher
        teacher_responses = rating_responses.filter(offering__in=offerings)
        
        if teacher_responses.exists():
            avg_rating = teacher_responses.aggregate(avg=Avg('rating'))['avg'] or 0
            total_responses = teacher_responses.count()
            
            # Subject-wise breakdown for this teacher
            subject_breakdown = []
            for offering in offerings:
                subject_responses = teacher_responses.filter(offering=offering)
                if subject_responses.exists():
                    subject_avg = subject_responses.aggregate(avg=Avg('rating'))['avg'] or 0
                    subject_breakdown.append({
                        'subject_id': offering.base_offering.subject.id,
                        'subject_name': offering.base_offering.subject.name,
                        'subject_code': offering.base_offering.subject.code,
                        'average_rating': round(subject_avg, 2),
                        'response_count': subject_responses.count()
                    })
            
            teacher_analysis.append({
                'teacher_id': teacher_id,
                'teacher_name': teacher_info['teacher_name'],
                'average_rating': round(avg_rating, 2),
                'total_responses': total_responses,
                'total_offerings': len(offerings),
                'subject_breakdown': subject_breakdown
            })
    
    # 3. Question-wise quantitative analysis
    question_analysis = []
    for question in Question.objects.filter(question_type='RATING'):
        question_responses = rating_responses.filter(question=question)
        
        if question_responses.exists():
            avg_rating = question_responses.aggregate(avg=Avg('rating'))['avg'] or 0
            
            # Category-wise breakdown
            category_stats = {}
            for offering in offerings:
                category_responses = question_responses.filter(offering=offering)
                category = offering.base_offering.subject.category or 'GENERAL'
                
                if category not in category_stats:
                    category_stats[category] = {'responses': 0, 'total_rating': 0}
                
                category_responses_data = category_responses.aggregate(
                    count=Count('rating'),
                    total=Sum('rating')
                )
                category_stats[category]['responses'] += category_responses_data['count']
                category_stats[category]['total_rating'] += category_responses_data['total'] or 0
            
            category_breakdown = []
            for category, stats in category_stats.items():
                if stats['responses'] > 0:
                    category_breakdown.append({
                        'category': category,
                        'average_rating': round(stats['total_rating'] / stats['responses'], 2),
                        'response_count': stats['responses']
                    })
            
            question_analysis.append({
                'question_id': question.id,
                'question_text': question.text,
                'category': question.category,
                'weight': question.weight,
                'average_rating': round(avg_rating, 2),
                'total_responses': question_responses.count(),
                'category_breakdown': category_breakdown
            })
    
    return {
        'subject_analysis': subject_analysis,
        'teacher_analysis': teacher_analysis,
        'question_analysis': question_analysis,
        'summary': {
            'total_subjects': len(subject_analysis),
            'total_teachers': len(teacher_analysis),
            'total_questions': len(question_analysis),
            'overall_average': round(
                sum(s['average_rating'] for s in subject_analysis) / len(subject_analysis) if subject_analysis else 0, 2
            )
        }
    }


def generate_cumulative_analysis(session, offerings_filter, user):
    """
    Cumulative Analysis: Calculate overall performance of class/department
    SQL Equivalent:
    SELECT 
        branch_id, semester_id,
        AVG(rating) as avg_rating,
        COUNT(*) as total_responses,
        MAX(rating) as max_rating,
        MIN(rating) as min_rating,
        SUM(CASE WHEN rating >= 4 THEN 1 ELSE 0 END) as positive_responses,
        SUM(CASE WHEN rating <= 2 THEN 1 ELSE 0 END) as negative_responses
    FROM feedback_response fr
    JOIN session_offering so ON fr.offering_id = so.id
    JOIN subject_offering bo ON so.base_offering_id = bo.id
    WHERE fr.session_id = session_id AND fr.question_type = 'RATING'
    GROUP BY branch_id, semester_id
    """
    
    # Base queryset for rating responses
    rating_responses = FeedbackResponse.objects.filter(
        session=session,
        question__question_type='RATING'
    ).filter(
        Q(offering__teacher=user) if user.role == 'teacher' else Q()
    )
    
    # Get all offerings for this session
    offerings = SessionOffering.objects.filter(session=session).filter(offerings_filter)
    
    # 1. Department/Branch-wise cumulative analysis
    branch_analysis = []
    branches_data = {}
    
    for offering in offerings:
        branch_key = offering.base_offering.branch.id
        if branch_key not in branches_data:
            branches_data[branch_key] = {
                'branch_id': branch_key,
                'branch_name': offering.base_offering.branch.name,
                'branch_code': offering.base_offering.branch.code,
                'offerings': []
            }
        branches_data[branch_key]['offerings'].append(offering)
    
    # Calculate metrics for each branch
    for branch_id, branch_info in branches_data.items():
        offerings = branch_info['offerings']
        
        # Get rating responses for this branch
        branch_responses = rating_responses.filter(offering__in=offerings)
        
        if branch_responses.exists():
            # Calculate comprehensive metrics
            metrics = branch_responses.aggregate(
                avg_rating=Avg('rating'),
                total_responses=Count('rating'),
                max_rating=Max('rating'),
                min_rating=Min('rating'),
                positive_responses=Count(Case(When(rating__gte=4, then=1))),
                negative_responses=Count(Case(When(rating__lte=2, then=1)))
            )
            
            # Semester-wise breakdown within branch
            semester_breakdown = []
            semesters_data = {}
            
            for offering in offerings:
                semester_key = offering.base_offering.semester.id
                if semester_key not in semesters_data:
                    semesters_data[semester_key] = {
                        'semester_id': semester_key,
                        'semester_number': offering.base_offering.semester.number,
                        'offerings': []
                    }
                semesters_data[semester_key]['offerings'].append(offering)
            
            for semester_id, semester_info in semesters_data.items():
                semester_offerings = semester_info['offerings']
                semester_responses = branch_responses.filter(offering__in=semester_offerings)
                
                if semester_responses.exists():
                    semester_metrics = semester_responses.aggregate(
                        avg_rating=Avg('rating'),
                        total_responses=Count('rating')
                    )
                    
                    semester_breakdown.append({
                        'semester_id': semester_id,
                        'semester_number': semester_info['semester_number'],
                        'average_rating': round(semester_metrics['avg_rating'] or 0, 2),
                        'total_responses': semester_metrics['total_responses']
                    })
            
            # Calculate percentages
            total_responses = metrics['total_responses']
            positive_percentage = (metrics['positive_responses'] / total_responses * 100) if total_responses > 0 else 0
            negative_percentage = (metrics['negative_responses'] / total_responses * 100) if total_responses > 0 else 0
            
            branch_analysis.append({
                'branch_id': branch_id,
                'branch_name': branch_info['branch_name'],
                'branch_code': branch_info['branch_code'],
                'average_rating': round(metrics['avg_rating'] or 0, 2),
                'total_responses': metrics['total_responses'],
                'max_rating': metrics['max_rating'],
                'min_rating': metrics['min_rating'],
                'positive_responses': metrics['positive_responses'],
                'negative_responses': metrics['negative_responses'],
                'positive_percentage': round(positive_percentage, 2),
                'negative_percentage': round(negative_percentage, 2),
                'semester_breakdown': semester_breakdown
            })
    
    # 2. Overall department performance summary
    overall_metrics = rating_responses.aggregate(
        avg_rating=Avg('rating'),
        total_responses=Count('rating'),
        max_rating=Max('rating'),
        min_rating=Min('rating'),
        positive_responses=Count(Case(When(rating__gte=4, then=1))),
        negative_responses=Count(Case(When(rating__lte=2, then=1)))
    )
    
    # Category-wise cumulative analysis
    category_analysis = []
    for category in Question.QUESTION_CATEGORIES:
        category_responses = rating_responses.filter(question__category=category[0])
        
        if category_responses.exists():
            category_metrics = category_responses.aggregate(
                avg_rating=Avg('rating'),
                total_responses=Count('rating'),
                positive_responses=Count(Case(When(rating__gte=4, then=1))),
                negative_responses=Count(Case(When(rating__lte=2, then=1)))
            )
            
            total_responses = category_metrics['total_responses']
            positive_percentage = (category_metrics['positive_responses'] / total_responses * 100) if total_responses > 0 else 0
            
            category_analysis.append({
                'category': category[0],
                'category_name': category[1],
                'average_rating': round(category_metrics['avg_rating'] or 0, 2),
                'total_responses': category_metrics['total_responses'],
                'positive_percentage': round(positive_percentage, 2)
            })
    
    return {
        'branch_analysis': branch_analysis,
        'category_analysis': category_analysis,
        'overall_summary': {
            'average_rating': round(overall_metrics['avg_rating'] or 0, 2),
            'total_responses': overall_metrics['total_responses'],
            'max_rating': overall_metrics['max_rating'],
            'min_rating': overall_metrics['min_rating'],
            'positive_responses': overall_metrics['positive_responses'],
            'negative_responses': overall_metrics['negative_responses'],
            'total_branches': len(branch_analysis),
            'total_categories': len(category_analysis)
        }
    }


def generate_comparative_study(session, offerings_filter, user):
    """
    Comparative Study: Compare current session with previous session
    SQL Equivalent:
    WITH current_session AS (
        SELECT subject_id, AVG(rating) as current_avg, COUNT(*) as current_count
        FROM feedback_response fr
        JOIN session_offering so ON fr.offering_id = so.id
        WHERE fr.session_id = current_session_id AND fr.question_type = 'RATING'
        GROUP BY subject_id
    ),
    previous_session AS (
        SELECT subject_id, AVG(rating) as previous_avg, COUNT(*) as previous_count
        FROM feedback_response fr
        JOIN session_offering so ON fr.offering_id = so.id
        WHERE fr.session_id = previous_session_id AND fr.question_type = 'RATING'
        GROUP BY subject_id
    )
    SELECT 
        c.subject_id,
        c.current_avg,
        p.previous_avg,
        (c.current_avg - p.previous_avg) as improvement,
        CASE 
            WHEN c.current_avg > p.previous_avg THEN 'Improved'
            WHEN c.current_avg < p.previous_avg THEN 'Declined'
            ELSE 'No Change'
        END as trend
    FROM current_session c
    LEFT JOIN previous_session p ON c.subject_id = p.subject_id
    """
    
    # Find previous session of same type
    previous_session = FeedbackSession.objects.filter(
        type=session.type,
        year__lt=session.year
    ).order_by('-year').first()
    
    if not previous_session:
        return {
            'error': 'No previous session found for comparison',
            'current_session': FeedbackSessionSerializer(session).data
        }
    
    # Get data for both sessions
    current_data = get_session_comparison_data(session, offerings_filter, user)
    previous_data = get_session_comparison_data(previous_session, offerings_filter, user)
    
    # 1. Subject-wise comparison
    subject_comparison = []
    for current_subject in current_data['subjects']:
        subject_name = current_subject['subject_name']
        previous_subject = next((s for s in previous_data['subjects'] if s['subject_name'] == subject_name), None)
        
        if previous_subject:
            improvement = round(current_subject['average_rating'] - previous_subject['average_rating'], 2)
            response_change = current_subject['total_responses'] - previous_subject['total_responses']
            
            # Determine trend
            if improvement > 0.1:
                trend = 'Improved'
            elif improvement < -0.1:
                trend = 'Declined'
            else:
                trend = 'Stable'
            
            subject_comparison.append({
                'subject_name': subject_name,
                'subject_code': current_subject['subject_code'],
                'current_session': {
                    'average_rating': current_subject['average_rating'],
                    'total_responses': current_subject['total_responses']
                },
                'previous_session': {
                    'average_rating': previous_subject['average_rating'],
                    'total_responses': previous_subject['total_responses']
                },
                'improvement': improvement,
                'response_change': response_change,
                'trend': trend,
                'improvement_percentage': calculate_improvement_percentage(
                    current_subject['average_rating'], 
                    previous_subject['average_rating']
                )
            })
        else:
            # New subject in current session
            subject_comparison.append({
                'subject_name': subject_name,
                'subject_code': current_subject['subject_code'],
                'current_session': {
                    'average_rating': current_subject['average_rating'],
                    'total_responses': current_subject['total_responses']
                },
                'previous_session': None,
                'improvement': None,
                'response_change': None,
                'trend': 'New Subject',
                'improvement_percentage': None
            })
    
    # 2. Teacher-wise comparison
    teacher_comparison = []
    for current_teacher in current_data['teachers']:
        teacher_name = current_teacher['teacher_name']
        previous_teacher = next((t for t in previous_data['teachers'] if t['teacher_name'] == teacher_name), None)
        
        if previous_teacher:
            improvement = round(current_teacher['average_rating'] - previous_teacher['average_rating'], 2)
            response_change = current_teacher['total_responses'] - previous_teacher['total_responses']
            
            if improvement > 0.1:
                trend = 'Improved'
            elif improvement < -0.1:
                trend = 'Declined'
            else:
                trend = 'Stable'
            
            teacher_comparison.append({
                'teacher_name': teacher_name,
                'current_session': {
                    'average_rating': current_teacher['average_rating'],
                    'total_responses': current_teacher['total_responses']
                },
                'previous_session': {
                    'average_rating': previous_teacher['average_rating'],
                    'total_responses': previous_teacher['total_responses']
                },
                'improvement': improvement,
                'response_change': response_change,
                'trend': trend,
                'improvement_percentage': calculate_improvement_percentage(
                    current_teacher['average_rating'], 
                    previous_teacher['average_rating']
                )
            })
        else:
            # New teacher in current session
            teacher_comparison.append({
                'teacher_name': teacher_name,
                'current_session': {
                    'average_rating': current_teacher['average_rating'],
                    'total_responses': current_teacher['total_responses']
                },
                'previous_session': None,
                'improvement': None,
                'response_change': None,
                'trend': 'New Teacher',
                'improvement_percentage': None
            })
    
    # 3. Overall session comparison
    overall_improvement = round(current_data['overall_average'] - previous_data['overall_average'], 2)
    overall_response_change = current_data['total_responses'] - previous_data['total_responses']
    
    if overall_improvement > 0.1:
        overall_trend = 'Improved'
    elif overall_improvement < -0.1:
        overall_trend = 'Declined'
    else:
        overall_trend = 'Stable'
    
    return {
        'current_session': {
            'session': FeedbackSessionSerializer(session).data,
            'overall_average': current_data['overall_average'],
            'total_responses': current_data['total_responses']
        },
        'previous_session': {
            'session': FeedbackSessionSerializer(previous_session).data,
            'overall_average': previous_data['overall_average'],
            'total_responses': previous_data['total_responses']
        },
        'subject_comparison': subject_comparison,
        'teacher_comparison': teacher_comparison,
        'overall_comparison': {
            'improvement': overall_improvement,
            'response_change': overall_response_change,
            'trend': overall_trend,
            'improvement_percentage': calculate_improvement_percentage(
                current_data['overall_average'], 
                previous_data['overall_average']
            )
        },
        'summary': {
            'total_subjects_compared': len([s for s in subject_comparison if s['previous_session']]),
            'total_teachers_compared': len([t for t in teacher_comparison if t['previous_session']]),
            'improved_subjects': len([s for s in subject_comparison if s['trend'] == 'Improved']),
            'declined_subjects': len([s for s in subject_comparison if s['trend'] == 'Declined']),
            'improved_teachers': len([t for t in teacher_comparison if t['trend'] == 'Improved']),
            'declined_teachers': len([t for t in teacher_comparison if t['trend'] == 'Declined'])
        }
    }


def get_session_comparison_data(session, offerings_filter, user):
    """Helper function to get session data for comparison"""
    
    # Base queryset for rating responses
    rating_responses = FeedbackResponse.objects.filter(
        session=session,
        question__question_type='RATING'
    ).filter(
        Q(offering__teacher=user) if user.role == 'teacher' else Q()
    )
    
    # Get offerings for this session
    offerings = SessionOffering.objects.filter(session=session).filter(offerings_filter)
    
    # Subject-wise data
    subjects_data = {}
    for offering in offerings:
        subject_key = offering.base_offering.subject.id
        if subject_key not in subjects_data:
            subjects_data[subject_key] = {
                'subject_id': subject_key,
                'subject_name': offering.base_offering.subject.name,
                'subject_code': offering.base_offering.subject.code,
                'offerings': []
            }
        subjects_data[subject_key]['offerings'].append(offering)
    
    subjects = []
    for subject_id, subject_info in subjects_data.items():
        offerings = subject_info['offerings']
        subject_responses = rating_responses.filter(offering__in=offerings)
        
        if subject_responses.exists():
            avg_rating = subject_responses.aggregate(avg=Avg('rating'))['avg'] or 0
            subjects.append({
                'subject_id': subject_id,
                'subject_name': subject_info['subject_name'],
                'subject_code': subject_info['subject_code'],
                'average_rating': round(avg_rating, 2),
                'total_responses': subject_responses.count()
            })
    
    # Teacher-wise data
    teachers_data = {}
    for offering in offerings:
        teacher_key = offering.teacher.id
        if teacher_key not in teachers_data:
            teachers_data[teacher_key] = {
                'teacher_id': teacher_key,
                'teacher_name': offering.teacher.get_full_name() or offering.teacher.username,
                'offerings': []
            }
        teachers_data[teacher_key]['offerings'].append(offering)
    
    teachers = []
    for teacher_id, teacher_info in teachers_data.items():
        offerings = teacher_info['offerings']
        teacher_responses = rating_responses.filter(offering__in=offerings)
        
        if teacher_responses.exists():
            avg_rating = teacher_responses.aggregate(avg=Avg('rating'))['avg'] or 0
            teachers.append({
                'teacher_id': teacher_id,
                'teacher_name': teacher_info['teacher_name'],
                'average_rating': round(avg_rating, 2),
                'total_responses': teacher_responses.count()
            })
    
    # Overall metrics
    overall_average = rating_responses.aggregate(avg=Avg('rating'))['avg'] or 0
    total_responses = rating_responses.count()
    
    return {
        'subjects': subjects,
        'teachers': teachers,
        'overall_average': round(overall_average, 2),
        'total_responses': total_responses
    }


def calculate_improvement_percentage(current, previous):
    """Calculate improvement percentage between two values"""
    if previous == 0:
        return None
    return round(((current - previous) / previous) * 100, 2)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analytics_dashboard_data(request):
    """
    Simplified endpoint for dashboard widgets and graphs
    Returns data optimized for visualization
    """
    user = request.user
    session_id = request.query_params.get('session_id')
    
    if not session_id:
        current_session = FeedbackSession.objects.filter(
            is_active=True,
            is_closed=False
        ).order_by('-created_at').first()
        if not current_session:
            return Response({'error': 'No active session found'}, status=404)
        session_id = current_session.id
    
    session = get_object_or_404(FeedbackSession, pk=session_id)
    
    # Role-based filtering
    offerings_filter = Q(teacher=user) if user.role == 'teacher' else Q()
    
    # Get comprehensive analytics
    analytics = generate_quantitative_analysis(session, offerings_filter, user)
    cumulative = generate_cumulative_analysis(session, offerings_filter, user)
    
    # Prepare data for graphs
    graph_data = {
        'subject_performance': [
            {
                'name': subject['subject_name'],
                'average': subject['average_rating'],
                'responses': subject['total_responses']
            }
            for subject in analytics['subject_analysis']
        ],
        'teacher_performance': [
            {
                'name': teacher['teacher_name'],
                'average': teacher['average_rating'],
                'responses': teacher['total_responses']
            }
            for teacher in analytics['teacher_analysis']
        ],
        'category_performance': [
            {
                'category': cat['category_name'],
                'average': cat['average_rating'],
                'positive_percentage': cat['positive_percentage']
            }
            for cat in cumulative['category_analysis']
        ],
        'branch_performance': [
            {
                'name': branch['branch_name'],
                'average': branch['average_rating'],
                'responses': branch['total_responses'],
                'positive_percentage': branch['positive_percentage']
            }
            for branch in cumulative['branch_analysis']
        ]
    }
    
    return Response({
        'session': FeedbackSessionSerializer(session).data,
        'summary': {
            'overall_average': cumulative['overall_summary']['average_rating'],
            'total_responses': cumulative['overall_summary']['total_responses'],
            'total_subjects': analytics['summary']['total_subjects'],
            'total_teachers': analytics['summary']['total_teachers']
        },
        'graph_data': graph_data,
        'suitable_for': {
            'hod_dashboard': user.role in ['hod', 'admin'],
            'teacher_reports': user.role in ['teacher', 'hod', 'admin'],
            'graph_visualization': True
        }
    })
