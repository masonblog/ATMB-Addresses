import csv
import requests
from bs4 import BeautifulSoup
import time
import re
import os
import argparse
import glob
import sys

# Configuration
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def clean_text(text):
    return " ".join(text.split())

def construct_url(city, street_address):
    # Rule: lowercase, replace spaces with hyphens
    city_slug = clean_text(city).lower().replace(' ', '-')
    street_slug = clean_text(street_address).lower().replace(' ', '-')
    # Basic sanitization for URL
    street_slug = street_slug.replace('.', '').replace('#', '')
    return f"https://www.anytimemailbox.com/s/{city_slug}-{street_slug}"

def extract_suite_info(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Target the specific address container to avoid footer (e.g., "Suite 244" in footer)
    addr_container = soup.find(class_='t-addr')
    if not addr_container:
        return ""

    # Get text specifically from the address container
    text = addr_container.get_text(separator="\n")
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    for line in lines:
        # Filter out common non-suite lines
        if "United States" in line or "Your Real Street Address" in line or "YOUR NAME" in line:
            continue
            
        # Check for Suite/Ste/Unit/Apt/#
        # We want lines that specifically look like unit info
        if re.search(r'\b(Suite|Ste|Unit|Apt)\b|[#]', line, re.IGNORECASE):
            # Remove "MAILBOX" placeholder if present
            clean_line = line.replace("MAILBOX", "").strip()
            # If line is just "#", it might be empty unit info, but let's return it if it looks like content
            if len(clean_line) > 1: 
                return clean_line
            
    return ""

def save_csv(filename, fieldnames, rows):
    temp_file = filename + ".tmp"
    with open(temp_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    # atomic replace if possible, or just rename
    if os.path.exists(filename):
        os.remove(filename)
    os.rename(temp_file, filename)

def process_file(input_file, output_file=None):
    if not os.path.exists(input_file):
        print(f"Error: Input file not found at {input_file}", flush=True)
        return

    if output_file is None:
        base, ext = os.path.splitext(input_file)
        if "_detailed" in base:
            output_file = input_file # Update in place if already an detailed file
        else:
            output_file = f"{base}_detailed{ext}"

    print(f"Processing: {input_file} -> {output_file}", flush=True)
    
    # Read input
    all_rows = []
    with open(input_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            all_rows.append(row)
            
    if not all_rows:
        print("  No rows found.", flush=True)
        return

    # Check if we are resuming
    processed_count = 0
    if os.path.exists(output_file):
        print(f"  Resuming from existing output file: {output_file}", flush=True)
        with open(output_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            # Load existing processed extracted data to mapped by ID or index
            # Since rows usually don't have ID, we might need to rely on index or matching address
            # Simpler approach: Just load the output file as the starting point for 'all_rows'
            # IF the output file has more/same rows as input.
            saved_rows = list(reader)
            if len(saved_rows) >= len(all_rows):
                all_rows = saved_rows
                if 'Suite/Apartment' not in fieldnames and 'Suite/Apartment' in reader.fieldnames:
                    fieldnames = reader.fieldnames

    # Ensure 'Suite/Apartment' column exists
    if 'Suite/Apartment' not in fieldnames:
        fieldnames.insert(1, 'Suite/Apartment')

    total = len(all_rows)
    success_count = 0
    updated_any = False

    for idx, row in enumerate(all_rows):
        # timestamp for progress speed
        
        # Check if already processed
        current_suite = row.get('Suite/Apartment', '').strip()
        if current_suite:
            # Already has data, skip (assume correct or previously extracted)
            success_count += 1
            continue
            
        city = row.get('City', '')
        street = row.get('Street Address', '')
        
        if not city or not street:
            continue
            
        detail_url = row.get('Detail Url', '').strip()
        if detail_url:
            url = detail_url
        else:
            url = construct_url(city, street)
            
        print(f"  [{idx+1}/{total}] {city}, {street}", end='', flush=True)
        
        try:
            response = requests.get(url, headers=DEFAULT_HEADERS, timeout=10)
            
            # Check for redirect
            if response.url != url:
                 # Sometimes simple slash differences or query params are ok, but major changes indicate redirect
                 # e.g. https://www.anytimemailbox.com/locations
                 if "locations" in response.url or response.url.strip("/") == "https://www.anytimemailbox.com":
                     print(f" -> Redirected to {response.url} (URL mismatch)", flush=True)
                     continue

            if response.status_code == 200:
                suite_info = extract_suite_info(response.text)
                if suite_info:
                    print(f" -> Found: {suite_info}", flush=True)
                    row['Suite/Apartment'] = suite_info
                    success_count += 1
                    updated_any = True
                else:
                    # Debug: check why
                    if "t-addr" not in response.text:
                         print(f" -> No .t-addr found in page", flush=True)
                    else:
                         print(f" -> No info extracted (Regex mismatch?)", flush=True)
            else:
                print(f" -> Failed ({response.status_code})", flush=True)
                
        except Exception as e:
            print(f" -> Error: {e}", flush=True)
        
        # Incremental save every 10 rows or if it's the last one
        if updated_any and (idx % 10 == 0 or idx == total - 1):
             save_csv(output_file, fieldnames, all_rows)
             updated_any = False # Reset flag
        
        time.sleep(0.5) 

    # Final save
    save_csv(output_file, fieldnames, all_rows)
    print(f"  Complete. Saved to {output_file}. (Filled: {success_count}/{total})", flush=True)

def main():
    parser = argparse.ArgumentParser(description="Extract suite info from Anytime Mailbox addresses.")
    parser.add_argument("--input", help="Path to input CSV file")
    parser.add_argument("--folder", help="Path to folder containing CSV files to process")
    
    args = parser.parse_args()
    
    if args.input:
        process_file(args.input)
    elif args.folder:
        if not os.path.isdir(args.folder):
            print(f"Error: Folder not found: {args.folder}")
            return
            
        csv_files = glob.glob(os.path.join(args.folder, "*_Addresses.csv"))
        print(f"Found {len(csv_files)} address files in {args.folder}")
        
        for csv_file in csv_files:
            if "_Updated" in csv_file:
                continue
            process_file(csv_file)
    else:
        # Default behavior
        default_file = r'c:\Users\dell\Desktop\ATMB-Addresses\Public\Colorado_Addresses.csv'
        if os.path.exists(default_file):
            print("No arguments provided. Processing default file.", flush=True)
            process_file(default_file)
        else:
            parser.print_help()

if __name__ == "__main__":
    main()
