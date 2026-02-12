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

# --- Mappings ---
COUNTRY_NAME_MAP = {
    "United States": "USA",
    "South Korea": "Republic of Korea",
    "Great Britain": "United Kingdom",
    "China": "People's Republic of China",
    "ROC": "Russian Olympic Committee",
    "Czech Republic": "Czechia",
    "Netherlands": "Netherlands", # Explicit map just in case
    "The Netherlands": "Netherlands"
}

def normalize_country_name(name):
    """
    Normalizes a country name for fuzzy matching.
    - Lowercase
    - Remove 'the', 'republic of', 'people's republic of'
    - Strip whitespace
    """
    if not name: return ""
    name = name.lower()
    for prefix in ["the ", "republic of ", "people's republic of "]:
        if name.startswith(prefix):
            name = name[len(prefix):]
    return name.strip()

def update_results_tab(client, medal_counts):
    sheet = client.open_by_key(SHEET_KEY)
    ws = sheet.worksheet(RESULTS_TAB_NAME)
    data = ws.get_all_values()
    
    # Map Helpers
    # "Individual Neutral Athletes" is a special case often requiring manual handling or specific mapping
    name_map = {"Individual Neutral Athletes": "AIN"} 
    
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
    matched_scraped_keys = set()
    
    for i, row in enumerate(data[1:], start=2):
        c_name = row[col_c]
        if not c_name: continue
        
        # Lookup Logic:
        metrics = None
        matched_key = None
        
        # 1. Direct match
        if c_name in medal_counts:
            metrics = medal_counts[c_name]
            matched_key = c_name

        if not metrics:
            # 2. Try Fuzzy Match against Medal Counts (Scraped Data)
            c_norm = normalize_country_name(c_name)
            for k, v in medal_counts.items():
                if normalize_country_name(k) == c_norm:
                    metrics = v
                    matched_key = k
                    break
            
            # 3. Try Mapping (Reverse Lookup)
            if not metrics:
                for scraped_name, sheet_name in COUNTRY_NAME_MAP.items():
                     # Check exact or fuzzy match of Sheet Name
                     if sheet_name == c_name or normalize_country_name(sheet_name) == c_norm:
                        metrics = medal_counts.get(scraped_name)
                        matched_key = scraped_name
                        # If map key isn't exactly in medal_counts, try fuzzy match there too
                        if not metrics:
                             s_norm = normalize_country_name(scraped_name)
                             for mk, mv in medal_counts.items():
                                 if normalize_country_name(mk) == s_norm:
                                     metrics = mv
                                     matched_key = mk
                                     break
                        if metrics: break
            
            # 4. Fallback for AIN (Legacy check)
            if not metrics:
                 for k, v in name_map.items():
                    if v == c_name: 
                        metrics = medal_counts.get(k)
                        matched_key = k
                        if metrics: break
            
            # DEBUG LOGGING for Results Tab
            if any(t in c_name for t in ["Finland", "Korea", "Netherlands"]):
                match_status = f"MATCHED (Data: {metrics})" if metrics else "NO MATCH"
                print(f"RESULTS DEBUG: Sheet Row '{c_name}' -> {match_status}")

        if metrics:
            if matched_key: matched_scraped_keys.add(matched_key)
            
            updates.append({'range': gspread.utils.rowcol_to_a1(i, col_c+1), 'values': [[c_name]]}) # Rewrite name to be safe? No.
            # col_g is 0-indexed. rowcol_to_a1 needs 1-indexed.
            updates.append({'range': gspread.utils.rowcol_to_a1(i, col_g+1), 'values': [[metrics['Gold']]]})
            updates.append({'range': gspread.utils.rowcol_to_a1(i, col_s+1), 'values': [[metrics['Silver']]]})
            updates.append({'range': gspread.utils.rowcol_to_a1(i, col_b+1), 'values': [[metrics['Bronze']]]})

    if updates:
        print(f"Updating {len(updates)} cells in Results...")
        ws.batch_update(updates)
    else:
        print("No match found for any country in Results tab.")

    # --- Auto-Append Missing Countries ---
    all_scraped_keys = set(medal_counts.keys())
    missing_keys = all_scraped_keys - matched_scraped_keys
    
    if missing_keys:
        print(f"Found {len(missing_keys)} countries in scraper but NOT in sheet. Appending...")
        new_rows = []
        for k in missing_keys:
            # Check if likely irrelevant (optional, but good for safety)
            # if medal_counts[k]['Gold'] == 0 ...? No, we want all medal winners.
            
            data = medal_counts[k]
            # Row Format: [Country, Gold, Silver, Bronze, Weight(1)...]
            # We need to respect column order.
            # We know indices: col_c, col_g, col_s, col_b.
            # We assume they are roughly 0, 1, 2, 3.
            # But let's construct a row distinct by max index.
            
            max_idx = max(col_c, col_g, col_s, col_b)
            row_vals = [''] * (max_idx + 1)
            
            row_vals[col_c] = k
            row_vals[col_g] = data['Gold']
            row_vals[col_s] = data['Silver']
            row_vals[col_b] = data['Bronze']
            
            # Optional: Add Weight=1 if column exists?
            # Let's check header for 'Weight' or 'Multiplier'
            try:
                col_w = header.index('Multiplier')
                if col_w > max_idx:
                    row_vals.extend([''] * (col_w - max_idx))
                row_vals[col_w] = 1
            except ValueError:
                pass # No multiplier column found
                
            new_rows.append(row_vals)
            print(f"  -> Appending {k}: {data}")

        if new_rows:
            ws.append_rows(new_rows)
            print("Appended missing countries.")

