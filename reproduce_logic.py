from main import normalize_country_name, COUNTRY_NAME_MAP

# Mock Data
mock_medal_counts = {
    'Netherlands': {'Gold': 1, 'Silver': 2, 'Bronze': 3},
    'South Korea': {'Gold': 0, 'Silver': 1, 'Bronze': 0},
    'United States': {'Gold': 5, 'Silver': 5, 'Bronze': 5},
    'Norway': {'Gold': 10, 'Silver': 10, 'Bronze': 10}
}

# Mock Results Tab Data (Header + Rows)
mock_sheet_data = [
    ['Country', 'Gold', 'Silver', 'Bronze'],
    ['The Netherlands', '', '', ''],        # Should match 'Netherlands' via Fuzzy
    ['Netherlands', '', '', ''],            # Should match 'Netherlands' via Exact
    ['Republic of Korea', '', '', ''],      # Should match 'South Korea' via Map
    ['South Korea', '', '', ''],            # Should match 'South Korea' via Exact/Fuzzy
    ['Korea', '', '', ''],                  # Might fail? 'korea' vs 'south korea'
    ['USA', '', '', ''],                    # Should match 'United States' via Map
    ['United States', '', '', ''],          # Should match 'United States' via Exact
    ['Norway', '', '', '']                  # Should match 'Norway' via Exact
]

col_c = 0 # Country is first column

print("--- Testing update_results_tab Logic ---")

for i, row in enumerate(mock_sheet_data[1:]):
    c_name = row[col_c]
    print(f"\nProcessing Sheet Country: '{c_name}'")
    
    metrics = mock_medal_counts.get(c_name)
    found_via = "1. Exact Match"
    
    if not metrics:
        # 2. Fuzzy Match Scraped Keys
        c_norm = normalize_country_name(c_name)
        for k, v in mock_medal_counts.items():
            if normalize_country_name(k) == c_norm:
                metrics = v
                found_via = f"2. Fuzzy Match (Scraped Key: '{k}')"
                break
        
        # 3. Map Reverse Lookup
        if not metrics:
            for scraped_name, sheet_name in COUNTRY_NAME_MAP.items():
                if sheet_name == c_name or normalize_country_name(sheet_name) == c_norm:
                    metrics = mock_medal_counts.get(scraped_name)
                    found_via = f"3. Map Reverse Lookup (Map Key: '{scraped_name}' -> '{sheet_name}')"
                    
                    if not metrics:
                         s_norm = normalize_country_name(scraped_name)
                         for mk, mv in mock_medal_counts.items():
                             if normalize_country_name(mk) == s_norm:
                                 metrics = mv
                                 found_via += f" + Fuzzy Scraped Key ('{mk}')"
                                 break
                    if metrics: break

    if metrics:
        print(f"  SUCCESS: Found metrics via {found_via}")
        print(f"  Data: {metrics}")
    else:
        print(f"  FAIL: No metrics found for '{c_name}'")
