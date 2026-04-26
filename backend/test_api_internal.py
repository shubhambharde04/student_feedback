
import requests

def test_report_api():
    url = "http://127.0.0.1:8000/api/hod/teacher/2/report/?session_id=3&bypass_threshold=true"
    # Note: This will likely fail with 403 because of authentication, 
    # but we want to see if the server CRASHES (500) or REJECTS (403).
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 500:
            print("❌ SERVER ERROR (500) - Check logs for traceback")
        else:
            print(f"Response: {response.text[:200]}...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_report_api()
