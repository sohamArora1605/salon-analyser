import time
import urllib.request

ENDPOINTS = [
    "http://localhost:8000/api/health/status",
    "http://localhost:8000/api/analytics/overview",
]


def fetch(url):
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return r.status, r.read().decode("utf-8")
    except Exception as e:
        return None, str(e)


if __name__ == '__main__':
    for attempt in range(1, 21):
        all_ok = True
        print(f"Attempt {attempt}...")
        for url in ENDPOINTS:
            status, body = fetch(url)
            if status is None:
                print(f"  {url} -> ERROR: {body}")
                all_ok = False
            else:
                print(f"  {url} -> {status}")
        if all_ok:
            print("All endpoints responded OK.")
            break
        time.sleep(1)
    else:
        print("Endpoints did not become available in time.")
