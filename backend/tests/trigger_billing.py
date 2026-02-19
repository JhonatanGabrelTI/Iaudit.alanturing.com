import httpx
import time

def trigger_billing():
    url = "http://localhost:8000/api/cobranca/billing/run-now"
    print(f"Triggering billing job at {url}...")
    try:
        resp = httpx.post(url, timeout=10)
        print(f"Status Code: {resp.status_code}")
        print(f"Response: {resp.json()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    trigger_billing()
