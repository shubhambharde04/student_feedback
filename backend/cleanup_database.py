import os
import sys
import django

# Add the current directory to sys.path to ensure 'users' can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feedback_system.settings')
django.setup()

from users.models import FeedbackSubmission, FeedbackResponse, Question

def cleanup():
    # 1. Delete old submissions and responses
    print(f"Deleting {FeedbackSubmission.objects.count()} submissions...")
    FeedbackSubmission.objects.all().delete()
    
    print(f"Deleting {FeedbackResponse.objects.count()} responses...")
    FeedbackResponse.objects.all().delete()

    # 2. Correct Question Categories so the sync/reporting works
    print("Updating question categories...")
    mapping = {
        'Punctuality & Discipline': 'PUNCTUALITY',
        'Domain Knowledge': 'TEACHING',
        'Presentation Skills & Interaction with Students': 'CLARITY',
        'Ability to Resolve Difficulties': 'INTERACTION',
        'Effective use of teaching Aids': 'BEHAVIOR'
    }

    for text, cat in mapping.items():
        q = Question.objects.filter(text=text).first()
        if q:
            q.category = cat
            q.save()
            print(f"  Updated '{text}' -> {cat}")
        else:
            # Maybe it's a partial match or needs creation
            print(f"  Warning: Question with text '{text}' not found.")

    print("Cleanup and setup complete. The database is ready for the current session.")

if __name__ == "__main__":
    cleanup()
