import json
import pandas as pd

# 1. Load the API response from file
# The previous file had extra data at the end, so we read it carefully
with open('tianxiangtai_response.json', 'r') as f:
    content = f.read()
    # Try to find the JSON end
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        # If multiple JSONs or garbage, try to split
        idx = content.rfind('}')
        if idx != -1:
            try:
                data = json.loads(content[:idx+1])
            except:
                print("Failed to parse JSON")
                exit(1)

# 2. Extract Data for mapping (Week 20260130 - 20260205)
target_rows = []
raw_rows = data.get('body', {}).get('data', [])

# Helper to find value by key prefix
def get_val(row, prefix):
    for k, v in row.items():
        if k.startswith(prefix):
            return v
    return None

for row in raw_rows:
    from_dt = get_val(row, "from_dt")
    if from_dt == "20260130":
        target_rows.append({
            "profiletype": get_val(row, "profiletype"),
            "requests": int(get_val(row, "count_sum") or 0),
            "p99": float(get_val(row, "ninty_nine_sum") or 0) / 7.0, # Approx
            "days": 7
        })

# 3. Load Excel Data (Manual extraction from previous turn's output to save time)
# Excel Request Counts for 0130-0205:
excel_data = {
    "odin": 186443005,
    "odin-home": 29160316,
    "odin-search": 68270746,
    "odin-video": 60484458,
    "odin-article": 183798810,
    "odin-focus": 57007993,
    "odin-author": 36802445
}

# 4. Match
mapping = {}
used_profiles = set()

print("Mapping Analysis:")
for name, req in excel_data.items():
    best_diff = float('inf')
    best_profile = None

    for row in target_rows:
        diff = abs(row['requests'] - req)
        if diff < best_diff:
            best_diff = diff
            best_profile = row['profiletype']

    # Check tolerance (1%)
    if best_diff < (req * 0.01):
        mapping[name] = best_profile
        used_profiles.add(best_profile)
        print(f"{name} -> {best_profile} (Diff: {best_diff})")
    else:
        print(f"WARNING: No match for {name}. Closest: {best_profile} (Diff: {best_diff})")

print("\nFinal Mapping Dict:")
print(json.dumps(mapping, indent=4))

# 5. Check for NEW week data in API
print("\nChecking for new week data (>20260205):")
new_week_rows = []
for row in raw_rows:
    from_dt = get_val(row, "from_dt")
    if from_dt and from_dt > "20260205":
        print(f"Found new data: {from_dt} - {get_val(row, 'to_dt')}")
        new_week_rows.append(row)

if not new_week_rows:
    print("No data found for weeks after 20260205 in the provided dump.")
