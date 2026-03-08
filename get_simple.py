import urllib.request
from bs4 import BeautifulSoup
import re

url = 'https://en.wikipedia.org/wiki/2022_Winter_Paralympics'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req).read()
soup = BeautifulSoup(html, 'html.parser')

DRAFTED = {"Germany", "Austria", "France", "Switzerland", "Great Britain", "Estonia", "Greece", 
           "Norway", "Sweden", "Japan", "China", "South Korea", "Czech Republic", "Spain",
           "Canada", "United States", "Italy", "Australia", "Finland", "Russia", "Belarus", "Denmark",
           "Netherlands", "Poland", "New Zealand", "Slovenia", "Belgium", "Croatia", "Chinese Taipei",
           "USA", "RPC", "ROC", "AIN"}
DRAFTED = {c.lower() for c in DRAFTED}

known_countries = {"Andorra", "Argentina", "Armenia", "Australia", "Austria", "Azerbaijan", "Belarus", "Belgium", "Bosnia and Herzegovina", "Brazil", "Bulgaria", "Canada", "Chile", "China", "Croatia", "Czech Republic", "Denmark", "El Salvador", "Estonia", "Finland", "France", "Georgia", "Germany", "Great Britain", "Greece", "Haiti", "Hungary", "Iceland", "Iran", "Israel", "Italy", "Japan", "Kazakhstan", "Latvia", "Liechtenstein", "Lithuania", "Mexico", "Mongolia", "Montenegro", "Netherlands", "New Zealand", "North Macedonia", "Norway", "Poland", "Portugal", "Puerto Rico", "Romania", "Russia", "Serbia", "Slovakia", "Slovenia", "South Korea", "Spain", "Sweden", "Switzerland", "Ukraine", "United States", "Uzbekistan"}

undrafted_sizes = {}
for c in known_countries:
    if c.lower() not in DRAFTED:
        # search the HTML directly for "CountryName (Number)"
        match = re.search(r'\b' + re.escape(c) + r'[^<]{0,5}\((\d+)\)', html.decode('utf-8', errors='ignore'))
        if match:
            undrafted_sizes[c] = int(match.group(1))

sorted_undrafted = sorted(undrafted_sizes.items(), key=lambda x: x[1], reverse=True)
for c, count in sorted_undrafted[:10]:
    print(f"{c}: {count} athletes")
