import requests
from bs4 import BeautifulSoup
url = 'https://en.wikipedia.org/wiki/2026_Winter_Olympics_medal_table'
headers = {'User-Agent': 'Mozilla/5.0'}
response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.content, 'html.parser')
table = soup.find('table', class_='wikitable')
for row in table.find_all('tr'):
    print([col.get_text(strip=True) for col in row.find_all(['th', 'td'])])
