import pandas as pd

# Load the Excel file
file_path = '周报2026-01-09.xlsx'
try:
    # Read all sheets to see what's inside
    xls = pd.ExcelFile(file_path)
    print(f"Sheet names: {xls.sheet_names}")

    # Read the first sheet
    df = pd.read_excel(file_path, sheet_name=0, header=None)
    print("\nFirst 20 rows of the first sheet:")
    print(df.head(20).to_string())

except Exception as e:
    print(f"Error reading Excel file: {e}")
