import requests
from bs4 import BeautifulSoup

WIKIPEDIA_URL_COUNTS = 'https://en.wikipedia.org/wiki/2026_Winter_Olympics_medal_table'

def scrape_medal_counts():
    print(f"Scraping Counts: {WIKIPEDIA_URL_COUNTS}...")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        response = requests.get(WIKIPEDIA_URL_COUNTS, headers=headers)
        response.raise_for_status()
    except Exception as e:
        print(f"Error scraping counts: {e}")
        return {}

    soup = BeautifulSoup(response.content, 'html.parser')
    tables = soup.find_all('table', class_='wikitable')
    print(f"Found {len(tables)} wikitables.")
    
    for t_idx, table in enumerate(tables):
        print(f"\n--- Table {t_idx} ---")
        rows = table.find_all('tr')
        if not rows: continue
        
        # Print header
        header_row = rows[0]
        headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
        print(f"Headers: {headers}")
        
        # Check first few rows
        for i, row in enumerate(rows[1:6]):
            cols = [c.get_text(strip=True) for c in row.find_all(['th', 'td'])]
            print(f"Row {i}: {cols}")
            
    # Specific check for Netherlands
    print("\n--- Searching for 'Netherlands' ---")
    if "Netherlands" in soup.get_text():
        print("'Netherlands' FOUND in page text.")
    else:
        print("'Netherlands' NOT FOUND in page text.")
        
    if "Korea" in soup.get_text():
        print("'Korea' FOUND in page text.")

    # Run the scraping logic on ALL tables to see if we find them
    print("\n--- Re-running scraping logic on ALL tables ---")
    medal_data = {}
    for t_idx, table in enumerate(tables):
        # same logic as main.py (simplified)
        for row in table.find_all('tr')[1:]:
            cols = row.find_all(['th', 'td'])
            if len(cols) < 5: continue
            try:
                def get_text(idx): return cols[idx].get_text(strip=True)
                country_idx = 1
                if len(cols) == 5: country_idx = 0
                
                c_text = get_text(country_idx)
                c_name = c_text.split('(')[0].replace('*', '').strip()
                
                # Check knowns
                if "Netherlands" in c_name or "Korea" in c_name:
                    print(f"MATCH in Table {t_idx}: {c_name} -> {cols[-1].get_text(strip=True)} Total")
                    
                g = int(cols[-4].get_text(strip=True)) # Gold
                medal_data[c_name] = g # Just dummy
            except: pass
            
    return medal_data

    return medal_data

def scrape_medal_details():
    WIKIPEDIA_URL_DETAILS = 'https://en.wikipedia.org/wiki/List_of_2026_Winter_Olympics_medal_winners'
    print(f"Scraping Details: {WIKIPEDIA_URL_DETAILS}...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(WIKIPEDIA_URL_DETAILS, headers=headers)
        response.raise_for_status()
    except Exception as e:
        print(f"Error scraping details: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    details = []
    
    tables = soup.find_all('table', class_='wikitable')
    print(f"Found {len(tables)} detailed wikitables.")
    
    for t_idx, table in enumerate(tables):
        # Heuristic check for medalist table
        header_row = table.find('tr')
        if not header_row: continue
        headers_text = [th.get_text(strip=True).lower() for th in header_row.find_all(['th'])]
        
        # Checking for Gold/Silver/Bronze columns
        if not any(k in str(headers_text) for k in ['gold', 'silver', 'bronze']):
             continue

        rows = table.find_all('tr')
        print(f"  Table {t_idx}: {len(rows)} rows. Headers: {headers_text}")
        
        for row in rows:
            cols = row.find_all(['th', 'td'])
            
            # Skip header
            row_text = row.get_text(strip=True).lower()
            if "gold" in row_text and "silver" in row_text: continue
            
            if len(cols) < 4: continue 
            
            try:
                # Mock Parsing Logic from main.py
                event_cell = cols[0]
                event_name = event_cell.get_text(" ", strip=True).replace("details", "").strip()
                
                def parse_medalist(cell, color):
                    text = cell.get_text(" ", strip=True) 
                    if not text: return
                    
                    # Logic 
                    country = "Unknown"
                    athlete = text
                    
                    # Try finding country via flag/link (Same logic as main.py)
                    links = cell.find_all('a')
                    for link in links:
                        title = link.get('title', '')
                        if " at the " in title:
                            country = title.split(" at the ")[0]
                            athlete = athlete.replace(country, "").strip() # naive cleanup
                            break
                    
                    # Store
                    details.append({
                        'Event': event_name,
                        'Medal': color,
                        'Athlete': athlete,
                        'Country': country
                    })

                if len(cols) >= 2: parse_medalist(cols[1], 'Gold')
                if len(cols) >= 3: parse_medalist(cols[2], 'Silver')
                if len(cols) >= 4: parse_medalist(cols[3], 'Bronze')
                
            except Exception: continue
            
    return details

if __name__ == "__main__":
    # Counts
    # scrape_medal_counts() # Skip for now
    
    # Details
    det = scrape_medal_details()
    print(f"\nFound {len(det)} detail entries.")
    
    print("\n--- Checking for Target Countries ---")
    targets = ["Netherlands", "Korea", "States"]
    for d in det:
        c = d['Country']
        for t in targets:
            if t in c:
                print(f"MATCH: {d}")
