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
undrafted_sizes = {}

span = soup.find(id='Participating_National_Paralympic_Committees')
if span and span.parent:
    node = span.parent.find_next_sibling()
    while node and node.name not in ['ul', 'div', 'table']:
        node = node.find_next_sibling()
    
    if node:
        for li in node.find_all('li'):
            text = li.text
            match = re.search(r'([A-Za-z\s\w]+)\s*\((\d+)\)', text.strip().replace('\xa0', ' '))
            if match:
                country = match.group(1).strip()
                count = int(match.group(2))
                if country.lower() not in DRAFTED and "RPC" not in country:
                    undrafted_sizes[country] = count

sorted_undrafted = sorted(undrafted_sizes.items(), key=lambda x: x[1], reverse=True)
for c, count in sorted_undrafted[:15]:
    print(f"{c}: {count} athletes")
