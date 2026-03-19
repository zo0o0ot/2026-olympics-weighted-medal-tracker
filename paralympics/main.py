import csv
import json
import os
import math
import urllib.request
from bs4 import BeautifulSoup
import re
import os
import math

# --- Configuration & Mappings ---

DRAFTED_TEAMS = {
    "Maya": ["Germany", "Austria", "France", "Switzerland", "Great Britain", "Estonia", "Greece", "Ukraine"],
    "Ross": ["Norway", "Sweden", "Japan", "China", "South Korea", "Czech Republic", "Spain", "Brazil"],
    "Mom": ["Canada", "USA", "Italy", "Australia", "Finland", "AIN", "Denmark", "Kazakhstan"],
    "Drew": ["Netherlands", "Poland", "New Zealand", "Slovenia", "Belgium", "Croatia", "Slovakia", "Latvia"]
}

COUNTRY_NAME_MAP = {
    "United States": "USA",
    "United States of America": "USA",
    "AIN": "Individual Neutral Athletes",
    "Republic of Korea": "South Korea",
    "United Kingdom": "Great Britain",
    "People's Republic of China": "China",
    "Russian Olympic Committee": "Russia",
    "Czechia": "Czech Republic",
    "The Netherlands": "Netherlands",
    "PR China": "China"
}

# Build a normalized lookup map for canonical country names
NORMALIZED_COUNTRY_MAP = {}
for raw_name, canonical in COUNTRY_NAME_MAP.items():
    NORMALIZED_COUNTRY_MAP[raw_name.lower().strip()] = canonical.lower().strip()

def normalize_country_name(name):
    """Normalize for fuzzy matching and apply canonical mappings."""
    if not name: return ""
    name = name.lower().strip()
    for prefix in ["the ", "republic of ", "people's republic of "]:
        if name.startswith(prefix):
            name = name[len(prefix):]
    name = name.strip()
    # Apply canonical mapping if available
    if name in NORMALIZED_COUNTRY_MAP:
        return NORMALIZED_COUNTRY_MAP[name]
    return name

# --- Core Logic ---

def get_paralympic_hardware_multiplier(event_name):
    """
    Returns the physical number of medals placed around necks for a single event win
    in the Winter Paralympics.
    """
    if not event_name: return 1
    name = event_name.lower()
    
    # Para Ice Hockey: Mixed teams, typically 17 players on roster
    if "hockey" in name:
        return 17
        
    # Wheelchair Curling: Mixed teams, typically 5 players on roster
    if "curling" in name:
        return 5
        
    # Relays (Cross-Country Skiing, etc.)
    if "relay" in name:
        return 4
        
    # Pairs / Guides (Visually impaired athletes often ski with a guide who also gets a medal)
    # This might require more advanced parsing depending on how Wikipedia structures it,
    # but for now, we assume standard singles unless "guide" or "pair" is explicitly mapped.
    # Note: In Paralympics, guides DO receive medals. 
    # If the event implies B1-B3 visually impaired, we could double it, but we'll stick to text-based for now.
    if "visually impaired" in name:
        return 2  # Athlete + Guide both get medals
        
    return 1

