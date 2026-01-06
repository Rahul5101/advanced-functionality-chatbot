import json
import pandas as pd
import os

# Folders
json_folder = r"cleaned_data"  # Folder containing JSON files
csv_folder = r"csv_data"       # Folder to save CSV files

# Create CSV folder if it doesn't exist
os.makedirs(csv_folder, exist_ok=True)

# Loop through all files in the JSON folder
for filename in os.listdir(json_folder):
    if filename.endswith(".json"):
        json_file_path = os.path.join(json_folder, filename)
        
        # Load JSON data
        with open(json_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Save to CSV
        csv_file_name = os.path.splitext(filename)[0] + ".csv"  # Same name as JSON file
        csv_file_path = os.path.join(csv_folder, csv_file_name)
        df.to_csv(csv_file_path, index=False, encoding="utf-8")
        
        print(f"Converted {filename} → {csv_file_name}")

print("All JSON files have been converted to CSV!")

