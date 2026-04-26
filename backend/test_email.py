
import os
import django
from django.core.mail import send_mail
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feedback_system.settings')
django.setup()

def test_email():
    print(f"Testing email sending for: {settings.EMAIL_HOST_USER}")
    try:
        send_mail(
            'GPN Feedback System Test',
            'This is a test email from your GPN Feedback System.',
            settings.DEFAULT_FROM_EMAIL,
            [settings.EMAIL_HOST_USER], # send to self
            fail_silently=False,
        )
        print("✅ SUCCESS: Email sent successfully!")
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        print("\nPossible solutions:")
        print("1. Ensure you are using a 16-character 'App Password' from Google (not your regular password).")
        print("2. Check if 2-Step Verification is enabled in your Google Account.")
        print("3. Verify that your EMAIL_USER in .env is correct.")

if __name__ == "__main__":
    test_email()
