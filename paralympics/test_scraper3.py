import urllib.request
from bs4 import BeautifulSoup

url = 'https://en.wikipedia.org/wiki/2026_Winter_Paralympics_medal_table'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req).read()
soup = BeautifulSoup(html, 'html.parser')

tables = soup.find_all('table')
for i, table in enumerate(tables):
    rows = table.find_all('tr')
    if rows:
        cols = rows[0].find_all(['td', 'th'])
        headers = [c.text.strip() for c in cols]
        print(f"Table {i} headers: {headers}")
        if 'Gold' in headers or 'Silver' in headers or 'Bronze' in headers:
            print("Found potential medal table.")
            for row in rows[1:3]:
                 print([c.text.strip() for c in row.find_all(['td', 'th'])])
