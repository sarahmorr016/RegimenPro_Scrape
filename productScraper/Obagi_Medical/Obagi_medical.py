import csv
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from datetime import datetime

# ==== FILE PATHS ====
input_csv = "/Users/sarahmorrison/Desktop/RegimenPro/productScraper/Obagi_Medical/Obagi_Medical_product_urls.csv"
output_csv = "/Users/sarahmorrison/Desktop/Obagi_Scraped_Products.csv"
comparison_csv = "/Users/sarahmorrison/Desktop/obagi_comparison.csv"

# ==== FIELD DEFINITIONS ====
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
    "Obagi Value",
    "RegimenPro Value",
    "Match?",
    "Date/Time Captured"
]

comparison_rows = []

# ==== COMPARISON FUNCTION ====
def compare_fields(source_data, regimen_data, product_url, timestamp):
    rows = []
    for key in source_data:
        if key in regimen_data:
            obagi_val = source_data[key].strip()
            regimen_val = regimen_data[key].strip()

            if key == "Product Price":
                try:
                    obagi_val_float = float(obagi_val.replace("$", "").strip())
                    regimen_val_float = float(regimen_val.replace("$", "").strip())
                    is_match = "✅ Yes" if obagi_val_float == regimen_val_float else "❌ No"
                except:
                    is_match = "⚠️ Invalid price format"
            else:
                is_match = "✅ Yes" if obagi_val.lower() == regimen_val.lower() else "❌ No"

            rows.append({
                "Product URL": product_url,
                "Field": key,
                "Obagi Value": obagi_val,
                "RegimenPro Value": regimen_val,
                "Match?": is_match,
                "Date/Time Captured": timestamp
            })
    return rows

# ==== MAIN LOGIC ====
with open(output_csv, 'w', newline='') as outfile:
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()

    with open(input_csv, mode="r", newline='') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            obagi_url = row["Product Urls"].strip()
            regimen_url = row["RegimenPro Urls"].strip()
            print("Loaded Obagi URL:", obagi_url)
            print("Loaded RegimenPro URL:", regimen_url)

            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            try:
                # GET Obagi JSON
                parsed = urlparse(obagi_url)
                clean_path = parsed.scheme + "://" + parsed.netloc + parsed.path
                json_url = clean_path + ".json"
                json_response = requests.get(json_url)
                if json_response.status_code == 200:
                    json_data = json_response.json()
                    product = json_data["product"]
                    variant = product["variants"][0]

                    name = product.get("title", "No name")
                    description_html = product.get("body_html", "")

                    # Clean and truncate description
                    raw_text = BeautifulSoup(description_html, 'html.parser').get_text(separator=" ", strip=True)
                    clean_description = raw_text.replace("-Use", "Use").replace("–", "-").replace("—", "-")
                    cutoff_markers = ["Use Instructions", "Ingredients", "Directions", "How to Use", "Suggested Use"]

                    for marker in cutoff_markers:
                        index = clean_description.lower().find(marker.lower())
                        if index != -1:
                            description = clean_description[:index].strip().rstrip("-:•")
                            break
                    else:
                        description = clean_description

                    sku = variant.get("sku", "No SKU")
                    price = variant.get("price", "No price")

                    # Write to scraped product CSV
                    writer.writerow({
                        "Product URL": obagi_url,
                        "Product Name": name,
                        "Product Description": description,
                        "SKU": sku,
                        "Product Price": price,
                        "Date/Time Captured": now_str
                    })

                    # GET RegimenPro JSON
                    regimen_response = requests.get(regimen_url + ".json")
                    if regimen_response.status_code == 200:
                        regimen_data = regimen_response.json()
                        rp_product = regimen_data["product"]
                        rp_variant = rp_product["variants"][0]
                        rp_description_html = rp_product.get("body_html", "")
                        rp_raw_text = BeautifulSoup(rp_description_html, 'html.parser').get_text(separator=" ", strip=True)

                        rp_clean_description = rp_raw_text.replace("-Use", "Use").replace("–", "-").replace("—", "-")
                        for marker in cutoff_markers:
                            index = rp_clean_description.lower().find(marker.lower())
                            if index != -1:
                                rp_description = rp_clean_description[:index].strip().rstrip("-:•")
                                break
                        else:
                            rp_description = rp_clean_description.strip().rstrip("-:•")

                        obagi_data = {
                            "Product Name": name,
                            "Product Description": description,
                            "SKU": sku,
                            "Product Price": price
                        }

                        regimen_data_cleaned = {
                            "Product Name": rp_product.get("title", "No name"),
                            "Product Description": rp_description,
                            "SKU": rp_variant.get("sku", "No SKU"),
                            "Product Price": rp_variant.get("price", "No price")
                        }

                        diff_rows = compare_fields(obagi_data, regimen_data_cleaned, obagi_url, now_str)
                        comparison_rows.extend(diff_rows)
                    else:
                        print(f"⚠️ RegimenPro JSON error: {regimen_response.status_code}")

                else:
                    print(f"⚠️ Obagi JSON error: {json_response.status_code}")

            except Exception as e:
                print(f"❌ Error processing {obagi_url}: {e}")

# ==== WRITE COMPARISON FILE ====
with open(comparison_csv, 'w', newline='') as compfile:
    comp_writer = csv.DictWriter(compfile, fieldnames=comparison_fieldnames)
    comp_writer.writeheader()
    for row in comparison_rows:
        comp_writer.writerow(row)
