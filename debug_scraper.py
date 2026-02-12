import json
from main import scrape_medal_counts, scrape_medal_details, validate_data

# --- Debug Scraper ---
# This script directly uses the production scrapers from main.py
# ensuring 100% consistency with the live app.

if __name__ == "__main__":
    print("=== DEBUGGING MEDAL COUNTS ===")
    counts = scrape_medal_counts()
    print(f"Scraped {len(counts)} countries.")
    
    is_valid, msg = validate_data(counts, "counts")
    print(f"Validation Status: {'PASS' if is_valid else 'FAIL'}")
    if not is_valid: print(f"Reason: {msg}")
    
    print("\nSample Data (Top 5):")
    for k in list(counts.keys())[:5]:
        print(f"{k}: {counts[k]}")

    print("\n=== DEBUGGING MEDAL DETAILS ===")
    details = scrape_medal_details()
    print(f"Scraped {len(details)} detail rows.")
    
    is_valid_d, msg_d = validate_data(details, "details")
    print(f"Validation Status: {'PASS' if is_valid_d else 'FAIL'}")
    if not is_valid_d: print(f"Reason: {msg_d}")
    
    print("\nSample Details (First 3):")
    for d in details[:3]:
        print(d)
        
    print("\n=== DEBUGGING FINISHED ===")

