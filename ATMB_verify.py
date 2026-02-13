import argparse
import csv
import os
import sys
import requests
import time

# --- Configuration ---
SMARTY_API_URL = "https://us-street.api.smarty.com/street-address"
CREDENTIALS_FILE = "smarty_api_key.txt"

def load_credentials(filepath):
    """Loads Auth ID and Auth Token from the specified file."""
    if not os.path.exists(filepath):
        print(f"Error: Credentials file not found at {filepath}")
        print("Please create the file with content:")
        print("auth_id=YOUR_AUTH_ID")
        print("auth_token=YOUR_AUTH_TOKEN")
        sys.exit(1)
        
    auth_id = None
    auth_token = None
    
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith("auth_id="):
                auth_id = line.split("=", 1)[1].strip()
            elif line.startswith("auth_token="):
                auth_token = line.split("=", 1)[1].strip()
                
    if not auth_id or not auth_token:
        print("Error: Invalid credentials file format. Missing auth_id or auth_token.")
        sys.exit(1)
        
    return auth_id, auth_token

def verify_address(auth_id, auth_token, street, city, state, zipcode, secondary=""):
    """
    Verifies a single address using Smarty API.
    Returns (rdi, cmra) or (None, None) if validation fails.
    """
    params = {
        "auth-id": auth_id,
        "auth-token": auth_token,
        "street": street,
        "city": city,
        "state": state,
        "zipcode": zipcode,
        "candidates": 1,
        "match": "strict"
    }
    
    if secondary:
        params["secondary"] = secondary
        
    try:
        response = requests.get(SMARTY_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            return "Invalid", "Invalid"
            
        candidate = data[0]
        metadata = candidate.get("metadata", {})
        analysis = candidate.get("analysis", {})
        
        rdi = metadata.get("rdi", "Unknown")
        cmra = analysis.get("dpv_cmra", "Unknown")
        
        return rdi, cmra
        
    except Exception as e:
        print(f"API Error: {e}")
        return "Error", "Error"

def main():
    parser = argparse.ArgumentParser(description="ATMB Verify Tool: Verify addresses using Smarty API.")
    parser.add_argument("--input", required=True, help="Path to input CSV file.")
    
    args = parser.parse_args()
    input_file = args.input
    
    if not os.path.exists(input_file):
        print(f"Error: Input file {input_file} does not exist.")
        sys.exit(1)
        
    # Check if input filename ends with _detailed (case insensitive)
    is_detailed = input_file.lower().endswith("_detailed.csv")
    
    # Construct output filename
    base, ext = os.path.splitext(input_file)
    output_file = f"{base}_verified{ext}"
    
    # Load Credentials
    # Look for credentials file in the same directory as the script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cred_path = os.path.join(script_dir, CREDENTIALS_FILE)
    
    # If not found, try current working directory
    if not os.path.exists(cred_path):
         cred_path = CREDENTIALS_FILE

    # If still not found, prompt user
    if not os.path.exists(cred_path):
        print(f"Error: Credentials file '{CREDENTIALS_FILE}' not found.")
        print(f"Please create it in {script_dir} or current directory.")
        sys.exit(1)
         
    auth_id, auth_token = load_credentials(cred_path)
    
    print(f"Processing: {input_file}")
    print(f"Output: {output_file}")
    print(f"Mode: {'Detailed (with Unit)' if is_detailed else 'Basic (Street Only)'}")
    
    rows = []
    # Use 'utf-8-sig' to handle potential BOM in CSV files
    try:
        with open(input_file, 'r', newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            if not fieldnames:
                 print("Error: Empty CSV or no header.")
                 sys.exit(1)
            for row in reader:
                rows.append(row)
    except FileNotFoundError:
        print(f"Error: File not found: {input_file}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        sys.exit(1)

            
    # Add new columns if not exist
    # Add new columns, insert after 'Zip Code' if possible
    # First remove them if they exist to ensure correct positioning
    if "RDI" in fieldnames:
        fieldnames.remove("RDI")
    if "CMRA" in fieldnames:
        fieldnames.remove("CMRA")
        
    if "Zip Code" in fieldnames:
        zip_idx = fieldnames.index("Zip Code")
        # Insert in reverse order to appear as Zip -> RDI -> CMRA
        fieldnames.insert(zip_idx + 1, "CMRA")
        fieldnames.insert(zip_idx + 1, "RDI")
    else:
        fieldnames.append("RDI")
        fieldnames.append("CMRA")
        
    total = len(rows)
    print(f"Total addresses: {total}")
    
    verified_count = 0
    
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for i, row in enumerate(rows):
                street = row.get("Street Address", "")
                city = row.get("City", "")
                state = row.get("State Abbreviation", "") 
                zipcode = row.get("Zip Code", "")
                
                secondary = ""
                if is_detailed:
                    secondary = row.get("Suite/Apartment", "").strip()
                    
                # Clean secondary if it is just "#" or looks empty
                if secondary == "#":
                    secondary = ""
                
                print(f"[{i+1}/{total}] Verifying: {street} {secondary}, {city}, {state}...", end="", flush=True)
                
                rdi, cmra = verify_address(auth_id, auth_token, street, city, state, zipcode, secondary)
                
                print(f" -> RDI: {rdi}, CMRA: {cmra}")
                
                row["RDI"] = rdi
                row["CMRA"] = cmra
                writer.writerow(row)
                verified_count += 1
                
                # Tiny sleep to avoid aggressive looping
                time.sleep(0.05)
                
        print(f"Done. Verified {verified_count} addresses. Saved to {output_file}")
        
    except PermissionError:
        print(f"\nError: Permission denied writing to {output_file}. Is it open?")
    except Exception as e:
        print(f"\nError writing output: {e}")

if __name__ == "__main__":
    main()
