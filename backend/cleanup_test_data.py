
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feedback_system.settings')
django.setup()

from users.models import SubmissionTracker, FeedbackResponse

def cleanup():
    # Only delete feedback from our test student account
    test_username = '2307001'
    trackers = SubmissionTracker.objects.filter(student__username=test_username)
    count = 0
    for t in trackers:
        if t.response_set:
            t.response_set.delete()
            count += 1
    trackers.delete()
    print(f"Removed {count} test feedback responses from student {test_username}.")

    # Also check for any ODD 2024-25 leftovers just in case
    FeedbackResponse.objects.filter(session__name='ODD 2024-25').delete()

if __name__ == "__main__":
    cleanup()
