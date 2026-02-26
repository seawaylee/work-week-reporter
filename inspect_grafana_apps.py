import requests
import json
import os

GRAFANA_URL_BASE = os.getenv("GRAFANA_URL_BASE", "https://grafana-m0ymy2z9.grafana.tencent-cloud.com/api/datasources/proxy/1/api/v1")
GRAFANA_HEADERS = {
    'accept': 'application/json, text/plain, */*',
    'content-type': 'application/x-www-form-urlencoded',
    'cookie': os.getenv("GRAFANA_COOKIE", ""),
    'x-grafana-org-id': os.getenv("GRAFANA_ORG_ID", "1")
}

def get_app_names():
    if not GRAFANA_HEADERS["cookie"]:
        raise SystemExit("Missing required env var: GRAFANA_COOKIE")
    # Try to get values for the label 'application'
    url = f"{GRAFANA_URL_BASE}/label/application/values"
    print(f"Requesting {url}...")
    try:
        response = requests.get(url, headers=GRAFANA_HEADERS, verify=False)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                apps = data.get('data', [])
                print(f"Found {len(apps)} applications.")
                # Filter for things that look like odin
                odin_apps = [a for a in apps if 'odin' in a]
                print("\nPotential Odin Apps found:")
                for app in sorted(odin_apps):
                    print(f"  - {app}")
                return odin_apps
            else:
                print("Error in response body:", data)
        else:
            print(f"HTTP Error {response.status_code}: {response.text}")

            # Fallback: Try query series if label values fails
            print("\nTrying fallback series query...")
            query = 'match[]=http_server_requests_seconds_count{application=~".*odin.*"}'
            url = f"{GRAFANA_URL_BASE}/series?{query}"
            response = requests.get(url, headers=GRAFANA_HEADERS, verify=False)
            if response.status_code == 200:
                print(response.text[:500]) # Print first 500 chars to debug
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    get_app_names()