def scrape_event_results():
    """
    Scrapes individual event results to calculate hardware (physical medals) properly.
    Returns a dict mapping normalized country names to their hardware counts by medal type.
    """
    event_hardware = {}  # {country: {"gold_hw": X, "silver_hw": Y, "bronze_hw": Z}}

    def add_hardware(country, medal_type, multiplier):
        """Helper to add hardware to a country's tally."""
        country = normalize_country_name(country)
        if country not in event_hardware:
            event_hardware[country] = {"gold_hw": 0, "silver_hw": 0, "bronze_hw": 0}
        event_hardware[country][medal_type] += multiplier

    # Known country names for validation
    KNOWN_COUNTRIES = {
        'australia', 'austria', 'belarus', 'belgium', 'brazil', 'canada', 'chile',
        'china', 'croatia', 'czech republic', 'czechia', 'denmark', 'estonia',
        'finland', 'france', 'germany', 'great britain', 'greece', 'hungary',
        'iceland', 'ireland', 'israel', 'italy', 'japan', 'kazakhstan', 'latvia',
        'liechtenstein', 'lithuania', 'mexico', 'mongolia', 'montenegro',
        'netherlands', 'new zealand', 'north korea', 'north macedonia', 'norway',
        'poland', 'portugal', 'romania', 'russia', 'serbia', 'slovakia', 'slovenia',
        'south korea', 'spain', 'sweden', 'switzerland', 'ukraine',
        'united kingdom', 'united states', 'usa', 'uzbekistan'
    }

    def extract_country_from_cell(cell):
        """Extract country name from a medal cell."""
        # Try to find a country link first
        for a_tag in cell.find_all('a'):
            href = a_tag.get('href', '')
            if 'at_the' in href and 'Paralympics' in href:
                # Match everything before "_at_the"
                match = re.search(r'/wiki/(.+?)_at_the', href)
                if match:
                    country = match.group(1).replace('_', ' ')
                    return country
        # Fallback: get first line of text (usually country name)
        text = cell.get_text().strip()
        if text:
            # Country name is usually the first word/line before player names
            first_line = text.split('\n')[0].strip()
            # Remove any bracketed content
            first_line = re.sub(r'\[.*?\]', '', first_line).strip()
            # Check if it's a known country
            if first_line.lower() in KNOWN_COUNTRIES:
                return first_line
        return None

    # List of sport pages to scrape for event results
    sport_configs = [
        ('https://en.wikipedia.org/wiki/Alpine_skiing_at_the_2026_Winter_Paralympics', 1),
        ('https://en.wikipedia.org/wiki/Biathlon_at_the_2026_Winter_Paralympics', 1),
        ('https://en.wikipedia.org/wiki/Cross-country_skiing_at_the_2026_Winter_Paralympics', 1),  # Relays handled specially
        ('https://en.wikipedia.org/wiki/Para_ice_hockey_at_the_2026_Winter_Paralympics', 17),
        ('https://en.wikipedia.org/wiki/Para_snowboard_at_the_2026_Winter_Paralympics', 1),
        ('https://en.wikipedia.org/wiki/Wheelchair_curling_at_the_2026_Winter_Paralympics', 5),  # Team events
    ]

    for sport_url, default_multiplier in sport_configs:
        try:
            req = urllib.request.Request(sport_url, headers={'User-Agent': 'Mozilla/5.0'})
            html = urllib.request.urlopen(req).read()
            soup = BeautifulSoup(html, 'html.parser')

            # Find tables with "Event | Gold | Silver | Bronze" structure
            tables = soup.find_all('table', class_=re.compile(r'wikitable'))

            for table in tables:
                rows = table.find_all('tr')
                if not rows:
                    continue

                # Check header row for medal columns
                header = rows[0]
                header_cells = [th.get_text().strip().lower() for th in header.find_all(['th', 'td'])]

                # Find column indices for medals
                gold_idx = silver_idx = bronze_idx = -1
                for i, h in enumerate(header_cells):
                    if 'gold' in h:
                        gold_idx = i
                    elif 'silver' in h:
                        silver_idx = i
                    elif 'bronze' in h:
                        bronze_idx = i

                if gold_idx == -1 or silver_idx == -1 or bronze_idx == -1:
                    continue

                # Process data rows
                for row in rows[1:]:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) <= max(gold_idx, silver_idx, bronze_idx):
                        continue

                    # Determine multiplier based on event name
                    event_cell = cells[0].get_text().lower() if cells else ""
                    if 'relay' in event_cell:
                        multiplier = 4
                    elif 'double' in event_cell:
                        multiplier = 2  # Mixed doubles curling
                    elif 'hockey' in sport_url.lower():
                        multiplier = 17
                    elif 'curling' in sport_url.lower() and 'team' in event_cell:
                        multiplier = 5
                    elif any(x in event_cell for x in ['visually impaired', 'b1', 'b2', 'b3', 'vi']):
                        multiplier = 2  # Athlete + guide
                    else:
                        multiplier = default_multiplier

                    # Extract countries from medal cells
                    gold_country = extract_country_from_cell(cells[gold_idx]) if gold_idx < len(cells) else None
                    silver_country = extract_country_from_cell(cells[silver_idx]) if silver_idx < len(cells) else None
                    bronze_country = extract_country_from_cell(cells[bronze_idx]) if bronze_idx < len(cells) else None

                    if gold_country:
                        add_hardware(gold_country, "gold_hw", multiplier)
                    if silver_country:
                        add_hardware(silver_country, "silver_hw", multiplier)
                    if bronze_country:
                        add_hardware(bronze_country, "bronze_hw", multiplier)

        except Exception as e:
            print(f"Failed to fetch {sport_url}: {e}")
            continue

    return event_hardware

