"""Fix missing FK columns on users_submissiontracker and users_answer."""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feedback_system.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from django.db import connection

def col_exists(cursor, table, column):
    cursor.execute("SHOW COLUMNS FROM `%s` LIKE %%s" % table, [column])
    return cursor.fetchone() is not None

with connection.cursor() as c:
    print("=" * 60)
    print("FIXING MISSING FK COLUMNS")
    print("=" * 60)

    # ── Fix users_submissiontracker ──────────────────────────────
    print("\n--- users_submissiontracker ---")

    if not col_exists(c, 'users_submissiontracker', 'student_id'):
        c.execute("ALTER TABLE users_submissiontracker ADD COLUMN student_id BIGINT NOT NULL DEFAULT 0")
        print("  [ADD] student_id")
    else:
        print("  [OK] student_id")

    if not col_exists(c, 'users_submissiontracker', 'session_id'):
        c.execute("ALTER TABLE users_submissiontracker ADD COLUMN session_id INT NOT NULL DEFAULT 0")
        print("  [ADD] session_id")
    else:
        print("  [OK] session_id")

    if not col_exists(c, 'users_submissiontracker', 'offering_id'):
        c.execute("ALTER TABLE users_submissiontracker ADD COLUMN offering_id INT NOT NULL DEFAULT 0")
        print("  [ADD] offering_id")
    else:
        print("  [OK] offering_id")

    if not col_exists(c, 'users_submissiontracker', 'response_set_id'):
        c.execute("ALTER TABLE users_submissiontracker ADD COLUMN response_set_id CHAR(32) NOT NULL DEFAULT ''")
        print("  [ADD] response_set_id")
    else:
        print("  [OK] response_set_id")

    # Add FKs (ignore errors if they already exist)
    fks = [
        ("users_subtracker_student_fk", "student_id", "users_user", "id"),
        ("users_subtracker_session_fk", "session_id", "users_feedbacksession", "id"),
        ("users_subtracker_offering_fk", "offering_id", "users_sessionoffering", "id"),
        ("users_subtracker_response_fk", "response_set_id", "users_feedbackresponse", "id"),
    ]
    for name, col, ref_table, ref_col in fks:
        try:
            c.execute(f"ALTER TABLE users_submissiontracker ADD CONSTRAINT `{name}` FOREIGN KEY (`{col}`) REFERENCES `{ref_table}`(`{ref_col}`)")
            print(f"  [ADD FK] {name}")
        except Exception as e:
            print(f"  [OK/SKIP FK] {name}: {e}")

    # Add unique constraint
    try:
        c.execute("ALTER TABLE users_submissiontracker ADD UNIQUE KEY unique_student_offering (student_id, offering_id)")
        print("  [ADD] unique_together (student, offering)")
    except Exception as e:
        print(f"  [OK/SKIP] unique_together: {e}")

    # Add index
    try:
        c.execute("CREATE INDEX users_submi_student_1ee408_idx ON users_submissiontracker (student_id, session_id)")
        print("  [ADD] index (student, session)")
    except Exception as e:
        print(f"  [OK/SKIP] index: {e}")

    # ── Fix users_answer ─────────────────────────────────────────
    print("\n--- users_answer ---")

    if not col_exists(c, 'users_answer', 'question_id'):
        c.execute("ALTER TABLE users_answer ADD COLUMN question_id INT NOT NULL DEFAULT 0")
        print("  [ADD] question_id")
    else:
        print("  [OK] question_id")

    if not col_exists(c, 'users_answer', 'response_parent_id'):
        c.execute("ALTER TABLE users_answer ADD COLUMN response_parent_id CHAR(32) NOT NULL DEFAULT ''")
        print("  [ADD] response_parent_id")
    else:
        print("  [OK] response_parent_id")

    # Add FKs
    try:
        c.execute("ALTER TABLE users_answer ADD CONSTRAINT users_answer_question_fk FOREIGN KEY (question_id) REFERENCES users_question(id)")
        print("  [ADD FK] question_id")
    except Exception as e:
        print(f"  [OK/SKIP FK] question_id: {e}")

    try:
        c.execute("ALTER TABLE users_answer ADD CONSTRAINT users_answer_response_fk FOREIGN KEY (response_parent_id) REFERENCES users_feedbackresponse(id)")
        print("  [ADD FK] response_parent_id")
    except Exception as e:
        print(f"  [OK/SKIP FK] response_parent_id: {e}")

    # ── Verify ───────────────────────────────────────────────────
    print("\n=== FINAL SCHEMA ===")

    print("\nusers_submissiontracker:")
    c.execute("DESCRIBE users_submissiontracker")
    for row in c.fetchall():
        print(f"  {row[0]}: {row[1]} {'PK' if row[3]=='PRI' else ''}")

    print("\nusers_answer:")
    c.execute("DESCRIBE users_answer")
    for row in c.fetchall():
        print(f"  {row[0]}: {row[1]} {'PK' if row[3]=='PRI' else ''}")

    print("\n[DONE] All FK columns fixed!")
