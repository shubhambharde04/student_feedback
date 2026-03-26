import os
import re

VIEWS_PATH = r"D:\student_feedback\backend\users\views.py"

def fix_views():
    with open(VIEWS_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    # Safety replacements for student profiles
    replacements = {
        r"request\.user\.branch": r"request.user.student_profile.branch",
        r"request\.user\.semester": r"request.user.student_profile.semester",
        r"user\.branch": r"user.student_profile.branch",
        r"user\.semester": r"user.student_profile.semester",
        r"student\.branch": r"student.student_profile.branch",
        r"student\.semester": r"student.student_profile.semester",
    }

    # Don't replace things that are already student_profile.branch
    for pattern, rep in replacements.items():
        # Negative lookbehind to ensure we don't double replace
        content = re.sub(r"(?<!student_profile\.)" + pattern, rep, content)

    with open(VIEWS_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
        
    print("Patched views.py")

if __name__ == "__main__":
    fix_views()
