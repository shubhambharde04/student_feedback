"""
Step 2: Check teacher_id FK, then fake the 0007 migration.
"""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feedback_system.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from django.db import connection

def col_exists(cursor, table, column):
    cursor.execute("SHOW COLUMNS FROM `%s` LIKE %%s" % table, [column])
    return cursor.fetchone() is not None

def run():
    with connection.cursor() as c:
        # Check teacher_id on feedbackresponse
        if not col_exists(c, 'users_feedbackresponse', 'teacher_id'):
            print("[ADD] teacher_id to users_feedbackresponse")
            c.execute("ALTER TABLE users_feedbackresponse ADD COLUMN teacher_id BIGINT NULL")
            try:
                c.execute("""
                    ALTER TABLE users_feedbackresponse 
                    ADD CONSTRAINT users_feedbackresponse_teacher_id_fk 
                    FOREIGN KEY (teacher_id) REFERENCES users_user(id)
                """)
                print("[ADD] FK constraint for teacher_id")
            except Exception as e:
                print(f"[WARN] FK already exists or error: {e}")
        else:
            print("[OK] teacher_id exists on users_feedbackresponse")

        # Verify all critical tables
        c.execute("SHOW TABLES LIKE 'users_%%'")
        tables = [r[0] for r in c.fetchall()]
        print("\nCurrent tables:")
        for t in sorted(tables):
            print(f"  {t}")

        # Check feedbackresponse columns
        print("\nusers_feedbackresponse columns:")
        c.execute("DESCRIBE users_feedbackresponse")
        for row in c.fetchall():
            print(f"  {row[0]}: {row[1]}")

        # Check feedbacksubmission columns
        print("\nusers_feedbacksubmission columns:")
        c.execute("DESCRIBE users_feedbacksubmission")
        for row in c.fetchall():
            print(f"  {row[0]}: {row[1]}")

        print("\n[DONE] Ready to fake migration.")

if __name__ == '__main__':
    run()
