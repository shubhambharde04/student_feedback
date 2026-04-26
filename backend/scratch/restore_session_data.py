import os
import sys
import django
import re

# Add the current directory to sys.path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feedback_system.settings')
django.setup()

from users.models import User, Subject, SubjectOffering, SubjectAssignment, SessionOffering, FeedbackSession, Branch, Semester

def restore():
    session = FeedbackSession.objects.filter(is_active=True).first()
    if not session:
        print("No active session found")
        return

    print(f"Restoring data for session: {session.name}")

    # 1. Parse diagnose_output.txt for Teacher -> Subject mapping
    mappings = []
    log_path = 'diagnose_output.txt'
    if os.path.exists(log_path):
        content = ""
        for enc in ['utf-16', 'utf-8', 'latin-1']:
            try:
                with open(log_path, 'r', encoding=enc) as f:
                    content = f.read()
                    if "DATABASE DIAGNOSIS" in content:
                        break
            except Exception:
                continue

        if content:
            section = re.search(r'7\. SUBJECT ASSIGNMENTS[\s\S]+?8\.', content)
            if section:
                lines = section.group(0).split('\n')
                for line in lines:
                    match = re.search(r'teacher=(\w+) -> (\w+) \| (\w+) sem=(\d+)', line)
                    if match:
                        mappings.append({
                            'teacher': match.group(1),
                            'subject_code': match.group(2),
                            'branch_code': match.group(3),
                            'semester': int(match.group(4))
                        })

    print(f"Found {len(mappings)} mappings in diagnostic log")

    # 2. Map mappings to a lookup dict
    teacher_lookup = {}
    for m in mappings:
        # Key: (subject_code, branch_code_mapped, semester_number)
        branch_code = m['branch_code'].replace('101', '')
        key = (m['subject_code'], branch_code, m['semester'])
        teacher_lookup[key] = m['teacher']

    # 3. Process ALL SubjectOfferings
    all_offerings = SubjectOffering.objects.filter(is_active=True)
    print(f"Processing {all_offerings.count()} subject offerings...")

    success_count = 0
    created_count = 0
    for offering in all_offerings:
        try:
            # Check if we have a teacher for this offering
            key = (offering.subject.code, offering.branch.code, offering.semester.number)
            teacher_username = teacher_lookup.get(key)
            teacher = None
            if teacher_username:
                try:
                    teacher = User.objects.get(username=teacher_username)
                except User.DoesNotExist:
                    print(f"  Warning: Teacher {teacher_username} not found in DB")

            # Create/Update SessionOffering
            so, created = SessionOffering.objects.update_or_create(
                session=session,
                base_offering=offering,
                defaults={'teacher': teacher, 'is_active': True}
            )
            
            if created:
                created_count += 1
            
            if teacher:
                # Sync to SubjectAssignment for legacy support
                SubjectAssignment.objects.update_or_create(
                    offering=offering,
                    defaults={'teacher': teacher}
                )
                success_count += 1

            # print(f"  Processed {offering.subject.code} ({offering.branch.code} Sem {offering.semester.number}) -> Teacher: {teacher.username if teacher else 'None'}")
        except Exception as e:
            print(f"  Error processing {offering.id}: {e}")

    print(f"Restoration complete.")
    print(f"  SessionOfferings created: {created_count}")
    print(f"  Teachers assigned: {success_count}")
    print(f"  Total SessionOfferings now: {SessionOffering.objects.filter(session=session).count()}")

if __name__ == "__main__":
    restore()
