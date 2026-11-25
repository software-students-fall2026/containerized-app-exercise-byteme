import argparse
import sys

import requests 

TIMEOUT_SEC = 35

def check_health(base_url):
    """Check that /health says the app, MongoDB and ML client are all good."""
    response = requests.get(f"{base_url}/health", timeout=TIMEOUT_SEC)
    body = response.json()
    assert response.status_code == 200, f"status {response.status_code}: {body}"
    assert body.get("status") == "ok", f"unexpected body: {body}" 
    return body

def check_inventory(base_url):
    """Check that /api/inventory returns the chart data shape."""
    response = requests.get(f"{base_url}/api/inventory", timeout=TIMEOUT_SEC)
    assert response.status_code == 200, f"status {response.status_code}"
    body = response.json()
    for key in ("history", "current", "low_stock"):
        assert key in body, f"missing key: {key}"
    assert {"labels", "datasets"} <= body["history"].keys(), "bad history shape"
    assert {"labels", "data"} <= body["current"].keys(), "bad current shape"
    return f"{len(body['history']['labels'])} history point(s)"

def check_upload(base_url, image_path):
    """Check that /upload accepts an image and returns counts from the ML client."""
    with open(image_path, "rb") as f:
        response = requests.post(
            f"{base_url}/upload",
            files={"image": (image_path, f, "image/jpeg")},
            timeout=TIMEOUT_SEC,
        )
    assert response.status_code == 200, f"status {response.status_code}: {response.text}"
    body = response.json()
    assert isinstance(body.get("counts"), dict), f"no counts in response: {body}"
    return body["counts"]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("base_url", nargs="?", default="http://localhost:5000")
    parser.add_argument("--image", default="sample.jpg")
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")

    checks = [
        ("GET  /health", lambda: check_health(base_url)),
        ("GET  /api/inventory", lambda: check_inventory(base_url)),
        ("POST /upload", lambda: check_upload(base_url, args.image))
    ]

    failures = 0
    for name, check in checks:
        try:
            detail = check()
            print(f"PASS {name} {detail}" )
        except (AssertionError, requests.RequestException, ValueError, OSError) as exc:
            failures = failures + 1
            print(f"FAIL {name} {exc}")

    print(f"\n{len(checks) - failures}/{len(checks)} checks passed")
    if failures:
        return 1
    else:
        return 0

if __name__ == "__main__":
    sys.exit(main())