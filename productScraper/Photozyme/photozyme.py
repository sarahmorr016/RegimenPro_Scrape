import csv
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from datetime import datetime

# === FILE PATHS ===
input_csv = "/Users/sarahmorrison/Desktop/RegimenPro/productScraper/Photozyme/Photozyme_product_urls.csv"
output_csv = "/Users/sarahmorrison/Desktop/Photozyme_Scraped_Products.csv"
comparison_csv = "/Users/sarahmorrison/Desktop/photozyme_comparison.csv"

# === FIELD DEFINITIONS ===
fieldnames = [
    "Product URL",
    "Product Name",
    "Product Description",
    "SKU",
    "Product Price",
    "Date/Time Captured"
]

comparison_fieldnames = [
    "Product URL",
    "Field",
    "Photozyme Value",
    "RegimenPro Value",
    "Match?",
    "Date/Time Captured"
]

comparison_rows = []
cutoff_markers = ["Benefits", "Ingredients", "How to Use", "Directions", "Suggested Use", "Apply", "Usage"]

# === CLEAN DESCRIPTION ===
def extract_main_description(body_html):
    soup = BeautifulSoup(body_html, 'html.parser')
    full_text = soup.get_text(separator=" ", strip=True)
    for marker in cutoff_markers:
        index = full_text.lower().find(marker.lower())
        if index != -1:
            return full_text[:index].strip()
    return full_text.strip()

# === COMPARISON FUNCTION ===
def compare_fields(source_data, regimen_data, product_url, timestamp):
    rows = []
    for key in source_data:
        if key in regimen_data:
            pz_val = source_data[key].strip()
            rp_val = regimen_data[key].strip()

            if key == "Product Price":
                try:
                    pz_val_float = float(pz_val.replace("$", "").strip())
                    rp_val_float = float(rp_val.replace("$", "").strip())
                    is_match = "✅ Yes" if pz_val_float == rp_val_float else "❌ No"
                except:
                    is_match = "⚠️ Invalid price format"
            else:
                is_match = "✅ Yes" if pz_val.lower() == rp_val.lower() else "❌ No"

            rows.append({
                "Product URL": product_url,
                "Field": key,
                "Photozyme Value": pz_val,
                "RegimenPro Value": rp_val,
                "Match?": is_match,
                "Date/Time Captured": timestamp
            })
    return rows

# === MAIN SCRIPT ===
with open(output_csv, 'w', newline='') as outfile:
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()

    with open(input_csv, mode="r", newline='') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            pz_url = row["Product Urls"].strip()
            rp_url = row["RegimenPro Urls"].strip()
            print("Loaded Photozyme URL:", pz_url)
            print("Loaded RegimenPro URL:", rp_url)

            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            try:
                # === PHOTOZYME ===
                parsed = urlparse(pz_url)
                clean_path = parsed.scheme + "://" + parsed.netloc + parsed.path
                pz_json_url = clean_path + ".json"

                pz_response = requests.get(pz_json_url)
                if pz_response.status_code == 200:
                    pz_data = pz_response.json()
                    product = pz_data["product"]
                    variant = product["variants"][0]

                    name = product.get("title", "No name")
                    description_html = product.get("body_html", "")
                    description = extract_main_description(description_html)
                    sku = variant.get("sku", "No SKU")
                    price = variant.get("price", "No price")

                    # Write to scraped product CSV
                    writer.writerow({
                        "Product URL": pz_url,
                        "Product Name": name,
                        "Product Description": description,
                        "SKU": sku,
                        "Product Price": price,
                        "Date/Time Captured": now_str
                    })

                    # === REGIMENPRO ===
                    rp_response = requests.get(rp_url + ".json")
                    if rp_response.status_code == 200:
                        rp_data = rp_response.json()
                        rp_product = rp_data["product"]
                        rp_variant = rp_product["variants"][0]
                        rp_description_html = rp_product.get("body_html", "")
                        rp_description = extract_main_description(rp_description_html)

                        photozyme_data = {
                            "Product Name": name,
                            "Product Description": description,
                            "SKU": sku,
                            "Product Price": price
                        }

                        regimenpro_data = {
                            "Product Name": rp_product.get("title", "No name"),
                            "Product Description": rp_description,
                            "SKU": rp_variant.get("sku", "No SKU"),
                            "Product Price": rp_variant.get("price", "No price")
                        }

                        comparison_rows.extend(compare_fields(photozyme_data, regimenpro_data, pz_url, now_str))
                    else:
                        print(f"⚠️ RegimenPro JSON error: {rp_response.status_code}")
                else:
                    print(f"⚠️ Photozyme JSON error: {pz_response.status_code}")

            except Exception as e:
                print(f"❌ Error processing {pz_url}: {e}")

# === WRITE COMPARISON FILE ===
with open(comparison_csv, 'w', newline='') as compfile:
    comp_writer = csv.DictWriter(compfile, fieldnames=comparison_fieldnames)
    comp_writer.writeheader()
    for row in comparison_rows:
        comp_writer.writerow(row)
