import re

wiki_countries = [
    "Andorra", "Argentina", "Armenia", "Australia", "Austria", "Azerbaijan", "Belarus", "Belgium", "Bosnia and Herzegovina", "Brazil", "Bulgaria", "Canada", "Chile", "China", "Croatia", "Czech Republic", "Denmark", "El Salvador", "Estonia", "Finland", "France", "Georgia", "Germany", "Great Britain", "Greece", "Haiti", "Hungary", "Iceland", "Iran", "Israel", "Italy", "Japan", "Kazakhstan", "Latvia", "Liechtenstein", "Lithuania", "Mexico", "Mongolia", "Montenegro", "Netherlands", "New Zealand", "North Macedonia", "Norway", "Poland", "Portugal", "Puerto Rico", "Romania", "Russia", "Serbia", "Slovakia", "Slovenia", "South Korea", "Spain", "Sweden", "Switzerland", "Ukraine", "United States", "Uzbekistan"
]

DRAFTED_TEAMS = {
    "Maya": ["Germany", "Austria", "France", "Switzerland", "Great Britain", "Estonia", "Greece"],
    "Ross": ["Norway", "Sweden", "Japan", "China", "South Korea", "Czech Republic", "Spain"],
    "Mom": ["Canada", "USA", "Italy", "Australia", "Finland", "AIN", "Denmark"],
    "Drew": ["Netherlands", "Poland", "New Zealand", "Slovenia", "Belgium", "Croatia", "Chinese Taipei"]
}

COUNTRY_NAME_MAP = {
    "USA": "United States",
    "AIN": "Individual Neutral Athletes",
    "Republic of Korea": "South Korea",
    "United Kingdom": "Great Britain",
    "People's Republic of China": "China",
    "Russian Olympic Committee": "Russia",
    "Czechia": "Czech Republic",
    "The Netherlands": "Netherlands",
    "PR China": "China"
}

missing = {}
for player, countries in DRAFTED_TEAMS.items():
    player_missing = []
    for c in countries:
        c_check = COUNTRY_NAME_MAP.get(c, c)
        if c_check == "Individual Neutral Athletes":
            if "Russia" not in wiki_countries and "Belarus" not in wiki_countries:
                player_missing.append(c)
        elif c_check not in wiki_countries:
            player_missing.append(c)
    if player_missing:
        missing[player] = player_missing

print("Missing Countries:", missing)
