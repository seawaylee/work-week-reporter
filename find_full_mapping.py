import json
import pandas as pd
import numpy as np

# 1. Load API Data
with open('tianxiangtai_response.json', 'r') as f:
    content = f.read()
    # Handle the extra data issue if present
    try:
        api_data_raw = json.loads(content)
    except:
        idx = content.rfind('}')
        api_data_raw = json.loads(content[:idx+1])

api_rows = api_data_raw.get('body', {}).get('data', [])

# Organize API data by Profile -> { Date: Requests }
# Dates in API are like "20260102"
api_profiles = {}
for row in api_rows:
    pid = str(row.get('profiletype2') or row.get('profiletype')) # Key might vary based on earlier findings
    # Actually let's look at keys dynamically again to be safe
    pid_key = next((k for k in row.keys() if k.startswith("profiletype")), None)
    pid = str(row[pid_key])

    from_key = next((k for k in row.keys() if k.startswith("from_dt")), None)
    from_dt = str(row[from_key])

    req_key = next((k for k in row.keys() if k.startswith("count_sum")), None)
    reqs = int(row.get(req_key, 0))

    if pid not in api_profiles:
        api_profiles[pid] = {}

    api_profiles[pid][from_dt] = reqs

# 2. Load Excel Data
df = pd.read_excel('周报2026-01-09.xlsx', header=None)

# Define known service locations (approximate based on inspection)
# Service Name is at (Row, Col)
# Data follows below
services = [
    ("odin", 0, 0),
    ("odin-home", 0, 6),
    ("odin-search", 0, 12),
    ("odin-video", 6, 0),
    ("odin-article", 6, 6),
    ("odin-focus", 6, 12),
    ("视频Loki", 12, 0),
    ("视频重点场景Loki", 12, 6),
    ("odin-author", 12, 12),
    ("频道Loki", 18, 0),
    ("话题Loki", 18, 6),
    ("algo-loki", 18, 12)
]

mapping_results = {}

for name, r_head, c_head in services:
    # Extract excel history
    excel_history = {} # DateStr -> Reqs

    # Iterate rows below header
    for r in range(r_head + 1, r_head + 6): # Check next 5 rows
        if r >= len(df): break

        # Date cell
        date_cell = str(df.iloc[r, c_head]).strip()
        # Request cell (Header+4 for Requests?)
        # Headers: Name | QPS | P99 | P999 | Reqs
        # Cols:    c      c+1   c+2   c+3    c+4
        req_val = df.iloc[r, c_head + 4]

        # Parse date to match API format "YYYYMMDD"
        # Excel format "0102-0108" -> "20260102" (Assuming 2026)
        if "-" in date_cell and len(date_cell) >= 9: # "0102-0108"
            parts = date_cell.split('-')
            start_md = parts[0].strip()
            # Assuming 2026
            api_date = f"2026{start_md}"

            try:
                req_num = int(req_val)
                excel_history[api_date] = req_num
            except:
                pass

    # Find matching profile
    best_pid = None
    best_score = float('inf') # Sum of % differences

    for pid, history in api_profiles.items():
        score = 0
        matches = 0

        for date, req in excel_history.items():
            if date in history:
                api_req = history[date]
                diff = abs(api_req - req)
                # Use percentage diff
                if req > 0:
                    pct_diff = diff / req
                    score += pct_diff
                    matches += 1

        if matches > 0 and matches == len(excel_history): # Must match ALL existing points?
            # Or at least most.
            if score < best_score:
                best_score = score
                best_pid = pid

    if best_pid and best_score < 0.05: # < 5% total error
        mapping_results[name] = best_pid
        print(f"Mapped {name} -> {best_pid} (Score: {best_score:.4f})")
    else:
        print(f"Failed to map {name}. Best: {best_pid} (Score: {best_score:.4f})")
        # Debug: show history
        # print(f"  Excel: {excel_history}")

print("\nFinal Mapping:")
print(json.dumps(mapping_results, indent=2))

# Save mapping to file
with open('service_mapping.json', 'w') as f:
    json.dump(mapping_results, f)
