import urllib.request
from bs4 import BeautifulSoup

url = 'https://en.wikipedia.org/wiki/2026_Winter_Paralympics_medal_table'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req).read()
soup = BeautifulSoup(html, 'html.parser')

tables = soup.find_all('table', {'class': 'wikitable sortable'})
for i, table in enumerate(tables):
    print(f"Table {i}:")
    for row in table.find_all('tr')[:3]:
        cols = row.find_all(['td', 'th'])
        print([c.text.strip() for c in cols])
        
