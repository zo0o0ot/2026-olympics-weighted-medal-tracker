import requests
from bs4 import BeautifulSoup
import json

url = "https://en.wikipedia.org/wiki/2026_Winter_Olympics"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

try:
    resp = requests.get(url, headers=headers)
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # Try to find the Participating NOCs table or list
    noc_data = {}
    
    # Often NOCs are in a ul/li structure with text like "United States (233)"
    # or in a table. We can just look for "(233)" to see where it lives.
    
    # Just grab all list items and try to parse "Country (number)"
    # Or look for tables under "Participating National Olympic Committees"
    found_us = False
    for span in soup.find_all('span', id=['Participating_National_Olympic_Committees', 'Participating_NOCs']):
        parent = span.parent
        # Look for the list after the header
        sib = parent.find_next_sibling()
        while sib and sib.name not in ['h2', 'h3']:
            if sib.name == 'ul' or sib.name == 'table':
                print("Found a structure:", sib.name)
            sib = sib.find_next_sibling()

    print("Checking text for '233'...")
    tags_with_233 = soup.find_all(string=lambda t: t and '233' in t)
    for tag in tags_with_233:
        print("Found 233 in tag:", tag.parent.name, "->", tag.strip()[:100])

except Exception as e:
    print(f"Error: {e}")
