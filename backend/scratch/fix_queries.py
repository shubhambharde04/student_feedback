import re

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern 1: rating_responses = something_responses.filter(question__question_type='RATING')
    content = re.sub(
        r'(\w+)_responses\.filter\(question__question_type=\'RATING\'\)',
        r'Answer.objects.filter(response_parent__in=\1_responses, question__question_type=\'RATING\')',
        content
    )
    
    # Pattern 2: responses.filter(question__question_type='RATING')
    content = re.sub(
        r'responses\.filter\(question__question_type=\'RATING\'\)',
        r'Answer.objects.filter(response_parent__in=responses, question__question_type=\'RATING\')',
        content
    )
    
    # Pattern 3: FeedbackResponse.objects.filter(..., question__question_type='RATING')
    def replace_fr_to_answer(match):
        kwargs_str = match.group(1)
        new_kwargs = []
        for kwarg in kwargs_str.split(','):
            kwarg = kwarg.strip()
            if not kwarg:
                continue
            if kwarg.startswith('question__'):
                new_kwargs.append(kwarg)
            else:
                new_kwargs.append('response_parent__' + kwarg)
        return 'Answer.objects.filter(' + ', '.join(new_kwargs) + ')'

    content = re.sub(
        r'FeedbackResponse\.objects\.filter\((.*?question__question_type=\'RATING\'.*?)\)',
        replace_fr_to_answer,
        content
    )
    
    # Pattern 4: .filter(question__category=cat_key) on an old FeedbackResponse queryset
    # It might be `so_responses` or `subj_responses`.
    # Let's replace `.filter(question__category` with `Answer.objects.filter(response_parent__in=X, question__category...`
    # if the prefix ends with _responses or is just responses
    content = re.sub(
        r'(\w+responses)\.filter\(question__',
        r'Answer.objects.filter(response_parent__in=\1, question__',
        content
    )

    # Pattern 5: .aggregate(avg=Avg('rating')) on old FeedbackResponse
    content = re.sub(
        r'(\w+responses)\.aggregate\(avg=Avg\(\'rating\'\)\)',
        r'Answer.objects.filter(response_parent__in=\1, question__question_type=\'RATING\').aggregate(avg=Avg(\'rating\'))',
        content
    )

    # Pattern 6: .values('question__text')
    content = re.sub(
        r'(\w+responses)\.values\(\'question__text\'\)',
        r'Answer.objects.filter(response_parent__in=\1, question__question_type=\'RATING\').values(\'question__text\')',
        content
    )

    # Pattern 7: rating_answers = Answer.objects.filter(response_parent__in=all_responses, question__question_type='RATING')
    # Actually if this was already correct, Pattern 1 might mess it up.
    # Let's clean up any Answer.objects.filter(response_parent__in=Answer.objects... )
    content = content.replace('Answer.objects.filter(response_parent__in=Answer.objects', 'ERROR_DOUBLE_ANSWER')

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

fix_file('d:/student_feedback/backend/users/views.py')
fix_file('d:/student_feedback/backend/users/session_views.py')
print("Queries fixed.")
