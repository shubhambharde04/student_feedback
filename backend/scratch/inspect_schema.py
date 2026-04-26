"""Fix users_submissiontracker schema to match Django model."""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feedback_system.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from django.db import connection

with connection.cursor() as c:
    # Show current schema
    print("=== Current users_submissiontracker schema ===")
    c.execute("DESCRIBE users_submissiontracker")
    for row in c.fetchall():
        print(f"  {row}")

    print("\n=== Current users_answer schema ===")
    c.execute("DESCRIBE users_answer")
    for row in c.fetchall():
        print(f"  {row}")

    print("\n=== Current users_feedbackresponse schema ===")
    c.execute("DESCRIBE users_feedbackresponse")
    for row in c.fetchall():
        print(f"  {row}")
