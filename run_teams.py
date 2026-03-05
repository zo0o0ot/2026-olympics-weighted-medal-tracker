import json
from main import aggregate_hardware_counts, export_teams_to_csv

def generate_team_csv():
    with open('scraped_details.json', 'r') as f:
        details = json.load(f)
        
    with open('scraped_medals.json', 'r') as f:
        medal_counts = json.load(f)
        
    print("Aggregating team scores with standard medals...")
    hw_counts = aggregate_hardware_counts(details)
    export_teams_to_csv(hw_counts, medal_counts)

if __name__ == '__main__':
    generate_team_csv()
