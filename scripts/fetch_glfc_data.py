import requests
import json
import os

ENDPOINTS = {
    "barriers": "http://data.glfc.org/barriers.json",
    "treatments": "http://data.glfc.org/treatments.json",
    "treatments2015": "http://data.glfc.org/treatments2015.json",
    "trapping": "http://data.glfc.org/trapping.json"
}

OUTPUT_DIR = "data/glfc"

def fetch_data():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    for name, url in ENDPOINTS.items():
        print(f"Fetching {name} from {url}...")
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            output_path = os.path.join(OUTPUT_DIR, f"{name}.json")
            with open(output_path, "w") as f:
                json.dump(data, f, indent=2)
            print(f"Saved {name} to {output_path} ({len(data)} records)")
        except Exception as e:
            print(f"Error fetching {name}: {e}")

if __name__ == "__main__":
    fetch_data()
