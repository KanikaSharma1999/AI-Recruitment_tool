"""
Trigger /admin/rerank-all endpoint directly.
Run from backend directory: python scratch/trigger_rerank.py
"""
import requests
import sys
import os

BASE_URL = "http://localhost:8000"

# ── 1. Login ─────────────────────────────────────────────────────────────────
print("Logging in...")
login_resp = requests.post(
    f"{BASE_URL}/token",
    data={"username": "sandhyagowda506@gmail.com", "password": "admin123"},
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    timeout=15,
)

if login_resp.status_code != 200:
    # Try alternate admin credentials
    login_resp = requests.post(
        f"{BASE_URL}/token",
        data={"username": "admin", "password": "admin"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )

print(f"Login status: {login_resp.status_code}")
if login_resp.status_code != 200:
    print("Login failed:", login_resp.text[:300])
    sys.exit(1)

token = login_resp.json().get("access_token")
print(f"Token obtained: {token[:20]}...")

# ── 2. Trigger rerank-all ────────────────────────────────────────────────────
print("\nTriggering /admin/rerank-all ...")
rerank_resp = requests.post(
    f"{BASE_URL}/admin/rerank-all",
    headers={"Authorization": f"Bearer {token}"},
    timeout=300,  # 5 min timeout for 39 candidates
)

print(f"Rerank status: {rerank_resp.status_code}")
print("Response:", rerank_resp.text[:500])
