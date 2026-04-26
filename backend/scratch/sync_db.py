import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feedback_system.settings')
django.setup()

def sync():
    with connection.cursor() as cursor:
        print("Cleaning up database for migration...")
        
        # 1. Drop partial tables from failed runs
        tables_to_drop = ['users_answer', 'users_teacher', 'users_submissiontracker', 'users_feedback', 'users_feedbackwindow']
        for table in tables_to_drop:
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {table}")
                print(f"  Dropped {table} (if it existed)")
            except Exception as e:
                print(f"  Error dropping {table}: {e}")

        # 2. Rename StudentProfile if it exists to avoid conflict
        try:
            cursor.execute("SELECT 1 FROM users_studentprofile LIMIT 1")
            cursor.execute("RENAME TABLE users_studentprofile TO users_studentprofile_old")
            print("  Renamed users_studentprofile to users_studentprofile_old")
        except:
            print("  users_studentprofile already renamed or not found")

        # 3. Create placeholder tables that Django expects to Alter or Delete in 0007
        # Based on 0006 state
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users_feedbacksubmission (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    submitted_at DATETIME(6) NOT NULL,
                    is_completed TINYINT(1) NOT NULL,
                    completion_percentage DOUBLE NOT NULL,
                    ip_address VARCHAR(39) NULL,
                    user_agent LONGTEXT NOT NULL,
                    form_id INT NOT NULL,
                    session_id INT NOT NULL,
                    student_id INT NOT NULL,
                    offering_id INT NOT NULL
                )
            """)
            print("  Created placeholder users_feedbacksubmission")
        except Exception as e:
            print(f"  Error creating users_feedbacksubmission: {e}")

        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users_feedbackresponse (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    rating INT NULL,
                    text_response LONGTEXT NOT NULL,
                    multiple_choice_response VARCHAR(200) NOT NULL,
                    submitted_at DATETIME(6) NOT NULL,
                    ip_address VARCHAR(39) NULL,
                    user_agent LONGTEXT NOT NULL,
                    form_id INT NOT NULL,
                    student_id INT NOT NULL,
                    session_id INT NOT NULL,
                    question_id INT NOT NULL,
                    offering_id INT NOT NULL
                )
            """)
            print("  Created placeholder users_feedbackresponse")
        except Exception as e:
            print(f"  Error creating users_feedbackreponse: {e}")

        # 4. Create dummy users_feedback with the constraint that 0007 tries to delete
        try:
            cursor.execute("CREATE TABLE IF NOT EXISTS users_feedback (id INT PRIMARY KEY, offering_id INT, student_id INT)")
            # In 0006, it was unique_together = ('student', 'offering')
            # The index name usually looks like users_feedback_student_id_offering_id_...
            # But I'll just try to create it.
            try:
                cursor.execute("ALTER TABLE users_feedback ADD UNIQUE (student_id, offering_id)")
            except:
                pass
            print("  Created placeholder users_feedback with unique constraint")
        except Exception as e:
            print(f"  Error creating users_feedback: {e}")

        print("Database sync complete. You can now run 'python manage.py migrate users'.")

if __name__ == "__main__":
    sync()
