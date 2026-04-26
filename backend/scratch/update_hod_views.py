import os
import re

file_path = 'users/views.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update _get_performance_label to handle None/0
performance_logic = """def _get_performance_label(avg_rating):
    if not avg_rating: return "N/A"
    if avg_rating >= 4.5: return "Excellent"
    if avg_rating >= 4.0: return "Good"
    if avg_rating >= 3.0: return "Average"
    return "Below Average" """

content = re.sub(r'def _get_performance_label\(avg_rating\):[\s\S]+?return "Below Average"', performance_logic, content)

# 2. Update _get_sentiment_summary to use sentiment_label
sentiment_logic = """def _get_sentiment_summary(feedbacks):
    \"\"\"Return counts of positive, neutral, negative for a FeedbackResponse queryset.\"\"\"
    return {
        'positive': feedbacks.filter(sentiment_label='positive').count(),
        'neutral': feedbacks.filter(sentiment_label='neutral').count(),
        'negative': feedbacks.filter(sentiment_label='negative').count(),
    }"""
content = re.sub(r'def _get_sentiment_summary\(feedbacks\):[\s\S]+?}', sentiment_logic, content)

# 3. Add _calculate_avg_rating utility
if 'def _calculate_avg_rating' not in content:
    content = content.replace('def _get_sentiment_summary', 'def _calculate_avg_rating(responses_queryset):\n    from .models import Answer\n    avg = Answer.objects.filter(\n        response_parent__in=responses_queryset,\n        question__question_type="RATING"\n    ).aggregate(avg=Avg("rating_value"))["avg"]\n    return round(avg, 2) if avg else 0\n\ndef _get_sentiment_summary', 1)

# 4. Rewrite hod_dashboard_overview
hod_dashboard_logic = """@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hod_dashboard_overview(request):
    if request.user.role != 'hod':
        return Response({'error': 'Only HOD allowed'}, status=403)

    total_feedback = FeedbackResponse.objects.count()
    total_teachers = User.objects.filter(role='teacher').count()
    total_subjects = Subject.objects.count()
    
    avg_rating = _calculate_avg_rating(FeedbackResponse.objects.all())

    # Top & lowest teacher
    teachers = User.objects.filter(role='teacher')
    teacher_ratings = []
    for teacher in teachers:
        responses = FeedbackResponse.objects.filter(teacher=teacher)
        t_avg = _calculate_avg_rating(responses)
        if t_avg > 0:
            teacher_ratings.append({
                'id': teacher.id,
                'name': teacher.get_full_name() or teacher.username,
                'email': teacher.email,
                'avg_rating': t_avg,
            })

    teacher_ratings.sort(key=lambda x: x['avg_rating'], reverse=True)

    return Response({
        "total_feedback": total_feedback,
        "total_teachers": total_teachers,
        "total_subjects": total_subjects,
        "average_rating": avg_rating,
        "top_teacher": teacher_ratings[0] if teacher_ratings else None,
        "lowest_teacher": teacher_ratings[-1] if teacher_ratings else None,
    })"""

content = re.sub(r'@api_view\(\[\'GET\'\]\)\n@permission_classes\(\[IsAuthenticated\]\)\ndef hod_dashboard_overview\(request\):[\s\S]+?return Response\({[\s\S]+?}\)', hod_dashboard_logic, content)

# 5. Rewrite hod_teachers
hod_teachers_logic = """@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hod_teachers(request):
    if request.user.role != 'hod':
        return Response({'error': 'Only HOD allowed'}, status=403)

    teachers = User.objects.filter(role='teacher')
    data = []

    for teacher in teachers:
        # Get count of session offerings assigned to this teacher
        subject_count = teacher.session_offerings.count()
        responses = FeedbackResponse.objects.filter(teacher=teacher)
        avg = _calculate_avg_rating(responses)

        data.append({
            'id': teacher.id,
            'name': teacher.get_full_name() or teacher.username,
            'username': teacher.username,
            'email': teacher.email,
            'subject_count': subject_count,
            'feedback_count': responses.count(),
            'avg_rating': avg,
            'performance': _get_performance_label(avg),
        })

    return Response(data)"""

content = re.sub(r'@api_view\(\[\'GET\'\]\)\n@permission_classes\(\[IsAuthenticated\]\)\ndef hod_teachers\(request\):[\s\S]+?return Response\(data\)', hod_teachers_logic, content)

# 6. Fix manage_teachers_real to include department correctly
manage_teachers_logic = """@api_view(['GET'])
@permission_classes([IsAuthenticated])
def manage_teachers_real(request):
    teachers = User.objects.filter(role='teacher')
    data = []
    for teacher in teachers:
        data.append({
            'id': teacher.id,
            'full_name': teacher.get_full_name() or teacher.username,
            'username': teacher.username,
            'email': teacher.email,
            'department_name': teacher.department.name if teacher.department else 'N/A'
        })
    return Response(data)"""

content = re.sub(r'@api_view\(\[\'GET\'\]\)\n@permission_classes\(\[IsAuthenticated\]\)\ndef manage_teachers_real\(request\):[\s\S]+?return Response\(data\)', manage_teachers_logic, content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated views.py successfully")
