import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_system():
    print("--- 1. Testing Login ---")
    login_data = {
        "username": "admin@ats.com",
        "password": "admin123"
    }
    try:
        r = requests.post(f"{BASE_URL}/auth/login", data=login_data)
        if r.status_code == 200:
            print("SUCCESS: Login Successful!")
            token = r.json()["access_token"]
        else:
            print(f"ERROR: Login Failed: {r.status_code} - {r.text}")
            return
    except Exception as e:
        print(f"ERROR: Login Request Error: {e}")
        return

    headers = {"Authorization": f"Bearer {token}"}

    print("\n--- 2. Testing Job Creation ---")
    job_data = {
        "title": "Python Developer",
        "company": "Tech Corp",
        "description": "We need a Python developer with SQL and React skills. 5+ years of experience required.",
    }
    try:
        r = requests.post(f"{BASE_URL}/jobs/create", json=job_data, headers=headers)
        if r.status_code == 200:
            print("SUCCESS: Job Created Successfully!")
        else:
            print(f"ERROR: Job Creation Failed: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"ERROR: Job Creation Request Error: {e}")

    print("\n--- 3. Testing Job List ---")
    try:
        r = requests.get(f"{BASE_URL}/jobs/list", headers=headers)
        if r.status_code == 200:
            print(f"SUCCESS: Job List Retrieved! (Count: {len(r.json())})")
        else:
            print(f"ERROR: Job List Failed: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"ERROR: Job List Request Error: {e}")

    print("\n--- 4. Testing Candidates List ---")
    try:
        r = requests.get(f"{BASE_URL}/candidates/list", headers=headers)
        if r.status_code == 200:
            print(f"SUCCESS: Candidate List Retrieved! (Count: {len(r.json())})")
        else:
            print(f"ERROR: Candidate List Failed: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"ERROR: Candidate List Request Error: {e}")

if __name__ == "__main__":
    test_system()
