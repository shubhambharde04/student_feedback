#!/usr/bin/env python
"""
Fix password hashing for all users
"""
import os
import sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feedback_system.settings')
import django
django.setup()

from users.models import User
from django.contrib.auth import authenticate

print("=" * 60)
print("FIXING USER PASSWORDS")
print("=" * 60)

# Get all users
users = User.objects.all()
print(f"Total users: {users.count()}")

fixed_count = 0
for user in users:
    if not user.password.startswith('pbkdf2_') and not user.password.startswith('argon2') and not user.password.startswith('bcrypt$'):
        print(f"\nFixing password for: {user.username} (role: {user.role})")
        
        # Hash the existing plain text password
        user.set_password(user.password)
        user.save()
        fixed_count += 1
    else:
        # Avoid printing for all users to reduce noise
        pass

print(f"\n" + "=" * 60)
print(f"Fixed {fixed_count} user passwords")
print("=" * 60)

# Test authentication for a few users
print("\nTESTING AUTHENTICATION:")
test_users = User.objects.all()[:3]
for user in test_users:
    password = user.enrollment_no if user.role == 'student' else user.username
    auth_user = authenticate(username=user.username, password=password)
    print(f"  {user.username}: {'✅' if auth_user else '❌'}")
