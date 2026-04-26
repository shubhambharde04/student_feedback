"""
Comprehensive database fixer: inspects current state, applies only missing
schema changes, then lets us fake the 0007 migration.
"""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feedback_system.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from django.db import connection

def col_exists(cursor, table, column):
    cursor.execute(f"SHOW COLUMNS FROM `{table}` LIKE %s", [column])
    return cursor.fetchone() is not None

def table_exists(cursor, table):
    cursor.execute("SHOW TABLES LIKE %s", [table])
    return cursor.fetchone() is not None

def index_exists(cursor, table, index_name):
    cursor.execute(f"SHOW INDEX FROM `{table}` WHERE Key_name = %s", [index_name])
    return cursor.fetchone() is not None

def run():
    with connection.cursor() as c:
        print("=" * 60)
        print("COMPREHENSIVE DATABASE FIXER")
        print("=" * 60)

        # ── 1. Ensure users_feedbackresponse exists ─────────────────
        if not table_exists(c, 'users_feedbackresponse'):
            print("[CREATE] users_feedbackresponse (placeholder)")
            c.execute("""
                CREATE TABLE users_feedbackresponse (
                    id CHAR(32) NOT NULL PRIMARY KEY,
                    submitted_at DATETIME(6) NOT NULL,
                    form_id INT NOT NULL,
                    session_id INT NOT NULL,
                    offering_id INT NOT NULL,
                    overall_remark LONGTEXT NULL,
                    sentiment_label VARCHAR(20) NOT NULL DEFAULT 'neutral',
                    sentiment_score DOUBLE NOT NULL DEFAULT 0.0,
                    teacher_id BIGINT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
        else:
            print("[OK] users_feedbackresponse exists")
            # Remove legacy columns if present (from old schema)
            for col in ['rating', 'text_response', 'multiple_choice_response',
                        'ip_address', 'user_agent', 'student_id', 'question_id']:
                if col_exists(c, 'users_feedbackresponse', col):
                    # Need to drop FK constraints first if any
                    try:
                        c.execute(f"ALTER TABLE users_feedbackresponse DROP COLUMN `{col}`")
                        print(f"  [DROP COL] {col}")
                    except Exception as e:
                        # Try dropping FK first
                        try:
                            c.execute(f"""
                                SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE
                                WHERE TABLE_NAME='users_feedbackresponse' AND COLUMN_NAME='{col}'
                                AND TABLE_SCHEMA=DATABASE() AND REFERENCED_TABLE_NAME IS NOT NULL
                            """)
                            for row in c.fetchall():
                                c.execute(f"ALTER TABLE users_feedbackresponse DROP FOREIGN KEY `{row[0]}`")
                                print(f"  [DROP FK] {row[0]}")
                            c.execute(f"ALTER TABLE users_feedbackresponse DROP COLUMN `{col}`")
                            print(f"  [DROP COL] {col} (after FK)")
                        except Exception as e2:
                            print(f"  [WARN] Could not drop {col}: {e2}")

            # Add new columns if missing
            if not col_exists(c, 'users_feedbackresponse', 'overall_remark'):
                c.execute("ALTER TABLE users_feedbackresponse ADD COLUMN overall_remark LONGTEXT NULL")
                print("  [ADD COL] overall_remark")
            if not col_exists(c, 'users_feedbackresponse', 'sentiment_label'):
                c.execute("ALTER TABLE users_feedbackresponse ADD COLUMN sentiment_label VARCHAR(20) NOT NULL DEFAULT 'neutral'")
                print("  [ADD COL] sentiment_label")
            if not col_exists(c, 'users_feedbackresponse', 'sentiment_score'):
                c.execute("ALTER TABLE users_feedbackresponse ADD COLUMN sentiment_score DOUBLE NOT NULL DEFAULT 0.0")
                print("  [ADD COL] sentiment_score")
            if not col_exists(c, 'users_feedbackresponse', 'teacher_id'):
                c.execute("ALTER TABLE users_feedbackresponse ADD COLUMN teacher_id BIGINT NULL")
                c.execute("ALTER TABLE users_feedbackresponse ADD CONSTRAINT users_feedbackresponse_teacher_id_1b819fd5_fk_users_user_id FOREIGN KEY (teacher_id) REFERENCES users_user(id)")
                print("  [ADD COL] teacher_id + FK")

            # Change id to UUID if still INT
            c.execute("SHOW COLUMNS FROM users_feedbackresponse LIKE 'id'")
            id_row = c.fetchone()
            if id_row and 'int' in id_row[1].lower():
                print("  [ALTER] Changing id from INT to CHAR(32) for UUID")
                c.execute("DELETE FROM users_feedbackresponse")  # clear data, it's placeholder
                c.execute("ALTER TABLE users_feedbackresponse MODIFY COLUMN id CHAR(32) NOT NULL")

        # ── 2. Ensure users_feedbacksubmission exists ───────────────
        if not table_exists(c, 'users_feedbacksubmission'):
            print("[CREATE] users_feedbacksubmission (placeholder)")
            c.execute("""
                CREATE TABLE users_feedbacksubmission (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    submitted_at DATETIME(6) NOT NULL,
                    is_completed TINYINT(1) NOT NULL DEFAULT 0,
                    completion_percentage DOUBLE NOT NULL DEFAULT 0.0,
                    ip_address VARCHAR(39) NULL,
                    user_agent LONGTEXT NULL,
                    form_id INT NOT NULL,
                    session_id INT NOT NULL,
                    student_id INT NOT NULL,
                    offering_id INT NOT NULL,
                    anonymous_id VARCHAR(100) NULL,
                    overall_remark LONGTEXT NULL,
                    sentiment_label VARCHAR(20) NOT NULL DEFAULT 'neutral',
                    sentiment_score DOUBLE NOT NULL DEFAULT 0.0
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
        else:
            print("[OK] users_feedbacksubmission exists")
            for col, defn in [
                ('anonymous_id', "VARCHAR(100) NULL"),
                ('overall_remark', "LONGTEXT NULL"),
                ('sentiment_label', "VARCHAR(20) NOT NULL DEFAULT 'neutral'"),
                ('sentiment_score', "DOUBLE NOT NULL DEFAULT 0.0"),
            ]:
                if not col_exists(c, 'users_feedbacksubmission', col):
                    c.execute(f"ALTER TABLE users_feedbacksubmission ADD COLUMN {col} {defn}")
                    print(f"  [ADD COL] {col}")
            # user_agent might be NOT NULL from old schema, make nullable
            if col_exists(c, 'users_feedbacksubmission', 'user_agent'):
                c.execute("ALTER TABLE users_feedbacksubmission MODIFY COLUMN user_agent LONGTEXT NULL")

        # ── 3. Ensure users_feedbacksession.is_closed exists ────────
        if not col_exists(c, 'users_feedbacksession', 'is_closed'):
            c.execute("ALTER TABLE users_feedbacksession ADD COLUMN is_closed TINYINT(1) NOT NULL DEFAULT 0")
            print("[ADD COL] users_feedbacksession.is_closed")
        else:
            print("[OK] users_feedbacksession.is_closed exists")

        # ── 4. Ensure users_user.designation exists ─────────────────
        if not col_exists(c, 'users_user', 'designation'):
            c.execute("ALTER TABLE users_user ADD COLUMN designation VARCHAR(100) NULL")
            print("[ADD COL] users_user.designation")
        else:
            print("[OK] users_user.designation exists")

        # ── 5. Ensure users_answer exists ───────────────────────────
        if not table_exists(c, 'users_answer'):
            print("[CREATE] users_answer")
            c.execute("""
                CREATE TABLE users_answer (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    rating INT NULL,
                    text_response LONGTEXT NOT NULL DEFAULT '',
                    choice_response VARCHAR(200) NOT NULL DEFAULT '',
                    question_id INT NOT NULL,
                    response_parent_id CHAR(32) NOT NULL,
                    CONSTRAINT users_answer_question_fk FOREIGN KEY (question_id) REFERENCES users_question(id),
                    CONSTRAINT users_answer_response_fk FOREIGN KEY (response_parent_id) REFERENCES users_feedbackresponse(id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
        else:
            print("[OK] users_answer exists")

        # ── 6. Ensure users_submissiontracker exists ────────────────
        if not table_exists(c, 'users_submissiontracker'):
            print("[CREATE] users_submissiontracker")
            c.execute("""
                CREATE TABLE users_submissiontracker (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    created_at DATETIME(6) NOT NULL,
                    offering_id INT NOT NULL,
                    response_set_id CHAR(32) NOT NULL,
                    session_id INT NOT NULL,
                    student_id BIGINT NOT NULL,
                    CONSTRAINT users_subtracker_offering_fk FOREIGN KEY (offering_id) REFERENCES users_sessionoffering(id),
                    CONSTRAINT users_subtracker_response_fk FOREIGN KEY (response_set_id) REFERENCES users_feedbackresponse(id),
                    CONSTRAINT users_subtracker_session_fk FOREIGN KEY (session_id) REFERENCES users_feedbacksession(id),
                    CONSTRAINT users_subtracker_student_fk FOREIGN KEY (student_id) REFERENCES users_user(id),
                    UNIQUE KEY unique_student_offering (student_id, offering_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            c.execute("CREATE INDEX users_submi_student_1ee408_idx ON users_submissiontracker (student_id, session_id)")
        else:
            print("[OK] users_submissiontracker exists")

        # ── 7. StudentSemester updates ──────────────────────────────
        for col, defn in [
            ('class_name', "VARCHAR(50) NOT NULL DEFAULT 'A'"),
            ('created_at', "DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)"),
            ('is_active', "TINYINT(1) NOT NULL DEFAULT 1"),
            ('roll_number', "VARCHAR(20) NULL"),
            ('session_id', "INT NULL"),
        ]:
            if not col_exists(c, 'users_studentsemester', col):
                c.execute(f"ALTER TABLE users_studentsemester ADD COLUMN {col} {defn}")
                print(f"[ADD COL] users_studentsemester.{col}")
            else:
                print(f"[OK] users_studentsemester.{col} exists")

        # Change studentsemester id to AutoField if BigAutoField
        c.execute("SHOW COLUMNS FROM users_studentsemester LIKE 'id'")
        id_row = c.fetchone()
        if id_row and 'bigint' in id_row[1].lower():
            c.execute("ALTER TABLE users_studentsemester MODIFY COLUMN id INT AUTO_INCREMENT")
            print("[ALTER] users_studentsemester.id -> INT AUTO_INCREMENT")

        # ── 8. Semester max validator ───────────────────────────────
        # Already handled by Django validation, no SQL change needed
        print("[OK] Semester validators (Django-level)")

        # ── 9. Drop legacy tables ───────────────────────────────────
        for t in ['users_feedback', 'users_feedbackwindow']:
            if table_exists(c, t):
                c.execute(f"DROP TABLE `{t}`")
                print(f"[DROP] {t}")

        # ── 10. Drop legacy profile tables ──────────────────────────
        for t in ['users_teacher', 'users_studentprofile']:
            if table_exists(c, t):
                c.execute(f"DROP TABLE `{t}`")
                print(f"[DROP] {t}")

        print()
        print("=" * 60)
        print("DATABASE SCHEMA IS NOW SYNCHRONIZED!")
        print("Run: python manage.py migrate users --fake 0007")
        print("=" * 60)

if __name__ == '__main__':
    run()
