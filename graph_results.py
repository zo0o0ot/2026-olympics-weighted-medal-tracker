import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import matplotlib.pyplot as plt

# --- Configuration ---
SHEET_KEY = '18gTKqgWBv4KuAqCKppB9IZxZja-yhJzufj6oqrg7JXw'
DRAFT_TAB_NAME = 'Draft'
NEW_TAB_NAME = 'Final Standings Visualized'

def get_google_sheet_client():
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    if not creds_json:
        raise ValueError("GOOGLE_CREDENTIALS environment variable not found.")
    creds_dict = json.loads(creds_json)
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

def main():
    try:
        client = get_google_sheet_client()
        sheet = client.open_by_key(SHEET_KEY)
        ws = sheet.worksheet(DRAFT_TAB_NAME)
        
        # Get all values from the Draft tab
        data = ws.get_all_values()
        
        # Target: rows 10-92 (indices 9-91), Columns A-D (indices 0-3) for players
        # E (index 4) for contextual descriptions
        
        # Let's inspect the data first to determine structure
        players = []
        if len(data) > 9:
            # Assuming row 9 has headers, or maybe row 10 is the first data row
            # Let's print the first few rows of interest
            print("Row 9 (Index 8):", data[8][:5])
            print("Row 10 (Index 9):", data[9][:5])
            print("Row 11 (Index 10):", data[10][:5])
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
