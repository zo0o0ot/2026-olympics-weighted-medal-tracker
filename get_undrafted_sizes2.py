import urllib.request
from bs4 import BeautifulSoup
import re

url = 'https://en.wikipedia.org/wiki/2022_Winter_Paralympics'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
html = urllib.request.urlopen(req).read()
soup = BeautifulSoup(html, 'html.parser')

DRAFTED = ["Germany", "Austria", "France", "Switzerland", "Great Britain", "Estonia", "Greece", 
           "Norway", "Sweden", "Japan", "China", "South Korea", "Czech Republic", "Spain",
           "Canada", "United States", "Italy", "Australia", "Finland", "Russia", "Belarus", "Denmark",
           "Netherlands", "Poland", "New Zealand", "Slovenia", "Belgium", "Croatia", "Chinese Taipei",
           "USA", "RPC", "ROC", "AIN"]
DRAFTED = [c.lower() for c in DRAFTED]

span = soup.find(id='Participating_National_Paralympic_Committees')
if span:
    found = False
    for node in span.parent.find_all_next(['ul', 'div']):
        for li in node.find_all('li'):
            text = li.text.strip().replace('\xa0', ' ')
            match = re.search(r'([A-Za-z\s]+)(?:\[.*?\])?\s*\((\d+)\)', text)
            if match:
                country = match.group(1).strip()
                count = int(match.group(2))
                if country.lower() not in DRAFTED and "RPC" not in country:
                    print(f"{country}: {count}")
                found = True
        if found:
            break
