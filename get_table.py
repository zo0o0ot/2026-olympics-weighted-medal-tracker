import urllib.request
from bs4 import BeautifulSoup
import re

url = 'https://en.wikipedia.org/wiki/2022_Winter_Paralympics'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req).read()
soup = BeautifulSoup(html, 'html.parser')

DRAFTED = ["Germany", "Austria", "France", "Switzerland", "Great Britain", "Estonia", "Greece", 
           "Norway", "Sweden", "Japan", "China", "South Korea", "Czech Republic", "Spain",
           "Canada", "United States", "Italy", "Australia", "Finland", "Russia", "Belarus", "Denmark",
           "Netherlands", "Poland", "New Zealand", "Slovenia", "Belgium", "Croatia", "Chinese Taipei",
           "USA", "RPC", "ROC", "AIN"]
DRAFTED = set(c.lower() for c in DRAFTED)

# Find all links in the page that might look like countries with numbers next to them
# Let's just find the text of the page and extract Country (Number)
# But it's easier to just find the list items that contain a link to a country
undrafted = {}
for li in soup.find_all('li'):
    a = li.find('a')
    if a and a.text:
        text = li.text.strip().replace('\xa0', ' ')
        match = re.search(r'^([A-Za-z\s]+)(?:\[.*?\])?\s*\((\d+)\)$', text)
        if match:
            country = match.group(1).strip()
            count = int(match.group(2))
            if country.lower() not in DRAFTED and "RPC" not in country:
                undrafted[country] = count

sorted_undrafted = sorted(undrafted.items(), key=lambda x: x[1], reverse=True)
for c, count in sorted_undrafted[:15]:
    print(f"{c}: {count} athletes")
