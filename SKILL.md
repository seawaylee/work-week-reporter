---
name: generate-week-report
description: Use when the user needs to generate the weekly Odin service report using the automated Python script
---

# Generate Week Report

## Overview
This skill automates the generation of the weekly service status report for Odin services by running the `generate_weekly_report.py` script. It fetches data from Tianxiangtai and Grafana, and updates an Excel template.

## When to Use
*   User asks to "generate weekly report" or "update report".
*   It is Tuesday (or report day).
*   Need to fetch latest metrics (QPS, P99, Requests) for Odin services.

## Prerequisites
*   **Python 3** with `pandas`, `openpyxl`, `requests`.
*   **Valid Cookies**: The script reads Tianxiangtai/Grafana cookies from environment variables (`TXT_COOKIE`, `GRAFANA_COOKIE`). If it fails with 401/403, you MUST ask the user to provide new cookies.
*   **Previous Report**: A file named like `周报YYYY-MM-DD.xlsx` must exist as a template.

## Workflow

1.  **Check Environment**
    *   Verify `generate_weekly_report.py` exists.
    *   Verify a previous week's Excel file exists (e.g., `周报2026-01-09.xlsx`).

2.  **Run Script**
    ```bash
    python3 generate_weekly_report.py
    ```

3.  **Verify Output**
    *   Script will output: `Success! Report generated: 周报YYYY-MM-DD.xlsx`
    *   **Check QPS**: Ensure `odin`, `odin-video`, `odin-search` etc. have integer QPS values (not None, not 0).
    *   **Check Requests**: Ensure Request counts are in the correct magnitude (Millions/Billions) and represent **Daily Averages**.

4.  **Troubleshooting**
    *   **"No data" or 0 values**: Usually means Cookies are expired or API signature changed.
    *   **"KeyError" in parsing**: API response structure might have changed. Debug with `curl` or small script.
    *   **Excel permission denied**: User has the file open. Ask them to close it.

## Key Files
*   `generate_weekly_report.py`: Main logic.
*   `service_mapping.json` (optional): If external mapping is used (currently hardcoded in script).

## Common Commands
*   Run report: `python3 generate_weekly_report.py`
*   Open report: `open 周报*.xlsx`
