import pandas as pd
import json
import re

# Load Excel
excel_path = '周报2026-01-09.xlsx'
df = pd.read_excel(excel_path, header=None)

# Function to extract data blocks from Excel
def extract_excel_data(df, target_date_str='0130-0205'):
    """
    Scans the dataframe for service blocks.
    Assumes service name is in a cell, and headers are in the same row or next.
    Then looks for the date row.
    """
    services = {}

    # Iterate through cells to find "peak QPS" or similar headers which indicate a block
    # Or better, look for the date column

    # It seems the structure is:
    # Row N: Service Name | Header | Header ...
    # Row N+1..: Date | Value | ...

    # Let's search for the date string
    for r_idx, row in df.iterrows():
        for c_idx, cell in enumerate(row):
            if str(cell).strip() == target_date_str:
                # Found a row with the target date.
                # The service name should be above this block.
                # Let's search upwards for the header row.

                # Usually headers are 1-2 rows above.
                # Headers: "峰值QPS", "P99", "P999", "请求数"

                # Check row r_idx - 1 or r_idx - 2?
                # In the inspect output:
                # Row 0: odin | 峰值QPS...
                # Row 4: 0130-0205 ...
                # So header is at Row 0 for Row 4. (Offset 4)

                # Let's look for the service name.
                # Service name is typically at column c_idx (if data is to the right) or c_idx-1?
                # In inspect: "odin" is at col 0. "0102-0108" is at col 0.
                # So Service name is at [header_row, c_idx].

                # Let's find the header row.
                # We assume the header row contains "请求数" or "P99".
                header_row_idx = -1
                for k in range(1, 10): # Look back up to 10 rows
                    if r_idx - k < 0: break
                    val = str(df.iloc[r_idx - k, c_idx+1]) # Check next col for "峰值QPS" etc
                    if "QPS" in val or "P99" in val or "tp99" in val:
                        header_row_idx = r_idx - k
                        break

                if header_row_idx != -1:
                    service_name = str(df.iloc[header_row_idx, c_idx]).strip()

                    # Extract values
                    # We need to map columns to metrics.
                    # Let's read the header row to map columns.
                    headers = df.iloc[header_row_idx, c_idx:c_idx+10].tolist() # Grab a few cols

                    # Current row values
                    values = df.iloc[r_idx, c_idx:c_idx+10].tolist()

                    metric_map = {}
                    for i, h in enumerate(headers):
                        h_str = str(h)
                        val = values[i]
                        if "请求" in h_str:
                            metric_map['requests'] = val
                        elif "P99" in h_str and "999" not in h_str: # P99 but not P999
                            metric_map['p99'] = val
                        elif "tp99" in h_str and "999" not in h_str:
                            metric_map['p99'] = val
                        elif "P999" in h_str or "tp999" in h_str:
                            metric_map['p999'] = val
                        elif "QPS" in h_str:
                            metric_map['qps'] = val

                    services[service_name] = metric_map

    return services

excel_data = extract_excel_data(df)
print("Excel Data (0130-0205):")
print(json.dumps(excel_data, indent=2, ensure_ascii=False, default=str))

# Load API Response
# The previous output was saved to a file. I need to read that file.
# The filename is in the previous turn's output.
# I'll just read the content of the file using a hardcoded path if I knew it,
# but I'll use the 'Read' tool in the agent flow.
# Since this is a script, I assume I'll pass the json content or path.
# I'll assume the file is named 'tianxiangtai_response.json' for this script
# and I'll create it in the agent flow before running this.

