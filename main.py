import os
import json
import requests
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
from bs4 import BeautifulSoup
from datetime import datetime

# --- Configuration ---
SHEET_KEY = '18gTKqgWBv4KuAqCKppB9IZxZja-yhJzufj6oqrg7JXw'  # From user provided URL
WIKIPEDIA_URL = 'https://en.wikipedia.org/wiki/2026_Winter_Olympics_medal_table'
RESULTS_TAB_NAME = 'Results'
FLAVOR_TAB_NAME = 'Flavor'
DRAFT_TAB_NAME = 'Draft'

def get_google_sheet_client():
    """
    Authenticates with Google Sheets using the Service Account JSON found in
    environment variable 'GOOGLE_CREDENTIALS'.
    """
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    if not creds_json:
        raise ValueError("GOOGLE_CREDENTIALS environment variable not found.")
    
    creds_dict = json.loads(creds_json)
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

def scrape_medal_data():
    """
    Scrapes the Wikipedia medal table for the 2026 Winter Olympics.
    Returns a dictionary: { 'Country Name': {'Gold': X, 'Silver': Y, 'Bronze': Z}, ... }
    """
    print(f"Scraping {WIKIPEDIA_URL}...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(WIKIPEDIA_URL, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Locate the medal table
    # Wikipedia tables usually have class 'wikitable' and 'sortable'
    # For Olympics, it's often the first wikitable with 'Medal table' caption or similar.
    # Note: Structure might change if table is empty, but we'll target the standard layout.
    
    table = soup.find('table', class_='wikitable')
    if not table:
        print("Warning: Medal table not found on Wikipedia page. Assuming 0 medals generally.")
        return {}

    medal_data = {}
    
    # Iterate over rows, skipping header
    rows = table.find_all('tr')
    for row in rows[1:]:
        cols = row.find_all(['th', 'td'])
        if len(cols) < 5:
            continue
            
        # Wikipedia table typical format: Rank | NOC (Country) | Gold | Silver | Bronze | Total
        # Sometimes Rank is not in a th/td or is merged. Context dependent.
        # usually 2nd col is Country if Rank is present.
        
        # Let's try to identify the country name. it usually contains a link and text.
        try:
            country_col = cols[1] if len(cols) > 5 else cols[0] # Very robust check needed here usually
            country_text = country_col.get_text(strip=True)
            
            # Extract numbers
            # Assuming G, S, B are cols 2, 3, 4 (0-indexed) if Rank is 0
            # If Rank is present (often 'Rank' header), it shifts.
            
            # Heuristic: look for the numbers from the right side.
            # Typical: [Rank] [Country] [G] [S] [B] [Total]
            # Verify headers usually, but for a strict script:
            
            bronze = int(cols[-2].get_text(strip=True))
            silver = int(cols[-3].get_text(strip=True))
            gold = int(cols[-4].get_text(strip=True))
            
            # Clean country name (remove " (MEX)" etc if needed, or keeping it to match sheet)
            # Sheet likely uses standard names. Wikipedia might have "United States" or "USA".
            # We'll need a mapper or fuzzy matcher later. For now, raw.
            medal_data[country_text] = {'Gold': gold, 'Silver': silver, 'Bronze': bronze}
        except (ValueError, IndexError):
            continue

    return medal_data

def update_sheet(client, scraped_data):
    """
    Updates the Google Sheet 'Results' tab with scraped data.
    """
    print("Opening spreadsheet...")
    sheet = client.open_by_key(SHEET_KEY)
    results_worksheet = sheet.worksheet(RESULTS_TAB_NAME)
    
    # Get all values to map countries
    # Assuming 'Results' tab has Country in Column A, Gold in B, Silver in C, Bronze in D
    # Or strict headers. Let's read headers.
    
    data = results_worksheet.get_all_values()
    headers = data[0]
    
    # Simple mapping: find column indices
    try:
        col_country = headers.index('Country')
        col_gold = headers.index('Gold')
        col_silver = headers.index('Silver')
        col_bronze = headers.index('Bronze')
    except ValueError:
        print("Error: Could not find required headers (Country, Gold, Silver, Bronze) in Results tab.")
        return

    # Update Rows
    # We will build a batch update list for efficiency
    updates = []
    
    # Map scraped names to Sheet names (this is the tricky part usually)
    # For now, we assume close matching or user will fix mappings.
    # Add manual mapping for known discrepancies (e.g., AIN)
    name_corrections = {
        "Individual Neutral Athletes": "AIN",
        # Add others as discovered
    }
    
    # Normalize scraped data keys
    normalized_scraped = {}
    for k, v in scraped_data.items():
        # Remove weird characters if any
        clean_name = k.split('(')[0].strip() # "United States (USA)" -> "United States"
        if k in name_corrections:
            clean_name = name_corrections[k]
        elif clean_name in name_corrections: # Check clean version too
             clean_name = name_corrections[clean_name]
             
        normalized_scraped[clean_name] = v

    print(f"Processing {len(data)-1} countries in sheet...")
    for i, row in enumerate(data[1:], start=2): # Start at row 2 (1-indexed)
        country_name = row[col_country]
        if not country_name:
            continue
            
        # Fetch current values to check diff (optional, but good for logging)
        
        # Look for match
        # Try direct match
        match = normalized_scraped.get(country_name)
        
        if not match:
            # Try fuzzy or partial?
            # For now, if no match, we assume 0 or unchanged?
            # Better to assume unchanged if not found, OR 0 if we trust scrape is complete.
            # Given it's a "Results" tab, likely 0 default.
            # But let's log missing ones.
            # print(f"  No live data found for '{country_name}'")
            continue
            
        # Prepare Update
        # gspread uses (row, col)
        updates.append({'range': f"{gspread.utils.rowcol_to_a1(i, col_gold+1)}", 'values': [[match['Gold']]]})
        updates.append({'range': f"{gspread.utils.rowcol_to_a1(i, col_silver+1)}", 'values': [[match['Silver']]]})
        updates.append({'range': f"{gspread.utils.rowcol_to_a1(i, col_bronze+1)}", 'values': [[match['Bronze']]]})

    if updates:
        print(f"Pushing {len(updates)} cell updates to Google Sheets...")
        results_worksheet.batch_update(updates)
    else:
        print("No updates to push.")

    # Calculate and Update Flavor Text?
    # This is harder to automate without an event feed (API).
    # Wikipedia doesn't easily give "New rows since X".
    # Strategy: Just keep the Results accurate for now. 
    # Flavor text might remain manual or require a better data source (API).
    print("Results updated.")

def main():
    try:
        if 'GOOGLE_CREDENTIALS' not in os.environ:
             print("Error: GOOGLE_CREDENTIALS env var missing. Local testing requires this.")
             return
             
        client = get_google_sheet_client()
        medal_data = scrape_medal_data()
        
        if not medal_data:
            print("No medal data scraped (or empty table).")
            # We might still want to run to clear things to 0 if the games started?
            # Safe to skip if empty to avoid wiping data on accidental scrap failure.
        else:
            update_sheet(client, medal_data)
            
    except Exception as e:
        print(f"Critical Error: {e}")
        raise

if __name__ == "__main__":
    main()
