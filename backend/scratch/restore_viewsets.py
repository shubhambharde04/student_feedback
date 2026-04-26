import os
import re

file_path = 'users/views.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Restore old viewsets
content = content.replace('class OLD_BranchViewSet', 'class BranchViewSet')
content = content.replace('class OLD_SemesterViewSet', 'class SemesterViewSet')
content = content.replace('class OLD_SubjectOfferingViewSet', 'class SubjectOfferingViewSet')
content = content.replace('class OLD_SubjectAssignmentViewSet', 'class SubjectAssignmentViewSet')
content = content.replace('class OLD_DepartmentViewSet', 'class DepartmentViewSet')

# Remove the mock definitions
# I'll just look for the block I added
mock_block_regex = r'# --- MOCKS FOR MISSING VIEWS ---[\s\S]+?@api_view\(\[\'GET\'\]\)\n@permission_classes\(\[IsAuthenticated\]\)\ndef manage_teachers_real'
content = re.sub(mock_block_regex, 'def manage_teachers_real', content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Restored original ViewSets and removed mocks")
