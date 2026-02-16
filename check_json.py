import json

def validate_data(data, data_type="counts"):
    """
    Validates scraped data to ensure no garbage (numeric keys, 'totals', etc.)
    Returns (bool, message)
    """
    if not data: return False, "No data found."
    
    if data_type == "counts":
        # Data is dict: {Country: {Gold, ...}}
        for country in data.keys():
            if not country or len(country) < 2: return False, f"Invalid country name: '{country}'"
            if country.isdigit(): return False, f"Numeric country name detected: '{country}'"
            if "total" in country.lower(): return False, f"Total row detected as country: '{country}'"
            if "rank" in country.lower(): return False, f"Rank header detected as country: '{country}'"
            
    return True, "Validation Passed"

try:
    with open('scraped_medals.json', 'r') as f:
        data = json.load(f)
        
    print(f"Loaded {len(data)} entries.")
    
    is_valid, msg = validate_data(data, "counts")
    print(f"Validation Result: {is_valid}")
    print(f"Message: {msg}")
    
    if not is_valid:
        print("\n--- Keys ---")
        for k in data.keys():
            print(f"'{k}'")
            
except Exception as e:
    print(f"Error: {e}")
