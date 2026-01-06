import os
import json
from bs4 import BeautifulSoup
import re

def clean_html_keep_structure(html: str) -> str:
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style"]):
        tag.decompose()

    for tag in soup.find_all(["p", "div", "br"]):
        tag.insert_after("\n")

    text = soup.get_text(separator=" ", strip=True)

    text = re.sub(r'\xa0', ' ', text)             
    text = re.sub(r' +', ' ', text)               
    text = re.sub(r'\n\s+', '\n', text)           
    text = re.sub(r'\n{2,}', '\n\n', text)        
    text = text.strip()

    return text

def process_single_json(input_file: str, output_file: str):
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    for item in data:
        if "section_desc" in item:
            item["section_desc"] = clean_html_keep_structure(item["section_desc"])

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def process_folder(input_folder: str, output_folder: str):
    os.makedirs(output_folder, exist_ok=True)

    for filename in os.listdir(input_folder):
        if filename.endswith(".json"):
            input_path = os.path.join(input_folder, filename)
            output_path = os.path.join(output_folder, filename)

            print(f"Processing: {filename}")
            process_single_json(input_path, output_path)

# Example usage
process_folder(r"raw_data", r"cleaned_data")
