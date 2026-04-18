import os
import django
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feedback_system.settings')
django.setup()

from django.test import Client
from users.models import User, Subject, SubjectOffering, Branch, Semester, StudentSemester

def run_tests():
    print("Setting up test data...")
    # Create or get users and models
    hod_user, created = User.objects.get_or_create(
        username='test_hod_enrollment',
        defaults={'role': 'hod', 'email': 'hod@test.com'}
    )
    if created:
        hod_user.set_password('password123')
        hod_user.save()

    student_user, created = User.objects.get_or_create(
        username='test_student_enrollment',
        defaults={'role': 'student', 'email': 'student@test.com', 'enrollment_no': 'ENR12345'}
    )
    if created:
        student_user.set_password('password123')
        student_user.save()

    branch, _ = Branch.objects.get_or_create(name='Test Branch', code='TEST')
    semester, _ = Semester.objects.get_or_create(number=99, defaults={'name': 'Test Semester'})
    subject, _ = Subject.objects.get_or_create(name='Test Subject', code='TS101')
    
    offering, _ = SubjectOffering.objects.get_or_create(
        subject=subject, branch=branch, semester=semester, defaults={'is_active': True}
    )

    # Initialize client and login
    client = Client(SERVER_NAME='localhost')
    from rest_framework.test import APIClient
    api_client = APIClient(SERVER_NAME='localhost')
    api_client.force_authenticate(user=hod_user)

    print("\n--- Testing GET /api/enrollments/ ---")
    response = api_client.get('/api/enrollments/')
    print(f"Status Code: {response.status_code}")
    if response.status_code != 200:
        print(f"Error: {response.data}")
    else:
        print(f"Success! Enrolled count: {len(response.data)}")

    print("\n--- Testing POST /api/enrollments/bulk-enroll/ ---")
    data = {
        'subject': offering.id, # The view supports 'subject' key for the offering ID
        'students': [student_user.id]
    }
    response = api_client.post('/api/enrollments/bulk-enroll/', data, format='json')
    print(f"Status Code: {response.status_code}")
    if response.status_code == 201:
        print(f"Successfully bulk enrolled. Response: {response.data}")
    else:
        print(f"Failed to bulk enroll. Error: {response.data}")

    # Verify student semester was created
    profile = StudentSemester.objects.filter(student=student_user).first()
    if profile:
        print(f"Verified: StudentSemester created with branch={profile.branch.code}, semester={profile.semester.number}")
    else:
        print("Failed: StudentSemester was not created.")

    print("\n--- Testing GET /api/enrollments/ (after enrollment) ---")
    response = api_client.get('/api/enrollments/')
    print(f"Status Code: {response.status_code}")
    enrollments = response.data if response.status_code == 200 else []
    print(f"Enrolled count: {len(enrollments)}")
    enrollment_id = None
    for e in enrollments:
        if e['student'] == student_user.id and e['subject'] == offering.id:
            enrollment_id = e['id']
            print(f"Found our test enrollment in the list: {e}")
            break

    if enrollment_id:
        print(f"\n--- Testing DELETE /api/enrollments/{enrollment_id}/ ---")
        response = api_client.delete(f'/api/enrollments/{enrollment_id}/')
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print(f"Successfully deleted enrollment.")
            profile_exists = StudentSemester.objects.filter(student=student_user).exists()
            print(f"Verified: StudentSemester exists? {profile_exists}")
        else:
            print(f"Failed to delete enrollment. Error: {response.data}")
    else:
        print("\nSkipping DELETE test because enrollment wasn't found in list.")

    print("\nCleaning up test data...")
    hod_user.delete()
    student_user.delete()
    offering.delete()
    subject.delete()
    semester.delete()
    branch.delete()
    print("Cleanup complete. All tests finished.")

if __name__ == '__main__':
    run_tests()
