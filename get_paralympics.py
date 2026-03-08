import urllib.request
from bs4 import BeautifulSoup

url = 'https://en.wikipedia.org/wiki/2026_Winter_Paralympics'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
html = urllib.request.urlopen(req).read()
soup = BeautifulSoup(html, 'html.parser')

print(soup.title.text)

# Find the section for participating nations
span = soup.find(id='Participating_National_Paralympic_Committees')
if not span:
    span = soup.find(id='Participating_Nations')

if span:
    print("Found participating nations section.")
    lst = span.parent.find_next_sibling(['ul', 'div', 'table'])
    if lst:
        links = lst.find_all('a')
        countries = set()
        for link in links:
            if link.text and len(link.text) > 2:
                countries.add(link.text)
        print("Countries found:", ", ".join(sorted(countries)))
else:
    print("Could not find participating nations section.")
