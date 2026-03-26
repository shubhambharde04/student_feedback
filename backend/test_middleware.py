import os
import django
from django.test import RequestFactory
from django.contrib.auth import get_user_model

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feedback_system.settings')
django.setup()

from users.middleware import FirstLoginMiddleware

User = get_user_model()
factory = RequestFactory()
user = User.objects.filter(is_first_login=True).first()

if not user:
    # Create a dummy user if none exists
    user = User.objects.create_user(username='test_mid', password='password', is_first_login=True)

def get_response(request):
    from django.http import HttpResponse
    return HttpResponse("Allowed")

middleware = FirstLoginMiddleware(get_response)

test_paths = [
    ('/api/auth/change-password/', "Allowed expected (Exact match)"),
    ('/api//auth/change-password/', "Allowed expected (Double slash)"),
    ('/admin/', "Allowed expected (Prefix)"),
    ('/admin/users/user/', "Allowed expected (Nested Prefix)"),
    ('/swagger/', "Allowed expected (Prefix)"),
    ('/favicon.ico', "Allowed expected (Prefix)"),
    ('/api/student/subjects/', "Blocked expected (API)"),
    ('/', "Blocked expected (Root)"),
]

print(f"Testing middleware for user: {user.username} (is_first_login={user.is_first_login})")
for path, expectation in test_paths:
    request = factory.get(path)
    request.user = user
    response = middleware(request)
    
    status = response.status_code
    result = "ALLOWED" if status == 200 else f"BLOCKED ({status})"
    print(f"Path: {path:30} | Result: {result:15} | {expectation}")
