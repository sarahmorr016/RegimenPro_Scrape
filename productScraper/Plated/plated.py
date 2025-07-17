import csv
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from datetime import datetime

# ==== FILE PATHS ====
input_csv = "/Users/sarahmorrison/Desktop/RegimenPro/productScraper/Plated/plated_product_urls.csv"
output_csv = "/Users/sarahmorrison/Desktop/Plated_Scraped_Products.csv"
comparison_csv = "/Users/sarahmorrison/Desktop/plated_comparison.csv"

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
    "Plated Value",
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
            plated_val = source_data[key].strip()
            regimen_val = regimen_data[key].strip()

            if key == "Product Price":
                try:
                    plated_val_float = float(plated_val.replace("$", "").strip())
                    regimen_val_float = float(regimen_val.replace("$", "").strip())
                    is_match = "✅ Yes" if plated_val_float == regimen_val_float else "❌ No"
                except:
                    is_match = "⚠️ Invalid price format"
            else:
                is_match = "✅ Yes" if plated_val.lower() == regimen_val.lower() else "❌ No"

            rows.append({
                "Product URL": product_url,
                "Field": key,
                "Plated Value": plated_val,
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
            plated_url = row["Product Urls"].strip()
            regimen_url = row["RegimenPro Urls"].strip()
            print("Loaded Plated URL:", plated_url)
            print("Loaded RegimenPro URL:", regimen_url)

            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            try:
                # FIX PLATED URL → .json format
                parsed = urlparse(plated_url)
                domain = parsed.scheme + "://" + parsed.netloc
                path_parts = parsed.path.strip("/").split("/")
                if "products" in path_parts:
                    handle = path_parts[-1]
                    json_url = f"{domain}/products/{handle}.json"
                else:
                    print(f"❌ Invalid Plated URL format: {plated_url}")
                    continue

                # === GET PLATED JSON ===
                json_response = requests.get(json_url)
                print("Plated status code:", json_response.status_code)

                if json_response.status_code == 200:
                    try:
                        json_data = json_response.json()
                    except ValueError:
                        print(f"❌ JSON decoding failed for Plated URL: {json_url}")
                        print("Raw response snippet:", json_response.text[:300])
                        continue
                else:
                    print(f"⚠️ Failed to fetch Plated JSON: {json_response.status_code}")
                    continue

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

                # Save scraped data
                writer.writerow({
                    "Product URL": plated_url,
                    "Product Name": name,
                    "Product Description": description,
                    "SKU": sku,
                    "Product Price": price,
                    "Date/Time Captured": now_str
                })

                # === GET REGIMENPRO JSON ===
                regimen_response = requests.get(regimen_url + ".json")
                print("RegimenPro status code:", regimen_response.status_code)

                if regimen_response.status_code == 200:
                    try:
                        regimen_data = regimen_response.json()
                    except ValueError:
                        print(f"❌ JSON decoding failed for RegimenPro URL: {regimen_url}")
                        print("Raw response snippet:", regimen_response.text[:300])
                        continue
                else:
                    print(f"⚠️ Failed to fetch RegimenPro JSON: {regimen_response.status_code}")
                    continue

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

                plated_data = {
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

                diff_rows = compare_fields(plated_data, regimen_data_cleaned, plated_url, now_str)
                comparison_rows.extend(diff_rows)

            except Exception as e:
                print(f"❌ Error processing {plated_url}: {e}")

# ==== WRITE COMPARISON FILE ====
with open(comparison_csv, 'w', newline='') as compfile:
    comp_writer = csv.DictWriter(compfile, fieldnames=comparison_fieldnames)
    comp_writer.writeheader()
    for row in comparison_rows:
        comp_writer.writerow(row)
