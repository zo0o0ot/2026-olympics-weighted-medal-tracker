import csv
import json
from main import get_hardware_multiplier, normalize_country_name

FLAG_MAP = {
    "Norway": "🇳🇴",
    "Netherlands": "🇳🇱",
    "United States": "🇺🇸",
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
        
    markdown_content = "# Country Performance Summaries\n\n"
    
    for row in rows:
        country = row['Country']
        flag = FLAG_MAP.get(country, "")
        if flag:
            flag = f" {flag}"
            
        participants = row['Participants']
        g = row['Gold Medals']
        s = row['Silver Medals']
        b = row['Bronze Medals']
        total_m = row['Total Medals']
        weighted_m = row['Weighted Medals']
        total_hw = row['Total Hardware']
        mult_m = row['Multiplied Medals']
        mult_hw = row['Multiplied Hardware']
        
        # Build paragraph
        markdown_content += f"## {country}{flag}\n\n"
        
        # Detail standard medals
        markdown_content += (
            f"**{country}** sent a delegation of **{participants}** athletes to the winter games. "
            f"They performed admirably, bringing home a haul of **{total_m} medals** "
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

if __name__ == '__main__':
    generate_markdown()
