import re
from collections import Counter
from .models import FeedbackResponse

# mapping of categories to keywords and formal report statements
OBSERVATION_MAPPING = {
    'teaching_quality': {
        'keywords': ['teaching', 'explanation', 'explained', 'good', 'excellent', 'best', 'great', 'clear', 'well'],
        'positive_statement': "Good teaching methodology observed with clear conceptual explanation.",
        'negative_statement': "Students suggest improvement in teaching methodology and concept clarity."
    },
    'concept_clarity': {
        'keywords': ['concept', 'clarity', 'unclear', 'confusing', 'understand', 'understanding', 'doubt'],
        'positive_statement': "High level of conceptual clarity achieved during lectures.",
        'negative_statement': "Improvement required in explanation of complex concepts for better student understanding."
    },
    'interaction': {
        'keywords': ['interactive', 'engaging', 'interaction', 'boring', 'monotonous', 'sleepy', 'interest', 'interesting'],
        'positive_statement': "Interactive and engaging atmosphere maintained in the classroom.",
        'negative_statement': "Classroom interaction needs enhancement to keep students engaged."
    },
    'behavior': {
        'keywords': ['polite', 'rude', 'comportment', 'behavior', 'helpful', 'arrogant', 'kind', 'friendly'],
        'positive_statement': "Professional and helpful behavior exhibited towards students.",
        'negative_statement': "Professional comportment and student interaction approach needs improvement."
    },
    'punctuality': {
        'keywords': ['late', 'on time', 'punctual', 'regular', 'delay', 'time', 'timing'],
        'positive_statement': "Teacher maintains consistency in punctuality and session timing.",
        'negative_statement': "Strict adherence to the academic timetable and punctuality is required."
    },
    'teaching_aids': {
        'keywords': ['ppt', 'blackboard', 'writing', 'visible', 'audible', 'slides', 'aids', 'diagram'],
        'positive_statement': "Effective use of teaching aids and visual tools observed.",
        'negative_statement': "Better utilization of teaching aids (PPT, diagrams) requested by students."
    }
}

def generate_key_observations(feedback_queryset):
    """
    Analyzes feedback comments and generates formal key observations.
    
    Returns:
        List[str]: A list of 2-4 professional observation statements.
    """
    comments_texts = feedback_queryset.exclude(overall_remark__isnull=True).exclude(overall_remark='').values_list('overall_remark', flat=True)
    
    if not comments_texts:
        return ["No specific observations derived from student comments."]
    
    category_counts = Counter()
    positive_categories = Counter()
    negative_categories = Counter()
    
    for comment_text in comments_texts:
        text = comment_text.lower()
        # Basic sentiment
        sentiment = 'neutral'
        if any(w in text for w in ['excellent', 'good', 'great', 'best', 'clear', 'helpful', 'nice']):
            sentiment = 'positive'
        elif any(w in text for w in ['bad', 'poor', 'worst', 'unclear', 'confusing', 'boring', 'arrogant', 'rude']):
            sentiment = 'negative'
            
        # Clean text for keywords
        clean_text = re.sub(r'[^\w\s]', '', text)
        words = set(clean_text.split())
        
        matched_categories = []
        for category, config in OBSERVATION_MAPPING.items():
            if any(keyword in words for keyword in config['keywords']):
                category_counts[category] += 1
                matched_categories.append(category)
                
                if sentiment == 'positive':
                    positive_categories[category] += 1
                elif sentiment == 'negative':
                    negative_categories[category] += 1
                    
    # Select top observations
    # We prioritize negative observations if they are significant (e.g., more than 3 comments)
    observations = []
    
    # Get top 2 negative issues (if any)
    top_negative = [cat for cat, count in negative_categories.most_common(2) if count >= 1]
    for cat in top_negative:
        observations.append(OBSERVATION_MAPPING[cat]['negative_statement'])
        
    # Get top 2 positive issues
    top_positive = [cat for cat, count in positive_categories.most_common(3) if count >= 1]
    for cat in top_positive:
        stmt = OBSERVATION_MAPPING[cat]['positive_statement']
        if stmt not in observations:
            observations.append(stmt)
            
    # Fallback if no keywords matched
    if not observations:
        # Calculate overall basic sentiment
        pos_count = sum(1 for text in comments_texts if any(w in text.lower() for w in ['excellent', 'good', 'great', 'best', 'clear', 'helpful', 'nice']))
        neg_count = sum(1 for text in comments_texts if any(w in text.lower() for w in ['bad', 'poor', 'worst', 'unclear', 'confusing', 'boring', 'arrogant', 'rude']))
        
        if pos_count > neg_count:
            return ["Overall positive feedback received from students regarding the course."]
        elif neg_count > pos_count:
            return ["Students have expressed areas of concern that require administrative attention."]
        return ["Mixed feedback received; students are generally satisfied with the course delivery."]
        
    return observations[:4] # Return max 4 statements
