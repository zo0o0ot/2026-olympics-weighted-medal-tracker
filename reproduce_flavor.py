# --- Copied Logic from main.py ---
COUNTRY_NAME_MAP = {
    "United States": "USA",
    "South Korea": "Republic of Korea",
    "Great Britain": "United Kingdom",
    "China": "People's Republic of China",
    "ROC": "Russian Olympic Committee",
    "Czech Republic": "Czechia",
    "Netherlands": "Netherlands", 
    "The Netherlands": "Netherlands"
}

def normalize_country_name(name):
    """
    Normalizes a country name for fuzzy matching.
    """
    if not name: return ""
    name = name.lower()
    for prefix in ["the ", "republic of ", "people's republic of "]:
        if name.startswith(prefix):
            name = name[len(prefix):]
    return name.strip()

# Mock Team Map (Draft Tab)
team_map = {
    "Team A": ["The Netherlands", "Norway"],
    "Team B": ["South Korea", "China"],
    "Team C": ["USA"]
}

# Mock Details (Scraped Data)
details = [
    {'Event': '1000m', 'Medal': 'Gold', 'Athlete': 'Jutta Leerdam', 'Country': 'Netherlands'},
    {'Event': 'Slalom', 'Medal': 'Silver', 'Athlete': 'Kim', 'Country': 'South Korea'},
    {'Event': 'Hockey', 'Medal': 'Gold', 'Athlete': 'Team USA', 'Country': 'United States'}
]

# Mock Existing Data (Flavor Tab)
# Format: Date, Country, Medal, Event, Athlete, Team
# Case 1: Partial match?
# Case 2: Exact match?
existing_rows = [
    ['2026-02-06', 'Netherlands', 'Gold', '1000m', 'Jutta Leerdam', 'Team A'],
    ['2026-02-07', 'South Korea', 'Silver', 'Slalom', 'Kim', 'Team B']
]

existing_sigs = set()
for row in existing_rows:
    if len(row) >= 5:
         # Simulating main.py logic: row[3] is Event, row[2] is Medal, row[4] is Athlete
         # Wait! row[3] in sheet is Event?
         # Sheet Headers: Date, Country, Medal, Event, Athlete, Team
         # Indices:       0     1        2      3      4        5
         
         # main.py logic:
         # sig = f"{row[3]}_{row[2]}_{row[4]}" 
         # Event_Medal_Athlete
         
         sig = f"{row[3]}_{row[2]}_{row[4]}"
         print(f"Loaded Existing Sig: {sig}")
         existing_sigs.add(sig)

print("\n--- Testing Signature Detection ---")

for d in details:
    sig = f"{d['Event']}_{d['Medal']}_{d['Athlete']}"
    print(f"Checking New Sig: {sig}")
    
    if sig in existing_sigs:
        print(f"  BLOCKED: Signature already exists.")
    else:
        print(f"  PASS: New entry detected.")
