import json
from main import DRAFTED_TEAMS, normalize_country_name, COUNTRY_NAME_MAP

def test_medal_math():
    with open('scraped_medals.json', 'r') as f:
        medal_counts = json.load(f)
        
    with open('multipliers.json', 'r') as f:
        multipliers = json.load(f)

    team_totals = {team: {'medals': 0, 'weighted_medals': 0, 'multiplied_medals': 0.0} for team in DRAFTED_TEAMS}
    
    for country, counts in medal_counts.items():
        g, s, b = counts.get('Gold', 0), counts.get('Silver', 0), counts.get('Bronze', 0)
        w = (g * 3) + (s * 2) + b
        
        search_name = "AIN" if country == "Individual Neutral Athletes" else country
        c_norm = normalize_country_name(search_name)
        
        mult = 1.0
        for k, v in multipliers.items():
            if normalize_country_name(k) == c_norm:
                mult = v
                break
                
        owner_team = None
        for team, countries in DRAFTED_TEAMS.items():
            # Check direct or mapped
            if search_name in countries or country in countries:
                owner_team = team
                break
                
            mapped_c = COUNTRY_NAME_MAP.get(search_name) or COUNTRY_NAME_MAP.get(country)
            if mapped_c and mapped_c in countries:
                owner_team = team
                break
                
            for c in countries:
                if normalize_country_name(c) == c_norm or normalize_country_name(COUNTRY_NAME_MAP.get(c, c)) == c_norm:
                    owner_team = team
                    break
                    
            if not owner_team:
                # Reverse lookup
                for k, v in COUNTRY_NAME_MAP.items():
                    if v in countries and (normalize_country_name(k) == c_norm or k == search_name):
                        owner_team = team
                        break
                        
            if owner_team: break
            
        if owner_team:
            team_totals[owner_team]['medals'] += w
            team_totals[owner_team]['weighted_medals'] += w
            team_totals[owner_team]['multiplied_medals'] += (w * mult)
            
    print("Team Totals (Weighted Medals):", {k: v['weighted_medals'] for k, v in team_totals.items()})
    print("Team Totals (Multiplied Medals):", {k: v['multiplied_medals'] for k, v in team_totals.items()})
    
if __name__ == '__main__':
    test_medal_math()
