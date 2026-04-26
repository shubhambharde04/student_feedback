import requests
import sys

BASE_URL = "http://127.0.0.1:8000/api/"

def test_api(name, path, method="GET", data=None, token=None):
    url = f"{BASE_URL}{path}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    print(f"Testing {name} [{method}] {url}...", end=" ")
    try:
        if method == "GET":
            resp = requests.get(url, headers=headers)
        elif method == "POST":
            resp = requests.post(url, headers=headers, json=data)
        
        if resp.status_code in [200, 201]:
            print(" SUCCESS")
            return resp.json()
        else:
            print(f" FAILED ({resp.status_code})")
            print(f"   Response: {resp.text[:200]}")
            return None
    except Exception as e:
        print(f" ERROR: {str(e)}")
        return None

def run_tests():
    # 1. Login
    login_data = {"username": "2307001", "password": "2307001"} # Real Student with Profile
    login_resp = test_api("Login (Student)", "auth/login/", "POST", login_data)
    if not login_resp: return
    
    student_token = login_resp.get("access")
    
    # 2. Student APIs
    test_api("Student Subjects", "student/subjects/", "GET", token=student_token)
    test_api("Student Dashboard", "student/dashboard/", "GET", token=student_token)
    test_api("Active Feedback Form", "feedback/active-form/", "GET", token=student_token)
    
    # 3. Teacher APIs
    teacher_login = {"username": "test_teacher", "password": "password"} # Teacher
    teacher_resp = test_api("Login (Teacher)", "auth/login/", "POST", teacher_login)
    if teacher_resp:
        teacher_token = teacher_resp.get("access")
        test_api("Teacher Dashboard", "teacher/dashboard/", "GET", token=teacher_token)
        test_api("Teacher Performance", "teacher/performance/", "GET", token=teacher_token)
        test_api("Performance Charts", "teacher/performance-charts/", "GET", token=teacher_token)

    # 4. HOD APIs
    hod_login = {"username": "test_hod", "password": "password"}
    hod_resp = test_api("Login (HOD/Admin)", "auth/login/", "POST", hod_login)
    if hod_resp:
        hod_token = hod_resp.get("access")
        test_api("HOD Dashboard", "hod/dashboard/", "GET", token=hod_token)
        test_api("HOD Analytics", "hod/analytics/", "GET", token=hod_token)
        test_api("HOD Statistics", "hod/statistics/", "GET", token=hod_token)
        test_api("Teacher Management", "users/teachers/", "GET", token=hod_token)

if __name__ == "__main__":
    run_tests()
