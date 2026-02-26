import pandas as pd

# Load Excel
file_path = '周报2026-01-09.xlsx'
try:
    df = pd.read_excel(file_path, header=None)
    print(f"Total rows: {len(df)}")

    # Print the last 20 rows to see what's there
    start_row = max(0, len(df) - 30)
    print(f"\nRows {start_row} to {len(df)}:")
    print(df.iloc[start_row:].to_string())

except Exception as e:
    print(f"Error: {e}")
