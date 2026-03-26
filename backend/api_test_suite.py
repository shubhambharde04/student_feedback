import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000/api"

class FeedbackTester:
    def __init__(self):
        self.session = requests.Session()
        self.username = None

    def login(self, username, password):
        print(f"\n--- Login Attempt: {username} ---")
        url = f"{BASE_URL}/auth/login/"
        payload = {"username": username, "password": password}
        try:
            response = self.session.post(url, json=payload, timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.username = username
                self.session.headers.update({"Authorization": f"Bearer {data['access']}"})
                print(f"✅ Login successful for {username}")
                return data
            else:
                print(f"❌ Login failed for {username}: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"❌ Connection Error: {str(e)}")
            return None

    def test_endpoint(self, method, endpoint, payload=None, description=""):
        url = f"{BASE_URL}{endpoint}"
        print(f"Testing {description} ({method} {endpoint})...")
        try:
            if method == "GET":
                response = self.session.get(url, timeout=5)
            elif method == "POST":
                response = self.session.post(url, json=payload, timeout=5)
            elif method == "DELETE":
                response = self.session.delete(url, timeout=5)
            
            if response.status_code in [200, 201]:
                print(f"✅ Success: {response.status_code}")
                return response.json()
            else:
                print(f"❌ Blocked/Error: {response.status_code} - {response.text}")
                return response
        except Exception as e:
            print(f"❌ Request Error: {str(e)}")
            return None

def run_suite():
    print("STARTING COMPREHENSIVE API TEST SUITE")
    tester = FeedbackTester()
    
    # 1. HOD TESTS (Power User)
    print("\n--- PHASE 1: HOD OPERATIONS ---")
    if tester.login("test_hod", "TestPass123!"):
        tester.test_endpoint("GET", "/hod/dashboard/", description="HOD Dashboard")
        tester.test_endpoint("GET", "/hod/teachers/", description="HOD Teacher List")
        tester.test_endpoint("GET", "/enrollments/form-data/", description="Enrollment Form Data")
        tester.test_endpoint("GET", "/branches/", description="Academic Branches List")
        tester.test_endpoint("GET", "/semesters/", description="Academic Semesters List")
        tester.test_endpoint("GET", "/offerings/", description="Subject Offerings List")
    
    # 2. STUDENT TESTS (First Login & Academic Data)
    print("\n--- PHASE 2: STUDENT OPERATIONS & SECURITY ---")
    stu_tester = FeedbackTester()
    # Default password is enrollment_no 'TESTSTU001'
    if stu_tester.login("test_student", "TESTSTU001"):
        # Profile SHOULD be allowed (exempt)
        stu_tester.test_endpoint("GET", "/auth/profile/", description="Student Profile (Before PW Change - Allowed)")
        
        # Should be blocked from subjects (Not exempt)
        print("Checking first-login enforcement on /student/subjects/...")
        res = stu_tester.test_endpoint("GET", "/student/subjects/", description="Student Subjects (Before PW Change - Should be 403)")
        
        if res and res.status_code == 403:
            print("SUCCESS: Endpoint blocked as expected.")
        elif res:
            print(f"WARNING: Endpoint returned {res.status_code} instead of 403.")
        
        # Test Password Change
        pw_payload = {
            "old_password": "TESTSTU001",
            "new_password": "NewTestPass123!",
            "confirm_password": "NewTestPass123!"
        }
        stu_tester.test_endpoint("POST", "/auth/change-password/", payload=pw_payload, description="Change Password")
        # Re-login with new password
        print("Re-logging with new password...")
        if stu_tester.login("test_student", "NewTestPass123!"):
            stu_tester.test_endpoint("GET", "/student/subjects/", description="Student Subjects (After PW Change)")
            stu_tester.test_endpoint("GET", "/auth/profile/", description="Student Profile")

    # 3. TEACHER TESTS
    print("\n--- PHASE 3: TEACHER OPERATIONS ---")
    t_tester = FeedbackTester()
    if t_tester.login("test_teacher", "TestPass123!"):
        t_tester.test_endpoint("GET", "/teacher/assignments/", description="Teacher Assignments")
        t_tester.test_endpoint("GET", "/teacher/dashboard/", description="Teacher Dashboard")

    print("\nAPI TEST SUITE COMPLETED")

if __name__ == "__main__":
    run_suite()
