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
    table = soup.find('table', class_='wikitable')
    if not table:
        print("No table found with class 'wikitable'")
        return {}
    
    # Print table sample
    print(f"Table found. Inspecting first few rows...")

    medal_data = {}
    for i, row in enumerate(table.find_all('tr')):
        if i == 0:
            # Header row
            headers = [th.get_text(strip=True) for th in row.find_all(['th', 'td'])]
            print(f"Headers: {headers}")
            continue
            
        cols = row.find_all(['th', 'td'])
        col_texts = [c.get_text(strip=True) for c in cols]
        print(f"Row {i}: {col_texts}")
        
        if len(cols) < 5: continue
        try:
            # Helper to safely get text
            def get_text(idx): return cols[idx].get_text(strip=True)
            
            # Logic for typical Olympics table: Rank | Country | G | S | B | Total
            # Detect country column (usually 2nd, index 1)
            # The rank column 0 might be th or td.
            
            # Heuristic: Check column count.
            # If 6 columns: Rank | Country | G | S | B | Total
            # If 5 columns: Country | G | S | B | Total (Rank might be missing/merged)
            
            # The country usually has a flag+link.
            # Let's try flexible index.
            
            country_idx = 1
            if len(cols) == 5: country_idx = 0
            
            country_text = get_text(country_idx)
            country_name = country_text.split('(')[0].strip()
            
            # Numbers are usually last 4 columns: G, S, B, Total
            bronze = int(cols[-2].get_text(strip=True))
            silver = int(cols[-3].get_text(strip=True))
            gold = int(cols[-4].get_text(strip=True))
            
            medal_data[country_name] = {'Gold': gold, 'Silver': silver, 'Bronze': bronze}
        except (ValueError, IndexError) as e:
            print(f"  Skipping row {i} due to error: {e}")
            continue
            
    return medal_data

if __name__ == "__main__":
    data = scrape_medal_counts()
    print("\n--- Scraped Data ---")
    for k, v in data.items():
        print(f"{k}: {v}")
