from main import normalize_country_name, COUNTRY_NAME_MAP

# --- Local Test Logic using Production Mappings ---

# --- Test Cases ---
test_cases = [
    ("Netherlands", "Netherlands", True),
    ("The Netherlands", "Netherlands", True),
    ("South Korea", "Republic of Korea", True), # Via Map
    ("United States", "USA", True), # Via Map
    ("The United States", "USA", True), # Via Map + Norm?
    ("China", "People's Republic of China", True),
    ("Czech Republic", "Czechia", True),
    ("Individual Neutral Athletes", "AIN", True)
]

print("--- Testing Normalization & Mapping (Production Logic) ---")
for input_name, target, expected in test_cases:
    # 1. Direct Normalization Match
    norm_input = normalize_country_name(input_name)
    norm_target = normalize_country_name(target)
    
    match = (norm_input == norm_target)
    
    # 2. Map Lookup
    if not match:
        mapped = COUNTRY_NAME_MAP.get(input_name)
        if mapped:
            if normalize_country_name(mapped) == norm_target:
                match = True
        
    print(f"'{input_name}' -> '{target}': {'PASS' if match == expected else 'FAIL'}")
    
print("\n--- Testing Specific Scenarios ---")
# Draft Tab Scenario: User types "The Netherlands", Scraper has "Netherlands"
draft_entry = "The Netherlands"
scraped_key = "Netherlands"

# Logic in calculate_draft_totals (Simulated)
found = False
if normalize_country_name(draft_entry) == normalize_country_name(scraped_key):
    found = True
elif COUNTRY_NAME_MAP.get(draft_entry) == scraped_key:
    found = True

print(f"Draft '{draft_entry}' finds Scraped '{scraped_key}': {found}")
