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

def normalize_country_name(name):
    """Normalize for fuzzy matching."""
    if not name: return ""
    name = name.lower()
    for prefix in ["the ", "republic of ", "people's republic of "]:
        if name.startswith(prefix):
            name = name[len(prefix):]
    return name.strip()

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
        return {}, []

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
                            medals.append({
                                "CountryRaw": country_raw,
                                "Country": country,
                                "Gold": g,
                                "Silver": s,
                                "Bronze": b,
                                "Hardware": g + s + b # We will override this with details if available
                            })
                        except (ValueError, IndexError):
                            pass
    except Exception as e:
        print(f"Failed to fetch {medal_url}: {e}")
                            
    return participants, medals

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
    participants, medals = scrape_wikipedia_data()
    
    # Optional load from local JSON if scraping fails
    if not participants:
        print("Using local participants data fallback...")
        participants = load_participant_counts()
        
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
        g = s = b = total_hw = 0
        for m in medals:
            if m['Country'] == c_norm:
                c_raw = m['CountryRaw'] # Upgrade to exact Wikipedia casing
                g = m['Gold']
                s = m['Silver']
                b = m['Bronze']
                total_hw = m['Hardware']
                break
                
        # We don't have scraped hardware details mapped yet, so Total Hardware defaults to Medal Count
        total_medals = g + s + b
        weighted_medals = (g * 3) + (s * 2) + (b * 1)
        
        # Calculate final multipliers
        mult_medals = round(weighted_medals * mult, 2)
        mult_hw = round(total_hw * mult, 2)
        
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
            "Total Hardware": total_hw,
            "Multiplied Medals": mult_medals,
            "Multiplied Hardware": mult_hw
        })

    # 4. Export CSVs
    print("Exporting Country Scores...")
    os.makedirs("output", exist_ok=True)
    with open("output/paralympic_country_scores.csv", 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            "Country", "Participants", "Max Delegation", "Dynamic Multiplier", 
            "Gold", "Silver", "Bronze", "Total Medals", "Weighted Medals", 
            "Total Hardware", "Multiplied Medals", "Multiplied Hardware"
        ])
        writer.writeheader()
        
        # Sort by Multiplied Hardware
        country_outputs.sort(key=lambda x: x['Multiplied Hardware'], reverse=True)
        for row in country_outputs:
            out_row = {k: v for k, v in row.items() if k != 'NormName'}
            writer.writerow(out_row)
            
    print("Exporting Player Scores...")
    player_scores = []
    for player, teams in DRAFTED_TEAMS.items():
        p_medals = 0
        p_hw = 0
        for team in teams:
            c_norm = normalize_country_name(team)
            for row in country_outputs:
                if row['NormName'] == c_norm or normalize_country_name(COUNTRY_NAME_MAP.get(row['Country'], "")) == c_norm:
                    p_medals += row['Multiplied Medals']
                    p_hw += row['Multiplied Hardware']
                    break
                    
        player_scores.append({
            "Player": player,
            "Total Multiplied Medals": round(p_medals, 2),
            "Total Multiplied Hardware": round(p_hw, 2)
        })
        
    with open("output/paralympic_player_scores.csv", 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            "Player", "Total Multiplied Medals", "Total Multiplied Hardware"
        ])
        writer.writeheader()
        player_scores.sort(key=lambda x: x['Total Multiplied Hardware'], reverse=True)
        writer.writerows(player_scores)
        
    print("Successfully exported all Paralympics CSV reports.")

if __name__ == '__main__':
    generate_reports()
