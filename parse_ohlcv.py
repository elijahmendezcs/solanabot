# parse_ohlcv.py
# ------------------
# Load raw OHLCV JSON data, convert timestamps, and save as CSV.
# Usage:
# 1. Copy the array of bars into a file named `ohlcv.json` in the same folder.
# 2. Run: python parse_ohlcv.py

import json
import pandas as pd
import sys


def main(json_path: str):
    # Load raw array from JSON file
    try:
        with open(json_path, 'r') as f:
            raw = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {json_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}")
        sys.exit(1)

    # Create DataFrame and assign column names
    df = pd.DataFrame(raw, columns=["ts_ms", "open", "high", "low", "close", "volume"])

    # Convert timestamp to datetime and set as index
    df["datetime"] = pd.to_datetime(df["ts_ms"], unit="ms")
    df = df.set_index("datetime").drop(columns=["ts_ms"])

    # Output head to console
    print("Parsed DataFrame head:")
    print(df.head())
    print()

    # Save to CSV
    out_csv = "ohlcv_parsed.csv"
    df.to_csv(out_csv)
    print(f"Saved parsed data to {out_csv}")


if __name__ == "__main__":
    # Default input file
    json_file = "ohlcv.json"
    main(json_file)
