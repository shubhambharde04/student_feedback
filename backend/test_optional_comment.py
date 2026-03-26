import requests
import json

BASE_URL = "http://127.0.0.1:8000/api/"

def test_optional_comment():
    print("--- Testing Optional Comment ---")
    
    # 1. Login
    login_url = f"{BASE_URL}auth/login/"
    payload = {"username": "test_student", "password": "password123"}
    response = requests.post(login_url, json=payload)
    token = response.json().get('access')
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get Subjects
    subjects_url = f"{BASE_URL}student/subjects/"
    subjects = requests.get(subjects_url, headers=headers).json()
    
    if len(subjects) > 0:
        offering_id = subjects[0]['id']
        
        # 3. Submit Feedback WITHOUT comment
        feedback_payload = {
            "offering": offering_id,
            "overall_rating": 4,
            "punctuality_rating": 4,
            "teaching_rating": 4,
            "clarity_rating": 4,
            "interaction_rating": 4,
            "behavior_rating": 4,
            # comment is omitted or empty
        }
        
        submit_url = f"{BASE_URL}feedback/submit/"
        response = requests.post(submit_url, json=feedback_payload, headers=headers)
        
        if response.status_code == 201:
            print("SUCCESS: Feedback submitted without comment!")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"FAILED: Status {response.status_code}, Error: {response.text}")
    else:
        print("SKIP: No subjects found.")

if __name__ == "__main__":
    test_optional_comment()