def update_flavor_tab(client, details, team_map):
    """
    Appends NEW entries to the Flavor tab.
    Logic: Read existing -> Check uniqueness -> Append new.
    Also handles basic cleanup of "messy" rows if detected.
    """
    if not details: return
    
    sheet = client.open_by_key(SHEET_KEY)
    ws = sheet.worksheet(FLAVOR_TAB_NAME)
    existing_data = ws.get_all_values()
    
    # --- Cleanup Logic ---
    # Check if header is wrong or data is messy
    headers = existing_data[0] if existing_data else []
    
    # Aggressive check: If the first column header isn't "Date", we wipe it.
    # This handles the schema migration from [Country, Medal...] to [Date, Country...]
    if not headers or headers[0] != "Date":
        print("Flavor tab has old schema or is messy. Wiping and resetting...")
        # Clear everything and set correct headers
        ws.clear()
        ws.append_row(['Date', 'Country', 'Medal', 'Event', 'Athlete', 'Team'])
        existing_data = [] # Reset local cache
    
    # Signature for uniqueness: Event + Medal + Athlete
    existing_sigs = set()
    # Skip header
    start_row_idx = 1 if existing_data else 0
    
    # Need to know which column is which in EXISTING data to check dupes
    # New Format: Date (0), Country (1), Medal (2), Event (3), Athlete (4), Team (5)
    # Old Format (if any survived): Country(0), Medal(1), Event(2), Athlete(3), Team(4)
    # If we just cleared, it's empty.
    
    for row in existing_data[start_row_idx:]:
        # Robust signature check
        # Try to find Event/Medal/Athlete columns by content specific?
        # Or just assume new format if headers match.
        if len(row) >= 5:
            # Assuming new format or similar enough to detect dupes
            # Let's use a broad signature: concatenate all except Date?
            # Or just Event+Medal+Athlete
            # In new format: Event is idx 3, Medal is idx 2, Athlete is idx 4
            if len(row) >= 5:
                 sig = f"{row[3]}_{row[2]}_{row[4]}" 
                 existing_sigs.add(sig)

    new_rows = []
    
    # Calculate Date in CST (Central Standard Time)
    # GitHub Actions are UTC. CST is UTC-6, CDT is UTC-5.
    # Current time is Feb. 8th UTC, but Feb. 7th CST.
    # Simple fix: utcnow() - 6 hours.
    # Or just use timezone specific library if available.
    # We'll use datetime.utcnow() and subtract 6 hours for now to be safe without pytz.
    from datetime import timedelta
    cst_now = datetime.utcnow() - timedelta(hours=6)
    today_str = cst_now.strftime("%Y-%m-%d")
    
    for d in details:
        sig = f"{d['Event']}_{d['Medal']}_{d['Athlete']}"
        if sig in existing_sigs: continue
        
        # New!
        c_name = d['Country']
        
        # Find Team
        owner_team = "Free Agent"
        
        # Normalize for matching: allow flexible matching against team list
        # Map scraped name to potential sheet names?
        # Or just try exact, then map.
        
        found = False
        for t_name, countries in team_map.items():
            if found: break
            
            # Check 1: Direct presence
            if c_name in countries:
                owner_team = t_name
                found = True
                break
            
            # Check 2: Fuzzy / Case insensitive
            c_norm = normalize_country_name(c_name)
            for c in countries:
                if normalize_country_name(c) == c_norm:
                    owner_team = t_name
                    found = True
                    break
            
            # Check 3: Map Lookup
            # If d['Country'] is "United States", maybe team has "USA"
            if not found:
                mapped_name = COUNTRY_NAME_MAP.get(c_name)
                # Direct Map Check
                if mapped_name and mapped_name in countries:
                    owner_team = t_name
                    found = True
                    break
                
                # Check normalized map result
                if mapped_name:
                    m_norm = normalize_country_name(mapped_name)
                    for c in countries:
                        if normalize_country_name(c) == m_norm:
                            owner_team = t_name
                            found = True
                            break
        
        # New Row Format: [Date, Country, Medal, Event, Athlete, Team]
        # We use today's date because Wikipedia doesn't provide it easily.
        # User asked for "date they were earned". 
        # Since we run daily, "today" is a good approximation for NEW rows.
        
        new_rows.append([today_str, d['Country'], d['Medal'], d['Event'], d['Athlete'], owner_team])
        existing_sigs.add(sig) # Prevent dupes within same batch

    if new_rows:
        print(f"Adding {len(new_rows)} new rows to Flavor tab.")
        # append_rows needs a list of lists
        ws.append_rows(new_rows, value_input_option='USER_ENTERED')
    else:
        print("No new Flavor entries.")

