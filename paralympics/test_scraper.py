import urllib.request
from bs4 import BeautifulSoup

url = 'https://en.wikipedia.org/wiki/2026_Winter_Paralympics_medal_table'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    html = urllib.request.urlopen(req).read()
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', {'class': 'wikitable sortable'})
    if table:
        for row in table.find_all('tr'):
            cols = row.find_all(['td', 'th'])
            print([c.text.strip() for c in cols])
    else:
        print("Table not found")
except Exception as e:
    print(f"Error: {e}")