def scrape_wikipedia_data():
    """
    Scrapes the 2026 Winter Paralympics page (or 2022 as fallback if 2026 is empty)
    to get participant counts and the medal table.
    For now, since 2026 hasn't started, we'll build the robust parser.
    """
    url = 'https://en.wikipedia.org/wiki/2026_Winter_Paralympics'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        html = urllib.request.urlopen(req).read()
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return {}, [], {}

    soup = BeautifulSoup(html, 'html.parser')
    participants = {}

    # Extract Participants
    span = soup.find(id='Participating_National_Paralympic_Committees')
    if not span:
        span = soup.find(id='Participating_Nations')

    if span:
        # Find the list of countries following this span
        for node in span.parent.find_all_next(['ul', 'div']):
            found_any = False
            for li in node.find_all('li'):
                text = li.text.strip().replace('\xa0', ' ')
                # Match Country (Number)
                match = re.search(r'([A-Za-z\s\w]+)(?:\[.*?\])?\s*\((\d+)\)', text)
                if match:
                    country = normalize_country_name(match.group(1).strip())
                    count = int(match.group(2))
                    participants[country] = count
                    found_any = True
            if found_any:
                break

    # Scrape event-level results for hardware calculation
    print("Scraping event results for hardware calculation...")
    event_hardware = scrape_event_results()

    # Extract Medal Table
    medals = []

    # Fetch dedicated medal table page
    medal_url = 'https://en.wikipedia.org/wiki/2026_Winter_Paralympics_medal_table'
    medal_req = urllib.request.Request(medal_url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        medal_html = urllib.request.urlopen(medal_req).read()
        medal_soup = BeautifulSoup(medal_html, 'html.parser')

        # Look for the main medal table by checking headers
        tables = medal_soup.find_all('table')
        target_table = None
        for tbl in tables:
            first_row = tbl.find('tr')
            if first_row:
                headers = [th.text.strip().lower() for th in first_row.find_all(['th', 'td'])]
                if 'gold' in headers and ('npc' in headers or 'nation' in headers) and 'total' in headers:
                    target_table = tbl
                    break

        if target_table:
            for row in target_table.find_all('tr')[1:]:
                cols = row.find_all(['td', 'th'])
                if len(cols) >= 5:
                    # Country name is usually in the second column (index 1) or first if no rank
                    # Let's try to find an <a> tag in the row.
                    a_tag = None
                    for col in cols[:3]:
                        a = col.find('a')
                        if a and len(a.text.strip()) > 2 and "Paralympics" not in a.text:
                            a_tag = a
                            break

                    if a_tag:
                        country_raw = a_tag.text.strip()
                        country = normalize_country_name(country_raw)

                        try:
                            # We can just take the last 4 columns (G, S, B, Total)
                            g = int(cols[-4].text.strip() or 0)
                            s = int(cols[-3].text.strip() or 0)
                            b = int(cols[-2].text.strip() or 0)

                            # Calculate hardware from event-level data if available
                            hw_data = event_hardware.get(country, {})
                            gold_hw = hw_data.get("gold_hw", 0)
                            silver_hw = hw_data.get("silver_hw", 0)
                            bronze_hw = hw_data.get("bronze_hw", 0)
                            total_hw = gold_hw + silver_hw + bronze_hw

                            # Fall back to medal count if no event data
                            if total_hw == 0:
                                gold_hw = g
                                silver_hw = s
                                bronze_hw = b
                                total_hw = g + s + b

                            medals.append({
                                "CountryRaw": country_raw,
                                "Country": country,
                                "Gold": g,
                                "Silver": s,
                                "Bronze": b,
                                "GoldHW": gold_hw,
                                "SilverHW": silver_hw,
                                "BronzeHW": bronze_hw,
                                "Hardware": total_hw
                            })
                        except (ValueError, IndexError):
                            pass
    except Exception as e:
        print(f"Failed to fetch {medal_url}: {e}")

    return participants, medals, event_hardware

def load_participant_counts(filepath="data/participants.json"):
    """
    Loads raw participant counts for each country.
    Returns: dict mapping normalized country names to integer participant counts.
    """
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: {filepath} not found. Returning empty participant data.")
        return {}

def calculate_dynamic_multipliers(participants_data):
    """
    Finds the maximum participant count across all nations, then calculates
    the multiplier for each country: (Max Participants / Country Participants).
    """
    if not participants_data:
        return {}
        
    max_participants = max(participants_data.values())
    print(f"Max Delegation Size found: {max_participants}")
    
    multipliers = {}
    for country, count in participants_data.items():
        if count > 0:
            multipliers[country] = max_participants / float(count)
        else:
            multipliers[country] = 1.0 # Fallback
            
    return multipliers, max_participants

def generate_reports():
    """
    Main execution pipeline.
    """
    # 1. Scrape live Wiki data
    print("Scraping Wikipedia for participants and medals...")
    participants, medals, event_hardware = scrape_wikipedia_data()

    # Optional load from local JSON if scraping fails
    if not participants:
        print("Using local participants data fallback...")
        participants = load_participant_counts()

    # Consolidate participants with same normalized names
    consolidated_participants = {}
    for country, count in participants.items():
        norm = normalize_country_name(country)
        if norm in consolidated_participants:
            consolidated_participants[norm] += count
        else:
            consolidated_participants[norm] = count
    participants = consolidated_participants

    # Consolidate medals with same normalized names
    consolidated_medals = {}
    for m in medals:
        norm = m['Country']
        if norm in consolidated_medals:
            consolidated_medals[norm]['Gold'] += m['Gold']
            consolidated_medals[norm]['Silver'] += m['Silver']
            consolidated_medals[norm]['Bronze'] += m['Bronze']
            consolidated_medals[norm]['GoldHW'] += m.get('GoldHW', m['Gold'])
            consolidated_medals[norm]['SilverHW'] += m.get('SilverHW', m['Silver'])
            consolidated_medals[norm]['BronzeHW'] += m.get('BronzeHW', m['Bronze'])
            consolidated_medals[norm]['Hardware'] += m['Hardware']
        else:
            consolidated_medals[norm] = {
                'CountryRaw': m['CountryRaw'],
                'Country': norm,
                'Gold': m['Gold'],
                'Silver': m['Silver'],
                'Bronze': m['Bronze'],
                'GoldHW': m.get('GoldHW', m['Gold']),
                'SilverHW': m.get('SilverHW', m['Silver']),
                'BronzeHW': m.get('BronzeHW', m['Bronze']),
                'Hardware': m['Hardware']
            }
    medals = list(consolidated_medals.values())
        
    # 2. Build multipliers
    multipliers, max_participants = calculate_dynamic_multipliers(participants)
    
    # 3. Aggregate Player Scores and Generate Output Data
    country_outputs = []
    
    # Pre-populate all drafted and participating countries into our main table
    all_countries_set = set(participants.keys())
    for medals_row in medals:
        all_countries_set.add(medals_row['Country'])
    for player, teams in DRAFTED_TEAMS.items():
        for team in teams:
            all_countries_set.add(normalize_country_name(team))
            
    for c_norm in all_countries_set:
        c_raw = c_norm.title()
        
        # Look for reverse mapping for pretty print
        for pretty, maps_to in COUNTRY_NAME_MAP.items():
            if normalize_country_name(pretty) == c_norm or normalize_country_name(maps_to) == c_norm:
                c_raw = pretty
                
        # Get raw stats
        p_count = participants.get(c_norm, 1) # default to 1 if unknown to avoid div zero
        mult = multipliers.get(c_norm, float(max_participants) if max_participants > 0 else 1.0)
        
        # Find medaling data
        g = s = b = total_hw = gold_hw = silver_hw = bronze_hw = 0
        for m in medals:
            if m['Country'] == c_norm:
                c_raw = m['CountryRaw'] # Upgrade to exact Wikipedia casing
                g = m['Gold']
                s = m['Silver']
                b = m['Bronze']
                gold_hw = m.get('GoldHW', g)
                silver_hw = m.get('SilverHW', s)
                bronze_hw = m.get('BronzeHW', b)
                total_hw = m['Hardware']
                break

        # Calculate medal counts
        total_medals = g + s + b
        weighted_medals = (g * 3) + (s * 2) + (b * 1)

        # Calculate hardware counts (raw = physical medals, weighted = gold*3 + silver*2 + bronze*1)
        raw_hardware = total_hw  # gold_hw + silver_hw + bronze_hw
        weighted_hardware = (gold_hw * 3) + (silver_hw * 2) + (bronze_hw * 1)

        # Calculate multiplied values
        mult_medals = round(weighted_medals * mult, 2)
        mult_raw_hw = round(raw_hardware * mult, 2)
        mult_weighted_hw = round(weighted_hardware * mult, 2)

        country_outputs.append({
            "Country": c_raw,
            "NormName": c_norm,
            "Participants": p_count,
            "Max Delegation": max_participants,
            "Dynamic Multiplier": round(mult, 4),
            "Gold": g,
            "Silver": s,
            "Bronze": b,
            "Total Medals": total_medals,
            "Weighted Medals": weighted_medals,
            "Raw Hardware": raw_hardware,
            "Weighted Hardware": weighted_hardware,
            "Multiplied Medals": mult_medals,
            "Multiplied Raw Hardware": mult_raw_hw,
            "Multiplied Weighted Hardware": mult_weighted_hw
        })

    # 4. Export CSVs
    print("Exporting Country Scores...")
    os.makedirs("output", exist_ok=True)
    with open("output/paralympic_country_scores.csv", 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            "Country", "Participants", "Max Delegation", "Dynamic Multiplier",
            "Gold", "Silver", "Bronze", "Total Medals", "Weighted Medals",
            "Raw Hardware", "Weighted Hardware",
            "Multiplied Medals", "Multiplied Raw Hardware", "Multiplied Weighted Hardware"
        ])
        writer.writeheader()

        # Sort by Multiplied Weighted Hardware
        country_outputs.sort(key=lambda x: x['Multiplied Weighted Hardware'], reverse=True)
        for row in country_outputs:
            out_row = {k: v for k, v in row.items() if k != 'NormName'}
            writer.writerow(out_row)
            
    print("Exporting Player Scores...")
    player_scores = []
    for player, teams in DRAFTED_TEAMS.items():
        p_mult_medals = 0
        p_mult_raw_hw = 0
        p_mult_weighted_hw = 0
        p_total_medals = 0
        p_weighted_medals = 0
        p_raw_hw = 0
        p_weighted_hw = 0
        for team in teams:
            c_norm = normalize_country_name(team)
            for row in country_outputs:
                if row['NormName'] == c_norm or normalize_country_name(COUNTRY_NAME_MAP.get(row['Country'], "")) == c_norm:
                    p_mult_medals += row['Multiplied Medals']
                    p_mult_raw_hw += row['Multiplied Raw Hardware']
                    p_mult_weighted_hw += row['Multiplied Weighted Hardware']
                    p_total_medals += row['Total Medals']
                    p_weighted_medals += row['Weighted Medals']
                    p_raw_hw += row['Raw Hardware']
                    p_weighted_hw += row['Weighted Hardware']
                    break

        player_scores.append({
            "Player": player,
            "Total Medals": p_total_medals,
            "Weighted Medals": p_weighted_medals,
            "Raw Hardware": p_raw_hw,
            "Weighted Hardware": p_weighted_hw,
            "Multiplied Medals": round(p_mult_medals, 2),
            "Multiplied Raw Hardware": round(p_mult_raw_hw, 2),
            "Multiplied Weighted Hardware": round(p_mult_weighted_hw, 2)
        })

    with open("output/paralympic_player_scores.csv", 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            "Player", "Total Medals", "Weighted Medals", "Raw Hardware", "Weighted Hardware",
            "Multiplied Medals", "Multiplied Raw Hardware", "Multiplied Weighted Hardware"
        ])
        writer.writeheader()
        player_scores.sort(key=lambda x: x['Multiplied Weighted Hardware'], reverse=True)
        writer.writerows(player_scores)
        
    print("Successfully exported all Paralympics CSV reports.")

if __name__ == '__main__':
    generate_reports()
