import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from main import normalize_country_name, COUNTRY_NAME_MAP

# --- Configuration ---
SHEET_KEY = '18gTKqgWBv4KuAqCKppB9IZxZja-yhJzufj6oqrg7JXw'
DRAFT_TAB_NAME = 'Draft'
RESULTS_TAB_NAME = 'Results'
FINAL_TAB_NAME = 'Final Standings 2026'

def get_google_sheet_client():
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    if not creds_json:
        raise ValueError("GOOGLE_CREDENTIALS environment variable not found.")
    creds_dict = json.loads(creds_json)
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

def run_consolidation():
    print("Connecting to Google Sheets...")
    client = get_google_sheet_client()
    sheet = client.open_by_key(SHEET_KEY)
    
    draft_ws = sheet.worksheet(DRAFT_TAB_NAME)
    res_ws = sheet.worksheet(RESULTS_TAB_NAME)
    
    # Check if final tab exists, if not create it
    try:
        final_ws = sheet.worksheet(FINAL_TAB_NAME)
        print(f"Found existing tab: {FINAL_TAB_NAME}. Clearing old data...")
        final_ws.clear()
    except gspread.exceptions.WorksheetNotFound:
        print(f"Creating new tab: {FINAL_TAB_NAME}...")
        final_ws = sheet.add_worksheet(title=FINAL_TAB_NAME, rows="100", cols="10")
        
    print("Fetching data from Draft and Results tabs...")
    draft_data = draft_ws.get_all_values()
    res_data = res_ws.get_all_values()
    
    # 1. Parse Results Map (To attach accurate total scores to each drafted Country)
    c_stats = {}
    if res_data:
        r_header = res_data[0]
        try:
            idx_c = r_header.index('Country')
            idx_g = r_header.index('Gold')
            idx_s = r_header.index('Silver')
            idx_b = r_header.index('Bronze')
            idx_m = r_header.index('Multiplier') if 'Multiplier' in r_header else -1
            
            for row in res_data[1:]:
                if len(row) <= idx_c: continue
                c = row[idx_c].strip()
                if not c: continue
                
                try:
                    g = int(row[idx_g]) if len(row) > idx_g and row[idx_g] else 0
                    s = int(row[idx_s]) if len(row) > idx_s and row[idx_s] else 0
                    b = int(row[idx_b]) if len(row) > idx_b and row[idx_b] else 0
                    
                    m = 1.0
                    if idx_m != -1 and len(row) > idx_m:
                         val = row[idx_m].replace(',', '.')
                         if val and val.replace('.','',1).isdigit():
                             m = float(val)
                except ValueError:
                    g, s, b, m = 0, 0, 0, 1.0
                    
                w = g*3 + s*2 + b*1
                mult = w * m
                c_stats[c] = {'G': g, 'S': s, 'B': b, 'Weight': w, 'Multiplier': m, 'FinalScore': mult}
        except ValueError as e:
            print(f"Error parsing results headers: {e}")
            return
            
    # 2. Parse Draft Data (Rows 10-92, Cols A-D are teams/players, Col E is Context)
    # The header for the players is usually row 1.
    players = []
    if len(draft_data) > 0:
        header = draft_data[0]
        for idx in range(4): # Columns A-D (0, 1, 2, 3)
            if idx < len(header):
                players.append(header[idx])
            else:
                players.append(f"Player {idx+1}")
                
    flat_data = [] # [Player, Country, Context, G, S, B, Weight, Multiplier, Final Score]
    
    # Start checking rows 10-92 (indices 9 to 91 in Python)
    print("Formatting Draft records...")
    start_row = 9
    end_row = min(91, len(draft_data))
    
    for row_idx in range(start_row, end_row):
        row = draft_data[row_idx]
        context = ""
        # Col E (index 4) contains context
        if len(row) > 4:
            context = row[4].strip()
            
        # Iterate over Player columns (0 to 3)
        for player_idx, player_name in enumerate(players):
            if player_idx < len(row):
                country = row[player_idx].strip()
                if not country: continue
                
                # Setup metric defaults based on logic in main.py
                metrics = None
                
                # Check for direct or fuzzy matches in c_stats
                # (Re-use main.py matching logic)
                s = c_stats.get(country)
                
                if not s:
                     mapped = COUNTRY_NAME_MAP.get(country) 
                     if mapped: s = c_stats.get(mapped)
                     
                     if not s:
                         c_norm = normalize_country_name(country)
                         for k, v in c_stats.items():
                             if normalize_country_name(k) == c_norm:
                                 s = v
                                 break
                         if not s:
                             for k, v in COUNTRY_NAME_MAP.items():
                                 if normalize_country_name(k) == c_norm:
                                     s = c_stats.get(v)
                                     break
                         if not s:
                             for k, v in COUNTRY_NAME_MAP.items():
                                 if v == country or normalize_country_name(v) == c_norm:
                                     s = c_stats.get(k)
                                     if s: break

                if not s and "individual" in country.lower(): s = c_stats.get("AIN") or c_stats.get("Individual Neutral Athletes")
                if not s and country == "AIN": s = c_stats.get("Individual Neutral Athletes")
                
                if s:
                    flat_data.append([
                        player_name, 
                        country, 
                        context, 
                        s['G'], 
                        s['S'], 
                        s['B'], 
                        s['Weight'], 
                        s['Multiplier'], 
                        s['FinalScore']
                    ])
                else:
                    flat_data.append([
                        player_name, 
                        country, 
                        context, 
                        0, 0, 0, 0, 1.0, 0
                    ])
                    
    print(f"Parsed {len(flat_data)} finalized drafted country rows.")
    
    # Write directly to Final Standings tab
    headers = ["Player", "Country", "Draft Context", "Gold", "Silver", "Bronze", "Total Weight", "Multiplier", "Final Score"]
    update_data = [headers] + flat_data
    
    print(f"Pushing updates to {FINAL_TAB_NAME} tab...")
    final_ws.update('A1', update_data)
    
    # Update styling (optional but useful for charts: numbers correctly cast, bold headers)
    final_ws.format('A1:I1', {'textFormat': {'bold': True}})
    print("Done! View the new tab on Google Sheets to build your Google Chart!")

if __name__ == "__main__":
    run_consolidation()