try:
    with open('tianxiangtai_response.json', 'r') as f:
        api_data_raw = json.load(f)

    # Check structure.
    # Based on preview: {"errMsg":"Success", "body": {"columnList":..., "data": [...]}}

    api_rows = api_data_raw.get('body', {}).get('data', [])
    column_list = api_data_raw.get('body', {}).get('columnList', [])

    # Map column indices to names
    col_map = {item['name']: item['index'] for item in column_list}
    # Note: data items are dicts with keys like "median_sum4", "days5".
    # So we don't strictly need the index map if the keys are named.
    # But let's look at the keys in the preview: "days5", "count_sum10", "profiletype2".
    # The keys seem to be "{name}{index}".

    # Filter for target date
    target_from = "20260130"
    target_to = "20260205"

    matches = []

    for row in api_rows:
        # Find keys that start with from_dt/to_dt or match the pattern
        # The keys are dynamic. Let's find the correct keys.
        from_key = next((k for k in row.keys() if k.startswith("from_dt")), None)
        to_key = next((k for k in row.keys() if k.startswith("to_dt")), None)

        if row.get(from_key) == target_from and row.get(to_key) == target_to:
            # Found matching date range

            # Extract metrics
            profile_key = next((k for k in row.keys() if k.startswith("profiletype")), None)
            req_key = next((k for k in row.keys() if k.startswith("count_sum")), None)

            # P99 and P999 are sums. Need to divide by days?
            # "ninty_nine_sum"
            p99_sum_key = next((k for k in row.keys() if k.startswith("ninty_nine_sum")), None)
            p999_sum_key = next((k for k in row.keys() if k.startswith("nine_nine_nine_sum")), None)
            days_key = next((k for k in row.keys() if k.startswith("days") and k != "days_sum"), None)
            # Note: There are multiple "days" columns in the preview.
            # "days3" (from column index 3, which is 'days'),
            # "days11" (from index 11, which is 'days' aggType sum)
            # Use the simple days count.

            # Let's inspect all keys for safety
            days_val = 7 # Default to 7 if not found, but it should be there
            for k, v in row.items():
                if k.startswith("days") and int(v) > 0:
                    days_val = int(v)
                    break

            profile = row.get(profile_key)
            reqs = int(row.get(req_key, 0))
            p99_sum = float(row.get(p99_sum_key, 0) or 0)
            p999_sum = float(row.get(p999_sum_key, 0) or 0)

            p99_avg = p99_sum / days_val if days_val else 0
            p999_avg = p999_sum / days_val if days_val else 0

            matches.append({
                "profiletype": profile,
                "requests": reqs,
                "p99_calc": p99_avg,
                "p999_calc": p999_avg
            })

    print("\nAPI Matches (0130-0205):")
    # Sort by requests to make visual matching easier
    matches.sort(key=lambda x: x['requests'], reverse=True)
    for m in matches:
        print(f"Profile {m['profiletype']}: Reqs={m['requests']:,}, P99={m['p99_calc']:.2f}, P999={m['p999_calc']:.2f}")

    # Auto-match logic
    print("\n--- Auto-Matching ---")

    mapping = {}

    for svc, metrics in excel_data.items():
        if not metrics.get('requests') or pd.isna(metrics['requests']):
            continue

        excel_req = int(metrics['requests'])
        excel_p99 = float(metrics['p99']) if metrics.get('p99') and not pd.isna(metrics['p99']) else 0

        # Find best match in API data
        # Criteria: Requests should be very close (exact match is ideal, but allow small delta)
        # P99 should be close.

        best_match = None
        min_req_diff = float('inf')

        for api_m in matches:
            diff = abs(api_m['requests'] - excel_req)
            if diff < min_req_diff:
                min_req_diff = diff
                best_match = api_m

        # Determine confidence
        # If diff is < 1% of requests, it's a match
        if best_match and min_req_diff < (excel_req * 0.05): # 5% tolerance
             print(f"MATCH FOUND: {svc} <--> Profile {best_match['profiletype']}")
             print(f"   Excel: Req={excel_req}, P99={excel_p99}")
             print(f"   API:   Req={best_match['requests']}, P99={best_match['p99_calc']:.2f}")
             mapping[svc] = best_match['profiletype']
        else:
             print(f"NO MATCH: {svc} (Req={excel_req}) - Closest is Profile {best_match['profiletype'] if best_match else 'None'} (Diff={min_req_diff})")

    print("\nSUGGESTED MAPPING:")
    print(json.dumps(mapping, indent=2))

except Exception as e:
    print(f"Error processing API data: {e}")

