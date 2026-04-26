import os
import re

file_path = 'users/views.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Improved manage_teachers_real
manage_teachers_logic = """@api_view(['GET'])
@permission_classes([AllowAny])
def manage_teachers_real(request):
    user = request.user
    teachers = User.objects.filter(role='teacher')
    
    # Optional: Filter by department if HOD has one assigned
    if hasattr(user, 'role') and user.role == 'hod' and getattr(user, 'department', None):
        teachers = teachers.filter(department=user.department)
        
    data = []
    for teacher in teachers:
        data.append({
            'id': teacher.id,
            'full_name': teacher.get_full_name() or teacher.username,
            'username': teacher.username,
            'email': teacher.email,
            'department_name': teacher.department.name if teacher.department else 'N/A'
        })
    return Response(data)"""

content = re.sub(r'@api_view\(\[\'GET\'\]\)\n@permission_classes\(\[IsAuthenticated\]\)\ndef manage_teachers_real\(request\):[\s\S]+?return Response\(data\)', manage_teachers_logic, content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated manage_teachers_real successfully")
