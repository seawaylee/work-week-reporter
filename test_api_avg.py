import requests
import json
import os

TXT_URL = os.getenv("TXT_URL", "")
TXT_HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Cookie': os.getenv("TXT_COOKIE", ""),
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36'
}

# Original Body (SUM)
# TXT_BODY = '...%22column%22%3A%22count_sum%22%2C%22aggType%22%3A%22sum%22...'

# New Body (Try AVG)
# Replacing "aggType":"sum" with "aggType":"avg" for the "count_sum" column
# Decode -> Modify -> Encode is safer, but hacky replace works if string is exact
# Original string part: %22column%22%3A%22count_sum%22%2C%22aggType%22%3A%22sum%22
# Target string part:   %22column%22%3A%22count_sum%22%2C%22aggType%22%3A%22avg%22

TXT_BODY = 'board_id=20133&dataset_id=20609&cfg=%7B%22rows%22%3A%5B%7B%22columnName%22%3A%22from_dt%22%2C%22link%22%3Afalse%2C%22filterType%22%3A%22eq%22%2C%22values%22%3A%5B%5D%2C%22id%22%3A%225c12004a-2e41-4ca8-b221-703b61ac8337%22%2C%22alias%22%3A%22%E5%BC%80%E5%A7%8B%E6%97%A5%E6%9C%9F%22%7D%2C%7B%22columnName%22%3A%22to_dt%22%2C%22link%22%3Afalse%2C%22filterType%22%3A%22eq%22%2C%22values%22%3A%5B%5D%2C%22id%22%3A%22476cab63-266d-4d6b-b5b4-9655e655affc%22%2C%22alias%22%3A%22%E7%BB%93%E6%9D%9F%E6%97%A5%E6%9C%9F%22%7D%2C%7B%22columnName%22%3A%22profiletype%22%2C%22link%22%3Afalse%2C%22filterType%22%3A%22eq%22%2C%22values%22%3A%5B%5D%2C%22id%22%3A%225ec46a09-f07a-4f93-90d9-d9340a3ffcd8%22%2C%22alias%22%3A%22%E6%9C%8D%E5%8A%A1%E9%83%A8%E7%BD%B2%E7%B1%BB%E5%9E%8B%22%7D%2C%7B%22columnName%22%3A%22days%22%2C%22link%22%3Afalse%2C%22filterType%22%3A%22eq%22%2C%22values%22%3A%5B%5D%2C%22id%22%3A%22e8a15fbc-05d4-444c-b414-44e18f63c7fd%22%2C%22alias%22%3A%22%E5%A4%A9%E6%95%B0%22%7D%5D%2C%22columns%22%3A%5B%5D%2C%22filters%22%3A%5B%7B%22columnName%22%3A%22profiletype%22%2C%22filterType%22%3A%22%3D%22%2C%22values%22%3A%5B%5D%2C%22alias%22%3A%22profiletype%22%7D%5D%2C%22datalength%22%3A2000%2C%22values%22%3A%5B%7B%22column%22%3A%22median_sum%22%2C%22aggType%22%3A%22sum%22%2C%22alias%22%3A%2250%E5%88%86%E4%BD%8D%E5%93%8D%E5%BA%94%E6%97%B6%E9%97%B4%28ms%29%22%7D%2C%7B%22column%22%3A%22days%22%2C%22aggType%22%3A%22sum%22%2C%22alias%22%3A%2250%E5%88%86%E4%BD%8D%E5%93%8D%E5%BA%94%E6%97%B6%E9%97%B4%28ms%29%22%7D%2C%7B%22column%22%3A%22ninty_nine_sum%22%2C%22aggType%22%3A%22sum%22%2C%22alias%22%3A%2299%E5%88%86%E4%BD%8D%E5%93%8D%E5%BA%94%E6%97%B6%E9%97%B4%28ms%29%22%7D%2C%7B%22column%22%3A%22days%22%2C%22aggType%22%3A%22sum%22%2C%22alias%22%3A%2299%E5%88%86%E4%BD%8D%E5%93%8D%E5%BA%94%E6%97%B6%E9%97%B4%28ms%29%22%7D%2C%7B%22column%22%3A%22nine_nine_nine_sum%22%2C%22aggType%22%3A%22sum%22%2C%22alias%22%3A%2299.9%E5%88%86%E4%BD%8D%E5%93%8D%E5%BA%94%E6%97%B6%E9%97%B4%28ms%29%22%7D%2C%7B%22column%22%3A%22days%22%2C%22aggType%22%3A%22sum%22%2C%22alias%22%3A%2299.9%E5%88%86%E4%BD%8D%E5%93%8D%E5%BA%94%E6%97%B6%E9%97%B4%28ms%29%22%7D%2C%7B%22column%22%3A%22count_sum%22%2C%22aggType%22%3A%22avg%22%2C%22alias%22%3A%22%E5%B9%B3%E5%9D%87%E8%AF%B7%E6%B1%82%E6%95%B0%22%7D%2C%7B%22column%22%3A%22days%22%2C%22aggType%22%3A%22sum%22%2C%22alias%22%3A%22%E5%B9%B3%E5%9D%87%E8%AF%B7%E6%B1%82%E6%95%B0%22%7D%5D%7D&reload=true'

if not TXT_URL or not TXT_HEADERS["Cookie"]:
    raise SystemExit("Missing required env vars: TXT_URL, TXT_COOKIE")

print("Sending modified request (aggType: avg)...")
response = requests.post(TXT_URL, headers=TXT_HEADERS, data=TXT_BODY, verify=False)
try:
    data = response.json()
    print("Success?")
    rows = data.get('body', {}).get('data', [])
    for row in rows:
        # Check odin (3202)
        pid_key = next((k for k in row.keys() if k.startswith("profiletype")), None)
        if pid_key and str(row[pid_key]) == "3202": # odin
            print("\nOdin Data:")
            print(json.dumps(row, indent=2))
            break
except:
    print(response.text)
