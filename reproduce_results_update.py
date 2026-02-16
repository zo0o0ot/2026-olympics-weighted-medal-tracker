import sys
from unittest.mock import MagicMock

# Mock gspread BEFORE importing main logic that might need it
mock_gspread = MagicMock()
mock_gspread.utils.rowcol_to_a1 = lambda r, c: f"R{r}C{c}"
sys.modules['gspread'] = mock_gspread

from main import update_results_tab, COUNTRY_NAME_MAP, normalize_country_name

# Mock Classes
class MockWorksheet:
    def __init__(self):
        self.data = [
            ['Country', 'Gold', 'Silver', 'Bronze', 'Multiplier'], # Header
            ['United States', '0', '0', '0', '1'],
            ['Great Britain', '0', '0', '0', '1'],
            ['China', '0', '0', '0', '1'],
            ['Australia', '0', '0', '0', '1'],
            ['Finland', '0', '0', '0', '1'],
            ['South Korea', '0', '0', '0', '1'],
            ['Netherlands', '0', '0', '0', '1'],
        ]
        
    def get_all_values(self):
        return self.data
        
    def batch_update(self, updates):
        print(f"\n[Mock] BATCH UPDATE: {len(updates)} cells")
        for u in updates:
            print(f"  {u['range']}: {u['values']}")
            
    def append_rows(self, rows):
        print(f"\n[Mock] APPEND ROWS: {len(rows)}")
        for r in rows:
            print(f"  {r}")

class MockClient:
    def open_by_key(self, key): return self
    def worksheet(self, name): return MockWorksheet()

# Test Data (matches user's scraped_medals.json snippet + hypotheses)
test_medal_counts = {
    'United States': {'Gold': 4, 'Silver': 6, 'Bronze': 2},
    'China': {'Gold': 0, 'Silver': 1, 'Bronze': 2}, # Mismatch? Sheet might be "People's Republic of China"
    'Finland': {'Gold': 0, 'Silver': 0, 'Bronze': 1},
    'South Korea': {'Gold': 0, 'Silver': 1, 'Bronze': 1}, # Sheet might be "Republic of Korea"
    'Netherlands': {'Gold': 1, 'Silver': 2, 'Bronze': 0},
    # Missing from scraper in my hypothesis, but user implies they have medals:
    'Great Britain': {'Gold': 1, 'Silver': 0, 'Bronze': 0}, 
    'Australia': {'Gold': 2, 'Silver': 0, 'Bronze': 0},
}

print("--- Running Reproduction ---")
client = MockClient()

# Override the print function in main.py to see debug output? 
# No need, main.py prints to stdout.

print("Test 1: Standard Update (GB, China, etc provided)")
update_results_tab(client, test_medal_counts)

# Now let's test mismatches specifically
print("\n--- Test 2: Mismatch Debugging ---")
# Sheet has "China", Scraper has "China" -> Should Match.
# Sheet has "South Korea", Scraper has "South Korea" -> Should Match.

# What about if Sheet has "People's Republic of China"?
print("\n--- Test 3: Standard Mapping Scenarios ---")
client.worksheet('Results').data = [
    ['Country', 'Gold', 'Silver', 'Bronze', 'Multiplier'],
    ['People\'s Republic of China', '0', '0', '0', '1'], # Formal name
    ['Republic of Korea', '0', '0', '0', '1'],        # Formal name
    ['United Kingdom', '0', '0', '0', '1'],           # For GB
]
update_results_tab(client, test_medal_counts)
