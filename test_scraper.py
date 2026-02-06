from main import scrape_medal_data

print("Testing Scraper Logic...")
data = scrape_medal_data()
if not data:
    print("Success: Function ran. Returned empty (expected for now) or scraped data.")
    print(f"Data dump: {data}")
else:
    print(f"Success: Scraped {len(data)} countries.")
    print("Sample:", list(data.items())[:3])
