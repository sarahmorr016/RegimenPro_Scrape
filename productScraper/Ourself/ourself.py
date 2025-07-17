import csv
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from datetime import datetime

# ==== FILE PATHS ====
input_csv = "/Users/sarahmorrison/Desktop/RegimenPro/productScraper/Ourself/Ourself_product_urls.csv"
output_csv = "/Users/sarahmorrison/Desktop/Ourself_Scraped_Products.csv"
comparison_csv = "/Users/sarahmorrison/Desktop/ourself_comparison.csv"

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
    "Ourself Value",
    "RegimenPro Value",
    "Match?",
    "Date/Time Captured"
]

comparison_rows = []
cutoff_phrases = ["ingredients", "directions", "how to use", "usage", "use instructions", "available in", "tints"]

# ==== COMPARISON FUNCTION ====
def compare_fields(source_data, regimen_data, product_url, timestamp):
    rows = []
    for key in source_data:
        if key in regimen_data:
            val1 = source_data[key].strip().rstrip("-:• ")
            val2 = regimen_data[key].strip().rstrip("-:• ")

            if key == "Product Price":
                try:
                    val1_f = float(val1.replace("$", "").strip())
                    val2_f = float(val2.replace("$", "").strip())
                    is_match = "✅ Yes" if val1_f == val2_f else "❌ No"
                except:
                    is_match = "⚠️ Invalid price format"
            else:
                is_match = "✅ Yes" if val1.lower() == val2.lower() else "❌ No"

            rows.append({
                "Product URL": product_url,
                "Field": key,
                "Ourself Value": val1,
                "RegimenPro Value": val2,
                "Match?": is_match,
                "Date/Time Captured": timestamp
            })
    return rows

# ==== MAIN SCRIPT ====
with open(output_csv, 'w', newline='') as outfile:
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()

    with open(input_csv, mode="r", newline='') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            ourself_url = row["Product Urls"].strip()
            regimen_url = row["RegimenPro Urls"].strip()
            print("Loaded Ourself URL:", ourself_url)
            print("Loaded RegimenPro URL:", regimen_url)

            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            try:
                # === OURSELF PRODUCT ===
                parsed = urlparse(ourself_url)
                clean_path = parsed.scheme + "://" + parsed.netloc + parsed.path
                json_url = clean_path + ".json"
                json_response = requests.get(json_url)
                if json_response.status_code == 200:
                    json_data = json_response.json()
                    product = json_data["product"]
                    variant = product["variants"][0]

                    name = product.get("title", "No name")
                    sku = variant.get("sku", "No SKU")
                    price = variant.get("price", "No price")

                    # Extract description using <p> method
                    description_html = product.get("body_html", "")
                    soup = BeautifulSoup(description_html, 'html.parser')
                    description = "No description found"
                    for p in soup.find_all("p"):
                        text = p.get_text(strip=True)
                        if not any(phrase in text.lower() for phrase in cutoff_phrases):
                            description = text.strip().rstrip("-:•")
                            break

                    writer.writerow({
                        "Product URL": ourself_url,
                        "Product Name": name,
                        "Product Description": description,
                        "SKU": sku,
                        "Product Price": price,
                        "Date/Time Captured": now_str
                    })

                    # === REGIMENPRO PRODUCT ===
                    regimen_response = requests.get(regimen_url + ".json")
                    if regimen_response.status_code == 200:
                        rp_data = regimen_response.json()
                        rp_product = rp_data["product"]
                        rp_variant = rp_product["variants"][0]

                        rp_name = rp_product.get("title", "No name")
                        rp_sku = rp_variant.get("sku", "No SKU")
                        rp_price = rp_variant.get("price", "No price")

                        # RegimenPro: extract full raw text, then cut off at known section headings
                        rp_html = rp_product.get("body_html", "")
                        rp_raw = BeautifulSoup(rp_html, 'html.parser').get_text(separator=" ", strip=True)
                        rp_clean = rp_raw.replace("-Use", "Use").replace("–", "-").replace("—", "-")

                        rp_description = rp_clean
                        for marker in cutoff_phrases:
                            index = rp_clean.lower().find(marker.lower())
                            if index != -1:
                                rp_description = rp_clean[:index].strip().rstrip("-:•")
                                break

                        # Build row data
                        ourself_data = {
                            "Product Name": name,
                            "Product Description": description,
                            "SKU": sku,
                            "Product Price": price
                        }

                        regimen_data_cleaned = {
                            "Product Name": rp_name,
                            "Product Description": rp_description,
                            "SKU": rp_sku,
                            "Product Price": rp_price
                        }

                        # Compare
                        diff_rows = compare_fields(ourself_data, regimen_data_cleaned, ourself_url, now_str)
                        comparison_rows.extend(diff_rows)
                    else:
                        print(f"⚠️ RegimenPro JSON error: {regimen_response.status_code}")
                else:
                    print(f"⚠️ Ourself JSON error: {json_response.status_code}")
            except Exception as e:
                print(f"❌ Error processing {ourself_url}: {e}")

# ==== WRITE COMPARISON FILE ====
with open(comparison_csv, 'w', newline='') as compfile:
    comp_writer = csv.DictWriter(compfile, fieldnames=comparison_fieldnames)
    comp_writer.writeheader()
    for row in comparison_rows:
        comp_writer.writerow(row)
