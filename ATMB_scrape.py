import requests
from bs4 import BeautifulSoup
import argparse
import csv
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
BASE_URL = "https://www.anytimemailbox.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
OUTPUT_DIR = "Public"

def get_soup(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser')
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        return None

def parse_address_block(addr_text):
    # Expected format:
    # Line 1: Street
    # Line 2: City, State Zip
    
    parts = [p.strip() for p in addr_text.splitlines() if p.strip()]
    if not parts:
        return None, None, None, None

    street = parts[0]
    city = ""
    state = ""
    zip_code = ""

    if len(parts) >= 2:
        # Parse the last line for City, State Zip
        # Regex for "City, State Zip" or "City, State Zip-Ext"
        # Example: "Airmont, NY 10901" or "New York, NY 10001"
        # We assume State is 2 chars.
        match = re.search(r'^(.*),\s+([A-Z]{2})\s+(\d{5}(?:-\d{4})?)$', parts[-1])
        if match:
            city = match.group(1).strip()
            state = match.group(2).strip()
            zip_code = match.group(3).strip()
        else:
            # Fallback if regex fails, maybe simple comma split check?
            # But let's stick to the regex as primary method
            print(f"Warning: Could not parse City/State/Zip from '{parts[-1]}'", file=sys.stderr)
            pass
            
    return street, city, state, zip_code

def scrape_state(state_slug):
    url = f"{BASE_URL}/l/usa/{state_slug}"
    print(f"Scraping {state_slug} from {url}...")
    
    soup = get_soup(url)
    if not soup:
        return

    location_items = soup.find_all(class_='theme-location-item')
    
    data = []
    
    if not location_items:
        print(f"No locations found for {state_slug}. Check if state name is correct.", file=sys.stderr)
        return

    for item in location_items:
        # Title often contains City or "City - Neighborhood"
        # title_tag = item.find(class_='t-title')
        # title = title_tag.get_text(strip=True) if title_tag else "Unknown"
        
        addr_div = item.find(class_='t-addr')
        if not addr_div:
            continue
            
        # Get text with separators replacing <br>
        # BeautifulSoup's start tags handling for separator is nice
        # But here we might just want to get text and split lines?
        # Let's use get_text with separator to be safe
        addr_text = addr_div.get_text(separator="\n", strip=True)
        
        street, city, state, zip_code = parse_address_block(addr_text)
        
        # Extract Detail URL
        # Look for the "Select Plan" button/link
        link = item.find('a', href=True, class_='theme-button')
        detail_url = ""
        if link:
            href = link['href']
            if href.startswith("/"):
                detail_url = f"{BASE_URL}{href}"
            else:
                detail_url = href
        
        if street and city and state and zip_code:
            data.append([street, city, state, zip_code, detail_url])

    if not data:
        print(f"No valid addresses parsed for {state_slug}.", file=sys.stderr)
        return

    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Filename: [state].csv (e.g. idaho.csv)
    filename = os.path.join(OUTPUT_DIR, f"{state_slug}.csv")
    
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Street Address", "City", "State Abbreviation", "Zip Code", "Detail Url"])
            writer.writerows(data)
        print(f"Successfully saved {len(data)} addresses to {filename}")
    except IOError as e:
        print(f"Error writing to {filename}: {e}", file=sys.stderr)

def scrape_us():
    url = f"{BASE_URL}/l/usa"
    print(f"Fetching all states from {url}...")
    soup = get_soup(url)
    if not soup:
        return

    # Find all state links.
    # Pattern: <a class="theme-loc-link" href="/l/usa/alabama">
    links = soup.select('a.theme-loc-link[href^="/l/usa/"]')
    
    state_slugs = []
    for link in links:
        href = link.get('href')
        # Extract slug: /l/usa/alabama -> alabama
        slug = href.split('/')[-1]
        if slug:
            state_slugs.append(slug)
    
    # Deduplicate just in case
    state_slugs = sorted(list(set(state_slugs)))
    print(f"Found {len(state_slugs)} states. Starting scrape...")

    # Use ThreadPoolExecutor for faster processing
    # Be polite but efficient. 5 workers.
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_state = {executor.submit(scrape_state, slug): slug for slug in state_slugs}
        for future in as_completed(future_to_state):
            slug = future_to_state[future]
            try:
                future.result()
            except Exception as exc:
                print(f"{slug} generated an exception: {exc}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(description="Scrape Anytime Mailbox addresses.")
    parser.add_argument("--input", required=True, help="State name (e.g., 'new-york') or 'us' for all states.")
    
    args = parser.parse_args()
    
    input_val = args.input.lower().strip()
    
    if input_val == 'us':
        scrape_us()
    else:
        scrape_state(input_val)

if __name__ == "__main__":
    main()
