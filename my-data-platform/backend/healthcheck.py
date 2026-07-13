import sys
import urllib.request
import json

def check_health():
    try:
        response = urllib.request.urlopen("http://localhost:8000/health", timeout=3)
        if response.getcode() == 200:
            data = json.loads(response.read().decode())
            if data.get("status") == "ok":
                return True
    except Exception as e:
        print(f"Healthcheck failed: {e}")
    return False

if __name__ == "__main__":
    if check_health():
        sys.exit(0)
    else:
        sys.exit(1)
