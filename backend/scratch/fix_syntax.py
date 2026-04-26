for filepath in ['d:/student_feedback/backend/users/views.py', 'd:/student_feedback/backend/users/session_views.py']:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    content = content.replace("\\'", "'")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
