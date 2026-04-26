import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feedback_system.settings')
import django
django.setup()

from users.models import User
from django.contrib.auth import authenticate

# Check all HOD users
hods = User.objects.filter(role='hod')
for h in hods:
    print(f"HOD: username='{h.username}' email='{h.email}' active={h.is_active}")

# Try authenticate
user = authenticate(username='@shubham00', password='gpn@2025')
print(f"\nAuth result for @shubham00/gpn@2025: {user}")

# Try with other common passwords
for pwd in ['admin', 'admin123', 'password', '12345678']:
    user = authenticate(username='@shubham00', password=pwd)
    if user:
        print(f"Auth SUCCESS with password: {pwd}")
        break
