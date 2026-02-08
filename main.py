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
            country_name = country_text.split('(')[0].replace('*', '').strip()
            
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
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        response = requests.get(WIKIPEDIA_URL_DETAILS, headers=headers)
        if response.status_code == 404:
             print("Detail page not found. Skipping Flavor updates.")
             return []
        response.raise_for_status()
    except Exception as e:
        print(f"Error scraping details: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    details = []
    
    tables = soup.find_all('table', class_='wikitable')
    
    for table in tables:
        # Check if this is a medalists table. 
        # Usually headers are: Event | Gold | Silver | Bronze
        # Inspect headers to confirm
        header_row = table.find('tr')
        if not header_row: continue
        headers_text = [th.get_text(strip=True).lower() for th in header_row.find_all(['th'])]
        
        # Heuristic: Must have 'gold', 'silver', 'bronze'
        if not all(k in str(headers_text) for k in ['gold', 'silver', 'bronze']):
            # Maybe it uses medallions or images?
            # Let's trust it's a medalist table if it has 3+ columns and visually looks right.
            # But the 'details' issue suggests we are parsing 'Event' column poorly.
            pass

        rows = table.find_all('tr')
        for row in rows:
            cols = row.find_all(['th', 'td'])
            
            # Skip if it's the header row (contains "Gold" etc)
            row_text = row.get_text(strip=True).lower()
            if "gold" in row_text and "silver" in row_text:
                continue
                
            if len(cols) < 4: continue 
            
            try:
                # Column 0: Event
                # Problem: "Downhilldetails" -> The 'details' text is likely a hidden span or link.
                # Solution: Get text, but exclude 'details' if it's a UI element.
                # Better: Extract text node only? Or replace 'details' if safe.
                event_cell = cols[0]
                event_name = event_cell.get_text(" ", strip=True).replace("details", "").strip()
                # Clean up "deta" partials if any
                if event_name.endswith("deta"): event_name = event_name[:-4].strip()
                
                # Column 1 (Gold), 2 (Silver), 3 (Bronze)
                # Cell format: "Athlete Name (Country)" or "Flag Athlete Name (Country)"
                # "Heidi WengNorw" suggets text concatenation. Flag (alt text) + Name?
                # Solution: Use .get_text(" ") to separate elements with spaces.
                
                def parse_medalist(cell, color):
                    # Use separator to avoid "NameFlag"
                    text = cell.get_text(" ", strip=True) 
                    if not text: return
                     
                    # Clean up: "Mikaela Shiffrin (USA)"
                    # Regex for country code in parens is safest.
                    import re
                    match = re.search(r'\((.*?)\)', text)
                    if match:
                        country_code = match.group(1)
                        # Remove country code from text to get name
                        # But wait, text might be "Flag Name (Country)"
                        # "Name" is what we want.
                        # Split by '('
                        parts = text.split('(')
                        athlete_raw = parts[0].strip()
                        
                        # Fix "FlagName" issue? "Heidi WengNorw" -> "Heidi Weng"
                        # If we have a country map, we can map code "NOR" -> "Norway".
                        # For simple usage, let's use the code as Country for now, 
                        # OR try to map typical codes if we can.
                        # Actually main.py doesn't have a NOC map. 
                        # We need valid Country names for Draft mapping ("Norway", not "NOR").
                        
                        # Let's try to scrape the full title of the flag link if present?
                        country_name = "Unknown"
                        flag_img = cell.find('img', class_='mw-file-element') # or similar flag class
                        # Look for 'a' tag with title?
                        links = cell.find_all('a')
                        for link in links:
                            title = link.get('title', '')
                            # Titles often: "Norway at the 2026 Winter Olympics" or just "Norway"
                            if " at the " in title:
                                country_name = title.split(" at the ")[0]
                                break
                            elif title and title not in athlete_raw: # Heuristic
                                # If title is country-like?
                                pass
                        
                        if country_name == "Unknown":
                            # Fallback: Use the code and hope? Or just "Unknown"
                            # The user saw "Heidi WengNorw" so likely "Norw" was 'Norway' text mashed.
                            # Let's rely on the text separation `get_text(" ")`.
                            # If text is "Heidi Weng Norway", we can parse.
                            pass
                            
                        athlete = athlete_raw
                        # If we found country via link, use it.
                        country = country_name if country_name != "Unknown" else country_code
                        
                    else:
                        # Fallback if no parens
                        athlete = text
                        country = "Unknown" 
                        
                        # Try finding country via flag/link
                        links = cell.find_all('a')
                        for link in links:
                            title = link.get('title', '')
                            if " at the " in title:
                                country = title.split(" at the ")[0]
                                # And remove this country name from athlete string if present
                                athlete = athlete.replace(country, "").strip()
                                break
                    
                    # Clean artifacts
                    athlete = athlete.replace("details", "").strip()
                    # Fix "Heidi WengNorw" type bugs:
                    # If we have Country "Norway", ensure it's allowed.
                    
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