def repair_flavor_teams(client, team_map):
    """
    One-off / Retroactive fix:
    Iterates through ALL Flavor tab rows.
    If a row has a Country that maps to a Team, but the current Team is 'Free Agent' (or empty),
    update it to the correct Team.
    """
    print("Running Retroactive Flavor Team Repair...")
    sheet = client.open_by_key(SHEET_KEY)
    ws = sheet.worksheet(FLAVOR_TAB_NAME)
    data = ws.get_all_values()
    
    if not data: return

    headers = data[0]
    try:
        col_country = headers.index('Country')
        col_team = headers.index('Team')
    except ValueError:
        print("Flavor tab missing headers for Repair.")
        return

    updates = []
    
    for i, row in enumerate(data[1:], start=2):
        # Safety check for row length
        if len(row) <= max(col_country, col_team): continue
        
        current_team = row[col_team]
        c_name = row[col_country]
        
        # Only try to repair if it looks like it needs it (Optional: or correct mismatch?)
        # Let's be safe: If it's "Free Agent" or empty, DEFINITELY try to fix.
        if current_team not in ["Free Agent", ""]: 
             continue
             
        # Debug Logging for Targets
        is_target = any(t in c_name for t in ["Netherlands", "Korea"])
        
        # --- Logic from update_flavor_tab (Shared) ---
        owner_team = "Free Agent"
        found = False
        
        match_type = ""

        # 1. Direct
        for t_name, countries in team_map.items():
            if c_name in countries:
                owner_team = t_name
                found = True
                match_type = "Direct"
                break
        
        # 2. Fuzzy
        if not found:
            c_norm = normalize_country_name(c_name)
            for t_name, countries in team_map.items():
                for c in countries:
                    if normalize_country_name(c) == c_norm:
                        owner_team = t_name
                        found = True
                        match_type = f"Fuzzy (Matched '{c}')"
                        break
                if found: break
        
        # 3. Map Rule
        if not found:
            mapped_name = COUNTRY_NAME_MAP.get(c_name)
            if mapped_name:
                # Direct check
                for t_name, countries in team_map.items():
                    if mapped_name in countries:
                        owner_team = t_name
                        found = True
                        match_type = f"Map Direct ('{mapped_name}')"
                        break
                
                # Normalized Map check
                if not found:
                    m_norm = normalize_country_name(mapped_name)
                    for t_name, countries in team_map.items():
                        for c in countries:
                             if normalize_country_name(c) == m_norm:
                                 owner_team = t_name
                                 found = True
                                 match_type = f"Map Fuzzy ('{mapped_name}' -> '{c}')"
                                 break
                        if found: break
        
        if is_target:
             if found:
                 print(f"DEBUG: Found '{c_name}' -> '{owner_team}' via {match_type}")
             else:
                 print(f"DEBUG: FAILED to match '{c_name}'. Current Team Map Keys: {list(team_map.keys())}")
                 # Optional: print close matches?

        # --- Apply Update if Found & Different ---

        
        # --- Apply Update if Found & Different ---
        if found and owner_team != current_team:
            print(f"Repairing Row {i}: {c_name} -> {owner_team} (Was: '{current_team}')")
            # Convert to A1 notation for update
            # col_team is 0-indexed. gspread is 1-indexed.
            col_letter = gspread.utils.rowcol_to_a1(1, col_team + 1)[0]
            cell_range = f"{col_letter}{i}"
            updates.append({'range': cell_range, 'values': [[owner_team]]})

    if updates:
        ws.batch_update(updates)
        print(f"Repaired {len(updates)} Flavor rows.")
    else:
        print("No Flavor rows needed repair.")

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
    # Dynamic read instead of fixed range
    d_data = draft_ws.get_all_values()
    
    # Assumption: Row 1 has Team Names. Susequent rows have countries.
    # We'll identify valid columns by checking Row 1
    if not d_data: return {}
    
    teams = {} # {col_index: {name: 'Team X', countries: []}}
    header = d_data[0]
    
    for col_i, t_name in enumerate(header):
        if not t_name: continue # Skip empty columns
        # Initialize
        teams[col_i] = {'name': t_name, 'countries': []}
        
    # Iterate rows for countries
    for row in d_data[1:]:
        for col_i, cell_val in enumerate(row):
             if col_i in teams and cell_val:
                 teams[col_i]['countries'].append(cell_val)

    # 3. Calculate & Push
    updates = []
    
    # Determine where to put totals (Dynamic Row)
    # d_data includes header (Row 1). len(d_data) is the number of rows read.
    # If d_data has 15 rows, the last row index is 14 (0-based) -> Row 15 (1-based).
    # We want totals at Row 17 (last + 2).
    # Minimum Row: 10 (to preserve original layout if list is short)
    
    last_data_row = len(d_data)
    total_row_idx = max(10, last_data_row + 2) # 1-based index for gspread
    
    # Row 1: Weighted Total
    # Row 2: Multiplied Total
    row_w_idx = total_row_idx
    row_m_idx = total_row_idx + 1
    
    # Labels
    updates.append({'range': f'E{row_w_idx}', 'values': [['Total Medals (Weighted)']]})
    updates.append({'range': f'E{row_m_idx}', 'values': [['Multiplied Total']]})

    # Calculate Totals
    team_map_result = {} # For Flavor tab use: {TeamName: [Countries]}
    
    for col_i, t_data in teams.items():
        team_map_result[t_data['name']] = t_data['countries']
        
        tot_w = 0
        tot_m = 0
        for c in t_data['countries']:
            # safe lookup
            s = c_stats.get(c)
            
            # Lookup with Mapping if direct fail
            if not s:
                 # Check if 'c' is a key in our map (User typed "United States") -> mapped to "USA"
                 mapped = COUNTRY_NAME_MAP.get(c) 
                 if mapped: s = c_stats.get(mapped)
                 
                 # Fuzzy Match Attempt
                 if not s:
                     c_norm = normalize_country_name(c)
                     # Iterate all stats keys
                     for k, v in c_stats.items():
                         if normalize_country_name(k) == c_norm:
                             s = v
                             break
                     if not s:
                         for k, v in COUNTRY_NAME_MAP.items():
                             # If user typed "The Netherlands", norm is "netherlands"
                             # Map key might be "Netherlands", value "Netherlands"
                             if normalize_country_name(k) == c_norm:
                                 # Found map key. Now get stats for value?
                                 mapped_val = v
                                 s = c_stats.get(mapped_val)
                                 if s: break
                                 
                     # Reverse Mapping (Value -> Key)
                     # User has "Republic of Korea" (Value in Map), Scraper has "South Korea" (Key in Map).
                     if not s:
                         for k, v in COUNTRY_NAME_MAP.items():
                             # Check exact or fuzzy match of Value
                             if v == c or normalize_country_name(v) == c_norm:
                                 # Found match. Scraper Key is k.
                                 s = c_stats.get(k)
                                 if s: break

            # Try AIN mapping
            if not s and "individual" in c.lower(): s = c_stats.get("AIN") or c_stats.get("Individual Neutral Athletes")
            if not s and c == "AIN": s = c_stats.get("Individual Neutral Athletes")
            
            # DEBUG LOGGING for User Issues
            if any(target in c for target in ["Finland", "Korea", "Netherlands"]):
                found_status = "FOUND" if s else "MISSING"
                print(f"DRAFT DEBUG: Country '{c}' -> {found_status} (Stats: {s})")
            
            if s:
                tot_w += s['w']
                tot_m += s['m']
        
        # Col letter
        col_char = gspread.utils.rowcol_to_a1(1, col_i+1)[0]
        updates.append({'range': f"{col_char}{row_w_idx}", 'values': [[tot_w]]})
        updates.append({'range': f"{col_char}{row_m_idx}", 'values': [[tot_m]]})

    print(f"Updating Draft tab totals at Row {row_w_idx}...")
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
            
            # 4. Retroactive Repair (One-off/Ongoing safety)
            repair_flavor_teams(client, team_map)
            
    except Exception as e:
        print(f"Critical Error: {e}")
        raise

if __name__ == "__main__":
    main()

