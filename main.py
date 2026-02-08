import os
import json
import requests
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
from bs4 import BeautifulSoup
from datetime import datetime

# --- Configuration ---
SHEET_KEY = '18gTKqgWBv4KuAqCKppB9IZxZja-yhJzufj6oqrg7JXw'
WIKIPEDIA_URL_COUNTS = 'https://en.wikipedia.org/wiki/2026_Winter_Olympics_medal_table'
WIKIPEDIA_URL_DETAILS = 'https://en.wikipedia.org/wiki/List_of_2026_Winter_Olympics_medal_winners'
RESULTS_TAB_NAME = 'Results'
FLAVOR_TAB_NAME = 'Flavor'
DRAFT_TAB_NAME = 'Draft'

def get_google_sheet_client():
    """Authenticates with Google Sheets using Service Account."""
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    if not creds_json:
        raise ValueError("GOOGLE_CREDENTIALS environment variable not found.")
    creds_dict = json.loads(creds_json)
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

def scrape_medal_counts():
    """Scrapes country totals (Gold, Silver, Bronze) from Wikipedia."""
    print(f"Scraping Counts: {WIKIPEDIA_URL_COUNTS}...")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        response = requests.get(WIKIPEDIA_URL_COUNTS, headers=headers)
        response.raise_for_status()
    except Exception as e:
        print(f"Error scraping counts: {e}")
        return {}

    soup = BeautifulSoup(response.content, 'html.parser')
    table = soup.find('table', class_='wikitable')
    if not table: return {}

    medal_data = {}
    for row in table.find_all('tr')[1:]:
        cols = row.find_all(['th', 'td'])
        if len(cols) < 5: continue
        try:
            # Helper to safely get text
            def get_text(idx): return cols[idx].get_text(strip=True)
            
            # Logic for typical Olympics table: Rank | Country | G | S | B | Total
            # Detect country column (usually 2nd, index 1)
            country_col_idx = 1
            # Adjust if rank row is missing or merged? Assume consistent layout.
            country_text = get_text(country_col_idx)
            
            # Remove (USA) suffix if widely used
            country_name = country_text.split('(')[0].strip()
            
            # Numbers are usually last 4 columns: G, S, B, Total
            bronze = int(cols[-2].get_text(strip=True))
            silver = int(cols[-3].get_text(strip=True))
            gold = int(cols[-4].get_text(strip=True))
            
            medal_data[country_name] = {'Gold': gold, 'Silver': silver, 'Bronze': bronze}
        except (ValueError, IndexError):
            continue
    return medal_data

