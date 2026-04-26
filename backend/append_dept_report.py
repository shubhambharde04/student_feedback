import os

code = """
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def hod_department_comprehensive_report(request):
    \"\"\"Class Report (Cumulative) for HOD\"\"\"
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
    total_answers = Answer.objects.filter(feedback__session=session)
    
    for offering in offerings:
        offering_answers = total_answers.filter(feedback__offering=offering)
        total_resp = offering_answers.values('feedback__student').distinct().count()
        
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
    sample_size = total_answers.filter(feedback__offering__in=offerings).values('feedback__student').distinct().count()
    
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
"""

with open("d:/student_feedback/backend/users/session_views.py", "a") as f:
    f.write("\n\n" + code + "\n")
print("Appended successfully")
