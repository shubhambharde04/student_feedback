import os
import re

VIEWS_PATH = r"D:\student_feedback\backend\users\views.py"
MODELS_PATH = r"D:\student_feedback\backend\users\models.py"

def fix_views():
    with open(VIEWS_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    # Query level replacements
    content = content.replace("assignments__teacher", "assignment__teacher")
    content = content.replace("assignments__is_active", "assignment__is_active")

    # Instance relation replacements
    content = content.replace(
        "assignment = offering.assignments.filter(is_active=True).first()",
        "assignment = offering.assignment if hasattr(offering, 'assignment') and offering.assignment.is_active else None"
    )

    content = content.replace(
        "for assign in off.assignments.filter(is_active=True)",
        "for assign in ([off.assignment] if hasattr(off, 'assignment') and off.assignment.is_active else [])"
    )

    content = content.replace(
        "if not offering.assignments.filter(teacher=user, is_active=True).exists():",
        "if not (hasattr(offering, 'assignment') and offering.assignment.teacher == user and offering.assignment.is_active):"
    )

    with open(VIEWS_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

def fix_models():
    with open(MODELS_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    content = content.replace(
        "assignment = self.offering.assignments.filter(is_active=True).first()",
        "assignment = self.offering.assignment if hasattr(self.offering, 'assignment') and self.offering.assignment.is_active else None"
    )

    with open(MODELS_PATH, 'w', encoding='utf-8') as f:
        f.write(content)


if __name__ == "__main__":
    fix_views()
    fix_models()
    print("Replacements applied successfully.")
