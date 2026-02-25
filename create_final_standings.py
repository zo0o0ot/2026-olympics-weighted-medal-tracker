import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from main import normalize_country_name, COUNTRY_NAME_MAP

# --- Configuration ---
SHEET_KEY = '18gTKqgWBv4KuAqCKppB9IZxZja-yhJzufj6oqrg7JXw'
DRAFT_TAB_NAME = 'Draft'
WEIGHTED_TAB_NAME = 'Weighted Totals Graph'
MULTIPLIED_TAB_NAME = 'Multiplied Totals Graph'

def get_google_sheet_client():
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    if not creds_json:
        raise ValueError("GOOGLE_CREDENTIALS environment variable not found.")
    creds_dict = json.loads(creds_json)
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

def create_or_clear_tab(sheet, tab_name):
    try:
        ws = sheet.worksheet(tab_name)
        print(f"Found {tab_name}. Clearing old data...")
        ws.clear()
        return ws
    except gspread.exceptions.WorksheetNotFound:
        print(f"Creating new tab: {tab_name}...")
        return sheet.add_worksheet(title=tab_name, rows="100", cols="10")

def run_consolidation():
    print("Connecting to Google Sheets...")
    client = get_google_sheet_client()
    sheet = client.open_by_key(SHEET_KEY)
    draft_ws = sheet.worksheet(DRAFT_TAB_NAME)
    
    w_ws = create_or_clear_tab(sheet, WEIGHTED_TAB_NAME)
    m_ws = create_or_clear_tab(sheet, MULTIPLIED_TAB_NAME)
        
    print("Fetching data from Draft tab...")
    draft_data = draft_ws.get_all_values()
    
    # Identify player headers (typically row 1, cols A-D)
    players = []
    if len(draft_data) > 0:
        header = draft_data[0]
        for idx in range(4): # Cols A-D
            if idx < len(header) and header[idx].strip():
                players.append(header[idx].strip())
            else:
                players.append(f"Player {idx+1}")
                
    weighted_history = []
    multiplied_history = []
    
    # Iterate through Draft data to find historical "Total" rows
    # The structure looks like this over time (accumulating downward):
    # 57    56    42    7    Weighted Total (3/2/1)
    # 85.1  138.0 45.6  55.5 Multiplied Total
    
    print("Parsing historical Totals data...")
    for row in draft_data:
        # Avoid empty rows
        if not any(row): continue
        
        # We identify a "Totals" block by looking at Column E (index 4)
        if len(row) > 4:
            context = row[4].strip()
            
            # Weighted Row
            if "Weighted" in context or "Total Medals" in context:
                scores = []
                for i in range(len(players)):
                    val = row[i].strip() if i < len(row) else "0"
                    scores.append(val)
                weighted_history.append(scores)
                
            # Multiplied Row
            elif "Multiplied Total" in context:
                scores = []
                for i in range(len(players)):
                    val = row[i].strip() if i < len(row) else "0"
                    scores.append(val)
                multiplied_history.append(scores)
                    
    print(f"Found {len(weighted_history)} Weighted Total snapshots.")
    print(f"Found {len(multiplied_history)} Multiplied Total snapshots.")
    
    # Write to Weighted Totals map
    # Structure: Header (Players), then each row is a point in time
    print(f"Pushing updates to {WEIGHTED_TAB_NAME} tab...")
    w_updates = [players] + weighted_history
    w_ws.update('A1', w_updates)
    w_ws.format('A1:D1', {'textFormat': {'bold': True}})
    
    # Write to Multiplied Totals map
    print(f"Pushing updates to {MULTIPLIED_TAB_NAME} tab...")
    m_updates = [players] + multiplied_history
    m_ws.update('A1', m_updates)
    m_ws.format('A1:D1', {'textFormat': {'bold': True}})
    
    print("Done! View the new tabs on Google Sheets to build your Google Charts!")

if __name__ == "__main__":
    run_consolidation()
