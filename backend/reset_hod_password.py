#!/usr/bin/env python
"""
Reset HOD password for testing
"""
import os
import sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feedback_system.settings')
import django
django.setup()

from users.models import User
from django.contrib.auth import authenticate

print("=" * 60)
print("RESETTING HOD PASSWORD")
print("=" * 60)

# Get HOD user
try:
    hod = User.objects.get(username='@shubham00')
    print(f"Found HOD: {hod.username}")
    print(f"Current password hash: {hod.password[:30]}...")
    
    # Reset password
    hod.set_password('admin123')
    hod.save()
    
    print(f"\nPassword reset to 'admin123'")
    
    # Test authentication
    auth_user = authenticate(username='@shubham00', password='admin123')
    if auth_user:
        print(f"✅ Authentication successful!")
        print(f"User: {auth_user.username}, Role: {auth_user.role}")
    else:
        print(f"❌ Authentication failed!")
        
except User.DoesNotExist:
    print("❌ HOD user not found!")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 60)
print("HOD password reset complete")
print("=" * 60)