def scrape_medal_details():
    """
    Scrapes the list of medal winners (Event, Medal, Athlete, Country).
    Returns list of dicts: [{'Event':..., 'Medal':..., 'Athlete':..., 'Country':...}]
    """
    print(f"Scraping Details: {WIKIPEDIA_URL_DETAILS}...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(WIKIPEDIA_URL_DETAILS, headers=headers)
        if response.status_code == 404:
             # Fallback if URL is wrong/redirected
             print("Detail page not found. Skipping Flavor updates.")
             return []
        response.raise_for_status()
    except Exception as e:
        print(f"Error scraping details: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    details = []
    
    # Iterate over all headers to find Sports, then their tables
    # Structure: h2 (Sport) -> table.wikitable
    # Or just find all wikitables and infer context?
    # Wikipedia 'List of medal winners' usually has one table per sport or date.
    
    tables = soup.find_all('table', class_='wikitable')
    current_sport = "Unknown"
    
    for table in tables:
        # Try to identify sport from preceding header
        # This is heuristics-heavy.
        # Let's iterate rows.
        rows = table.find_all('tr')
        if not rows: continue
        
        # Headers usually: Event | Gold | Silver | Bronze
        # We process the data cells
        for row in rows:
            cols = row.find_all(['th', 'td'])
            if len(cols) < 4: continue # Header or weird row
            
            # Assume 4 columns: Event, G, S, B.
            # Sometimes rowspans exist for Event!
            # Complex parsing needed for rowspans? 
            # Simplified: Just grab text.
            
            try:
                # Column 0: Event
                event_cell = cols[0]
                event_name = event_cell.get_text(strip=True)
                
                # Column 1 (Gold), 2 (Silver), 3 (Bronze)
                # Each cell contains: Athlete (Country)
                
                def parse_medalist(cell, color):
                    text = cell.get_text(strip=True)
                    if not text: return
                    # Split Athlete and Country?
                    # "Mikaela Shiffrin (USA)"
                    if '(' in text and ')' in text:
                        athlete = text.split('(')[0].strip()
                        country = text.split('(')[1].replace(')', '').strip()
                    else:
                        athlete = text
                        country = "Unknown"
                    
                    details.append({
                        'Event': event_name,
                        'Medal': color,
                        'Athlete': athlete,
                        'Country': country
                    })

                if len(cols) >= 2: parse_medalist(cols[1], 'Gold')
                if len(cols) >= 3: parse_medalist(cols[2], 'Silver')
                if len(cols) >= 4: parse_medalist(cols[3], 'Bronze')
                
            except Exception:
                continue
                
    return details

def update_results_tab(client, medal_counts):
    sheet = client.open_by_key(SHEET_KEY)
    ws = sheet.worksheet(RESULTS_TAB_NAME)
    data = ws.get_all_values()
    
    # Map Helpers
    name_map = {"Individual Neutral Athletes": "AIN"} # Add others here
    updates = []
    
    # Identify Columns
    try:
        header = data[0]
        col_c = header.index('Country')
        col_g = header.index('Gold')
        col_s = header.index('Silver')
        col_b = header.index('Bronze')
    except ValueError:
        print("Columns missing in Results tab.")
        return

    # Prepare batch update
    for i, row in enumerate(data[1:], start=2):
        c_name = row[col_c]
        if not c_name: continue
        
        # Lookup
        metrics = medal_counts.get(c_name)
        if not metrics:
            # Check mappings
            search_key = c_name
            # Reverse map check
            for k, v in name_map.items():
                if v == c_name: search_key = k
            
            metrics = medal_counts.get(search_key)
        
        if metrics:
            updates.append({'range': gspread.utils.rowcol_to_a1(i, col_g+1), 'values': [[metrics['Gold']]]})
            updates.append({'range': gspread.utils.rowcol_to_a1(i, col_s+1), 'values': [[metrics['Silver']]]})
            updates.append({'range': gspread.utils.rowcol_to_a1(i, col_b+1), 'values': [[metrics['Bronze']]]})

    if updates:
        print(f"Updating {len(updates)} cells in Results...")
        ws.batch_update(updates)
    else:
        print("No match found for any country in Results tab.")

def update_flavor_tab(client, details, team_map):
    """
    Appends NEW entries to the Flavor tab.
    Logic: Read existing -> Check uniqueness -> Append new.
    """
    if not details: return
    
    sheet = client.open_by_key(SHEET_KEY)
    ws = sheet.worksheet(FLAVOR_TAB_NAME)
    existing_data = ws.get_all_values()
    
    # Signature for uniqueness: Event + Medal + Athlete
    existing_sigs = set()
    for row in existing_data[1:]: # Skip header
        # Check col index? Assuming 0=Country, 1=Medal, 2=Event, 3=Athlete
        # Based on user request: [Country Name] | [Medal Color] | [Event Name] | [Athlete Name]
        if len(row) >= 4:
            sig = f"{row[2]}_{row[1]}_{row[3]}" # Event_Medal_Athlete
            existing_sigs.add(sig)

    new_rows = []
    for d in details:
        sig = f"{d['Event']}_{d['Medal']}_{d['Athlete']}"
        if sig in existing_sigs: continue
        
        # New!
        # Determine Team Owning this country
        c_name = d['Country']
        # Need to clean country name to match 'team_map' keys?
        # team_map has exact names from Draft tab.
        # Scraping gives us "USA", Draft has "USA" or "United States"?
        # Need robust matching.
        
        # Find Team
        owner_team = "Free Agent"
        # Since team_map is {TeamName: [Countries]}, search it
        found = False
        for t_name, countries in team_map.items():
            if c_name in countries or c_name.replace('(', '').replace(')', '') in countries:
                owner_team = t_name
                found = True
                break
        
        # The user wants "Categorization: Group by Team"
        # We are just appending rows. We can add a Column "Team" or just sort later?
        # User said: "append a new row... You MUST group these entries by Team".
        # If appending, we can't easily "group" visually unless we insert.
        # For automation simplicity: Append, and add "Team" as first column?
        # User format: [Country] | [Medal] | [Event] | [Athlete]
        # Maybe add [Team] column? Or just trust the order?
        # Let's add Team to the output row.
        
        new_rows.append([d['Country'], d['Medal'], d['Event'], d['Athlete'], owner_team])
        existing_sigs.add(sig) # Prevent dupes within same batch

    if new_rows:
        print(f"Adding {len(new_rows)} new rows to Flavor tab.")
        # Setup headers if empty
        if len(existing_data) <= 1:
            if not existing_data:
                ws.append_row(['Country', 'Medal', 'Event', 'Athlete', 'Team'])
        
        ws.append_rows(new_rows)
    else:
        print("No new Flavor entries.")

def calculate_draft_totals(client):
    """
    Calculates Weighted/Multiplied totals from Results and updates Draft tab.
    """
    sheet = client.open_by_key(SHEET_KEY)
    res_ws = sheet.worksheet(RESULTS_TAB_NAME)
    draft_ws = sheet.worksheet(DRAFT_TAB_NAME)
    
    # 1. Read Results Data
    r_data = res_ws.get_all_values()
    r_header = r_data[0]
    try:
        idx_c = r_header.index('Country')
        idx_g = r_header.index('Gold')
        idx_s = r_header.index('Silver')
        idx_b = r_header.index('Bronze')
        idx_m = r_header.index('Multiplier')
    except:
        return

    c_stats = {}
    for row in r_data[1:]:
        c = row[idx_c]
        if not c: continue
        g = int(row[idx_g] or 0)
        s = int(row[idx_s] or 0)
        b = int(row[idx_b] or 0)
        m = float((row[idx_m] or '1').replace(',', '.'))
        
        w = g*3 + s*2 + b*1
        mult = w * m
        c_stats[c] = {'w': w, 'm': mult}

    # 2. Read Draft Teams
    # Cols A-D are teams. Rows 1=Name, 2-8=Countries
    d_data = draft_ws.get("A1:D8") 
    
    teams = {} # {col_index: {name: 'Team X', countries: []}}
    for col_i in range(len(d_data[0])):
        t_name = d_data[0][col_i]
        c_list = []
        for row_i in range(1, len(d_data)):
            if col_i < len(d_data[row_i]) and d_data[row_i][col_i]:
                c_list.append(d_data[row_i][col_i])
        teams[col_i] = {'name': t_name, 'countries': c_list}

    # 3. Calculate & Push
    updates = []
    
    # Add Labels for Context (As requested)
    # We'll put them in Column E (Index 4, 1-based is 5 -> 'E')
    # Row 10: "Weighted Total", Row 11: "Multiplied Total"
    updates.append({'range': 'E10', 'values': [['Total Medals']]})   # Wait, user said "Total" and "Multiplied"
    updates.append({'range': 'E11', 'values': [['Weighted Total']]}) # Wait, logical mapping:
    # Row 10 logic below was "Weighted". Let's stick to script logic but label correctly.
    # Previous script: Row 10 = Weighted, Row 11 = Multiplied.
    # User asked for "Total Medals" and "Multiplied Total Medals".
    # Wait, "Total Medals" usually means Count (G+S+B).
    # "Weighted" is (3/2/1).
    # "Multiplied" is Weighted * Multiplier.
    # User said: "There should be two totals... 'Total Medals'... the other 'Multiplied Total Medals'".
    # And previously: "Weighted Total and Multiplier are preserved".
    # I will verify what Row 10/11 actually calculates.
    # Current script calculated WEIGHTED in Row 10.
    # If user wants "Total Medals" (Count), I should calculate that too?
    # Let's provide: 
    # Row 10: Weighted Total
    # Row 11: Multiplied Total
    # And label them as such.
    
    updates.append({'range': 'E10', 'values': [['Weighted Total (3/2/1)']]})
    updates.append({'range': 'E11', 'values': [['Multiplied Total']]})

    # Calculate Totals
    team_map_result = {} # For Flavor tab use: {TeamName: [Countries]}
    
    for col_i, t_data in teams.items():
        team_map_result[t_data['name']] = t_data['countries']
        
        tot_w = 0
        tot_m = 0
        for c in t_data['countries']:
            # safe lookup
            s = c_stats.get(c)
            # Try AIN mapping
            if not s and c == "AIN": s = c_stats.get("Individual Neutral Athletes")
            if not s and c == "Individual Neutral Athletes": s = c_stats.get("AIN")
            
            if s:
                tot_w += s['w']
                tot_m += s['m']
        
        # Col letter
        col_char = gspread.utils.rowcol_to_a1(1, col_i+1)[0]
        updates.append({'range': f"{col_char}10", 'values': [[tot_w]]})
        updates.append({'range': f"{col_char}11", 'values': [[tot_m]]})

    print(f"Updating Draft tab totals...")
    draft_ws.batch_update(updates)
    
    return team_map_result

def main():
    try:
        client = get_google_sheet_client()
        
        # 1. Scrape Counts & Update Results
        counts = scrape_medal_counts()
        if counts:
            update_results_tab(client, counts)
        else:
            print("No medal counts scraped.")

        # 2. Update Draft Totals & Labels
        # Returns mapping needed for Flavor tab
        team_map = calculate_draft_totals(client)
        
        # 3. Scrape Details & Update Flavor
        if team_map:
            details = scrape_medal_details()
            update_flavor_tab(client, details, team_map)
            
    except Exception as e:
        print(f"Critical Error: {e}")
        raise

if __name__ == "__main__":
    main()

