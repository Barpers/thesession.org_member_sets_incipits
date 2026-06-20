#!/usr/bin/env python3
"""
Download all pages of JSON data from The Session API and save to a file.
"""
import urllib.request
import urllib.parse
import json
import sys

# API endpoint
base_url = "https://thesession.org/members/179479/sets"

all_sets = []
total_pages = 1
current_page = 1

print(f"Starting download from {base_url}...")

try:
    # Fetch the first page to determine total pages
    params = urllib.parse.urlencode({
        "perpage": 50,
        "format": "json",
        "page": current_page
    })
    url = f"{base_url}?{params}"
    
    with urllib.request.urlopen(url, timeout=10) as response:
        data = json.loads(response.read().decode('utf-8'))
    
    # Get the total number of pages
    if "pages" in data:
        total_pages = data["pages"]
        print(f"Total pages to download: {total_pages}")
    
    # Extract sets from first page
    if "sets" in data:
        all_sets.extend(data["sets"])
        print(f"Page {current_page}: Downloaded {len(data['sets'])} sets")
    
    # Download remaining pages
    for page_num in range(2, total_pages + 1):
        params = urllib.parse.urlencode({
            "perpage": 50,
            "format": "json",
            "page": page_num
        })
        url = f"{base_url}?{params}"
        
        with urllib.request.urlopen(url, timeout=10) as response:
            page_data = json.loads(response.read().decode('utf-8'))
        
        if "sets" in page_data:
            all_sets.extend(page_data["sets"])
            print(f"Page {page_num}: Downloaded {len(page_data['sets'])} sets")
    
    # Save to file
    output_file = "./data/sets_full.json"
    with open(output_file, "w") as f:
        json.dump(all_sets, f, indent=2)
    
    print(f"\n✓ Successfully downloaded {len(all_sets)} total sets")
    print(f"✓ Saved to: {output_file}")
    
except urllib.error.URLError as e:
    print(f"✗ Error fetching data: {e}", file=sys.stderr)
    sys.exit(1)
except json.JSONDecodeError as e:
    print(f"✗ Error parsing JSON: {e}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"✗ Unexpected error: {e}", file=sys.stderr)
    sys.exit(1)
