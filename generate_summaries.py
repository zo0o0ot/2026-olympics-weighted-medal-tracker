import csv
import json
from main import get_hardware_multiplier, normalize_country_name

FLAG_MAP = {
    "Norway": "🇳🇴",
    "Netherlands": "🇳🇱",
    "United States": "🇺🇸",
    "United States of America": "🇺🇸",
    "Canada": "🇨🇦",
    "Great Britain": "🇬🇧",
    "Sweden": "🇸🇪",
    "Italy": "🇮🇹",
    "France": "🇫🇷",
    "Germany": "🇩🇪",
    "Austria": "🇦🇹",
    "South Korea": "🇰🇷",
    "Switzerland": "🇨🇭",
    "Japan": "🇯🇵",
    "Georgia": "🇬🇪",
    "Slovenia": "🇸🇮",
    "Spain": "🇪🇸",
    "Finland": "🇫🇮",
    "New Zealand": "🇳🇿",
    "China": "🇨🇳",
    "Australia": "🇦🇺",
    "Poland": "🇵🇱",
    "Brazil": "🇧🇷",
    "Belgium": "🇧🇪",
    "Bulgaria": "🇧🇬",
    "Individual Neutral Athletes": "", # No specific flag 
    "AIN": "",
    "Czech Republic": "🇨🇿",
    "Kazakhstan": "🇰🇿",
    "Estonia": "🇪🇪",
    "Denmark": "🇩🇰",
    "Latvia": "🇱🇻",
    "Chinese Taipei": "🇹🇼",
    "Croatia": "🇭🇷",
    "Greece": "🇬🇷"
}

def generate_markdown():
    csv_file = "country_blog_data.csv"
    md_file = "country_summaries.md"
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        
    try:
        with open('scraped_details.json', 'r', encoding='utf-8') as f:
            details = json.load(f)
    except Exception:
        details = []
        
    from main import DRAFTED_TEAMS, COUNTRY_NAME_MAP
    
    def write_markdown_file(md_file, title, target_rows, details, is_master=False):
        if not target_rows:
            return
            
        markdown_content = f"# {title}\n\n"
        
        for row in target_rows:
            # When writing the master file, we are handed the raw CSV rows.
            # But we might also be handed a custom list of countries that didn't win medals 
            # (where 'row' might be a fake dict or string).
            if isinstance(row, str):
                # It's a zero-medal country name, not a CSV row
                drafted_country = row
                display_name = drafted_country
                for k, v in COUNTRY_NAME_MAP.items():
                    if normalize_country_name(v) == normalize_country_name(drafted_country):
                        display_name = k
                        break
                        
                if display_name in ["United States", "USA"]:
                    display_name = "United States of America"
                elif display_name == "AIN":
                    display_name = "Individual Neutral Athletes"
                    
                flag = FLAG_MAP.get(display_name, FLAG_MAP.get(drafted_country, ""))
                if flag:
                    flag = f" {flag}"
                    
                markdown_content += f"## {display_name}{flag}\n\n"
                markdown_content += f"**{display_name}** did not bring home any medals during these winter games.\n\n"
                markdown_content += "---\n\n"
                continue

            # Standard CSV Row logic
            country = row['Country']
            drafted_country = country # For displaying fallback
            c_norm_drafted = normalize_country_name(country)
            
            display_name = country
            for k, v in COUNTRY_NAME_MAP.items():
                if normalize_country_name(v) == c_norm_drafted:
                    display_name = k
                    break
                    
            # Apply user-requested display overrides
            if display_name in ["United States", "USA"]:
                display_name = "United States of America"
            elif display_name == "AIN":
                display_name = "Individual Neutral Athletes"
                
            flag = FLAG_MAP.get(display_name, FLAG_MAP.get(drafted_country, ""))
            if flag:
                flag = f" {flag}"
                
            # Build paragraph
            markdown_content += f"## {display_name}{flag}\n\n"
            
            participants = row['Participants']
            g = row['Gold Medals']
            s = row['Silver Medals']
            b = row['Bronze Medals']
            total_m = row['Total Medals']
            weighted_m = row['Weighted Medals']
            total_hw = row['Total Hardware']
            mult_m = row['Multiplied Medals']
            mult_hw = row['Multiplied Hardware']
            
            # Detail standard medals
            total_m_int = int(total_m)
            if total_m_int >= 20:
                performance_desc = "delivered a powerhouse performance"
            elif total_m_int >= 10:
                performance_desc = "put together a strong campaign"
            elif total_m_int >= 5:
                performance_desc = "had a solid showing"
            else:
                performance_desc = "made their mark on the games"

            # Use display_name in the text instead of the raw row country
            markdown_content += (
                f"**{display_name}** sent a delegation of **{participants}** athletes to the winter games. "
                f"They {performance_desc}, bringing home a haul of **{total_m} medals** "
                f"({g} 🥇, {s} 🥈, {b} 🥉) which netted them a baseline weighted score of {weighted_m} points.\n\n"
            )
            
            # Determine highest team size for event multiplier logic
            max_multiplier = 1
            search_name = "AIN" if country == "Individual Neutral Athletes" else country
            c_norm = normalize_country_name(search_name)
            
            for detail in details:
                if normalize_country_name(detail.get('Country', '')) == c_norm:
                    mult = get_hardware_multiplier(detail.get('Event', ''), detail.get('Medal', ''))
                    if mult > max_multiplier:
                        max_multiplier = mult

            # Detail hardware and multipliers (analytical breakdown)
            hardware_difference = int(total_hw) - int(total_m)
            
            if max_multiplier > 6:
                markdown_content += (
                    f"They excelled in large team sports, significantly boosting their physical medal count to "
                    f"**{total_hw} total hardware medals** placed around necks. "
                )
            elif max_multiplier > 1 or hardware_difference > 0:
                markdown_content += (
                    f"Their success in small team sports and relays boosted their physical medal count to "
                    f"**{total_hw} total hardware medals** placed around necks. "
                )
            else:
                markdown_content += (
                    f"Their medals came entirely from individual events, keeping their physical hardware output equal to their standard medal count. "
                )
                
            markdown_content += (
                f"After factoring in their custom draft handicap, they finished the games with a "
                f"Final **Multiplied Hardware** score of **{mult_hw}** and a base **Multiplied Medals** score of **{mult_m}**.\n\n"
            )
                
            markdown_content += "---\n\n"
            
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
            
        print(f"Generated summaries successfully into {md_file}.")


    # Write the master generated file containing all countries in the CSV
    write_markdown_file("country_summaries.md", "Master Country Performance Summaries", rows, details, is_master=True)
    
    # Write the player-specific files
    for player_name, drafted_countries in DRAFTED_TEAMS.items():
        # Setup target array linking rows with potential 0-medal drafts
        player_targets = []
        for drafted_country in drafted_countries:
            c_norm_drafted = normalize_country_name(drafted_country)
            
            matching_row = None
            for row in rows:
                csv_c = row['Country']
                if normalize_country_name(csv_c) == c_norm_drafted or normalize_country_name(COUNTRY_NAME_MAP.get(csv_c, csv_c)) == c_norm_drafted:
                    matching_row = row
                    break
                    
            if matching_row:
                player_targets.append(matching_row)
            else:
                player_targets.append(drafted_country) # Pass as string
                
        write_markdown_file(f"{player_name}_summaries.md", f"{player_name}'s Drafted Country Summaries", player_targets, details)

if __name__ == '__main__':
    generate_markdown()
