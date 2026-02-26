import requests
import json
import urllib.parse
import os
from datetime import datetime

GRAFANA_URL = os.getenv("GRAFANA_URL", "https://grafana-m0ymy2z9.grafana.tencent-cloud.com/api/datasources/proxy/1/api/v1/query_range")
GRAFANA_HEADERS = {
    'accept': 'application/json, text/plain, */*',
    'content-type': 'application/x-www-form-urlencoded',
    'cookie': os.getenv("GRAFANA_COOKIE", ""),
    'x-grafana-org-id': os.getenv("GRAFANA_ORG_ID", "1")
}

# Date range: 20260206 - 20260209
start_ts = int(datetime(2026, 2, 6).timestamp())
end_ts = int(datetime(2026, 2, 9, 23, 59, 59).timestamp())

app_name = "umab-odin-search-interface"

query = f'max_over_time(sum(rate(http_server_requests_seconds_count{{application="{app_name}"}}[1m]))[24h:])'
encoded_query = urllib.parse.quote(query)
body = f'query={encoded_query}&start={start_ts}&end={end_ts}&step=300'

print(f"Querying for {app_name}...")
print(f"Time range: {start_ts} - {end_ts}")
if not GRAFANA_HEADERS["cookie"]:
    raise SystemExit("Missing required env var: GRAFANA_COOKIE")
try:
    response = requests.post(GRAFANA_URL, headers=GRAFANA_HEADERS, data=body, verify=False)
    data = response.json()

    print("\nStatus:", data.get('status'))
    results = data.get('data', {}).get('result', [])
    if results:
        values = results[0]['values']
        # Print first few and last few values
        print(f"Found {len(values)} data points.")
        print("First 5:", values[:5])
        print("Last 5:", values[-5:])

        max_val = max([float(x[1]) for x in values])
        print(f"\nMax Value found: {max_val}")
    else:
        print("No results found in data.")
        print("Raw Data:", json.dumps(data, indent=2))

except Exception as e:
    print(e)
