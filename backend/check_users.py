#!/usr/bin/env python
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feedback_system.settings')
django.setup()

from users.models import User
from django.contrib.auth import authenticate

print(f"Total users: {User.objects.count()}")
print("\nHOD users:")
for user in User.objects.filter(role='hod')[:5]:
    print(f"  {user.username} - {user.get_full_name()}")

print("\nTeacher users:")
for user in User.objects.filter(role='teacher')[:5]:
    print(f"  {user.username} - {user.get_full_name()}")

print("\nStudent users (with enrollment):")
for user in User.objects.filter(role='student')[:5]:
    print(f"  {user.username} - Enrollment: {user.enrollment_no}, Name: {user.get_full_name()}")

# Test authentication with common passwords
print("\nTesting login credentials:")

# Test HOD login
hod_user = User.objects.filter(role='hod').first()
if hod_user:
    print(f"\nTesting HOD login for: {hod_user.username}")
    for password in ['admin123', 'password', '123456', 'admin', hod_user.username]:
        auth_user = authenticate(username=hod_user.username, password=password)
        if auth_user:
            print(f"  ✓ Login successful with password: '{password}'")
            break
    else:
        print(f"  ✗ No valid password found for {hod_user.username}")

# Test Student login
student_user = User.objects.filter(role='student').first()
if student_user:
    print(f"\nTesting Student login for: {student_user.enrollment_no}")
    for password in ['password', '123456', 'student', student_user.enrollment_no]:
        auth_user = authenticate(username=student_user.enrollment_no, password=password)
        if auth_user:
            print(f"  ✓ Login successful with password: '{password}'")
            break
    else:
        print(f"  ✗ No valid password found for {student_user.enrollment_no}")

# Create a test user with known password if needed
if not User.objects.filter(username='testuser').exists():
    test_user = User.objects.create_user(
        username='testuser',
        password='test123',
        role='student',
        enrollment_no='999999',
        first_name='Test',
        last_name='User'
    )
    print(f"\n✓ Created test user: testuser / test123 (enrollment: 999999)")
