import csv
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from datetime import datetime
import html

# File paths
input_csv = "/Users/sarahmorrison/Desktop/RegimenPro/productScraper/CLn_Skin_Care/CLn_Skin_Care_product_urls.csv"
output_csv = "/Users/sarahmorrison/Desktop/CLn_Scraped_Products.csv"
comparison_csv = "/Users/sarahmorrison/Desktop/cln_comparison.csv"

# Fields to extract and compare
fieldnames = [
    "Product URL",
    "Product Name",
    "Product Description",
    "SKU",
    "Product Price",
    "Ingredients",
    "Date/Time Captured"
]

comparison_fieldnames = [
    "Product URL",
    "Shopify Admin URL",
    "Field",
    "CLn Skin Care Value",
    "RegimenPro Value",
    "Match?",
    "Date/Time Captured"
]

comparison_rows = []
cln_cache = {}

def compare_fields(cln_data, regimen_data, product_url, shopify_admin_url, timestamp):
    rows = []
    for key in cln_data:
        if key in regimen_data:
            cln_val = cln_data[key].strip()
            regimen_val = regimen_data[key].strip()

            if key == "Product Price":
                try:
                    cln_float = float(cln_val.replace("$", "").strip())
                    regimen_float = float(regimen_val.replace("$", "").strip())
                    is_match = "✅ Yes" if cln_float == regimen_float else "❌ No"
                except:
                    is_match = "⚠️ Invalid price format"
            else:
                is_match = "✅ Yes" if cln_val.lower() == regimen_val.lower() else "❌ No"

            rows.append({
                "Product URL": product_url,
                "Shopify Admin URL": shopify_admin_url,
                "Field": key,
                "CLn Skin Care Value": cln_val,
                "RegimenPro Value": regimen_val,
                "Match?": is_match,
                "Date/Time Captured": timestamp
            })
    return rows

# Write scraped output
with open(output_csv, 'w', newline='') as outfile:
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()

    with open(input_csv, mode="r", newline='') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            cln_url = row["Product Urls"].strip()
            regimen_url = row["RegimenPro Urls"].strip()
            regimen_size = row.get("RegimenPro Size", "").strip()

            print("\n--- Processing ---")
            print("CLn Skin Care URL:", cln_url)
            print("RegimenPro URL:", regimen_url)
            if regimen_size:
                print("Expected Size:", regimen_size)
            else:
                print("No size provided — will use default CLn variant")

            cln_name = cln_description = cln_price = cln_sku = ingredients = "Not found"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            try:
                if cln_url not in cln_cache:
                    cln_json_url = cln_url.split("?")[0] + ".json"
                    cln_response = requests.get(cln_json_url)
                    if cln_response.status_code == 200:
                        cln_data = cln_response.json()
                        cln_cache[cln_url] = cln_data["product"]
                    else:
                        print("❌ Failed to fetch CLn JSON. Status:", cln_response.status_code)
                        continue

                cln_product = cln_cache[cln_url]
                cln_name = cln_product.get("title", "No name")

                # Match variant by size
                matched_variant = None
                if regimen_size:
                    for variant in cln_product.get("variants", []):
                        if variant.get("title", "").strip() == regimen_size:
                            matched_variant = variant
                            break

                if not matched_variant:
                    print(f"⚠️ No matching size found for '{regimen_size}' — using default variant.")
                    matched_variant = cln_product["variants"][0]

                cln_sku = matched_variant.get("sku", "No SKU")
                cln_price = matched_variant.get("price", "No price")

                raw_html = cln_product.get("body_html", "")
                decoded_html = html.unescape(raw_html)
                soup = BeautifulSoup(decoded_html, 'html.parser')

                # Description (all text)
                cln_description = soup.get_text(separator=" ", strip=True)

                # Ingredients (specifically from table)
                ingredients = "Not found"
                ing_row = soup.find("th", string=lambda s: s and "ingredient" in s.lower())
                if ing_row and ing_row.find_next_sibling("td"):
                    ingredients = ing_row.find_next_sibling("td").get_text(strip=True)

            except Exception as e:
                print(f"❌ Error loading CLn JSON for {cln_url}: {e}")
                continue

            # ✅ Write to output CSV
            writer.writerow({
                "Product URL": cln_url,
                "Product Name": cln_name,
                "Product Description": cln_description,
                "SKU": cln_sku,
                "Product Price": cln_price,
                "Ingredients": ingredients,
                "Date/Time Captured": timestamp
            })

            # Compare to RegimenPro
            try:
                regimen_json_url = regimen_url + ".json"
                regimen_response = requests.get(regimen_json_url)
                if regimen_response.status_code == 200:
                    regimen_data = regimen_response.json()
                    regimen_product = regimen_data["product"]
                    regimen_name = regimen_product.get("title", "No name")
                    regimen_sku = regimen_product["variants"][0].get("sku", "No SKU")
                    regimen_price = regimen_product["variants"][0].get("price", "No price")

                    raw_html = regimen_product.get("body_html", "")
                    decoded_html = html.unescape(raw_html)
                    soup = BeautifulSoup(decoded_html, 'html.parser')
                    regimen_description = soup.get_text(separator=" ", strip=True)

                    shopify_product_id = regimen_product.get("id", "")
                    shopify_admin_url = f"https://admin.shopify.com/store/regimenmd/products/{shopify_product_id}"

                    cln_scraped = {
                        "Product Name": cln_name,
                        "Product Description": cln_description,
                        "SKU": cln_sku,
                        "Product Price": cln_price
                    }

                    regimen_scraped = {
                        "Product Name": regimen_name,
                        "Product Description": regimen_description,
                        "SKU": regimen_sku,
                        "Product Price": regimen_price
                    }

                    comparison_rows.extend(compare_fields(
                        cln_scraped, regimen_scraped, cln_url, shopify_admin_url, timestamp
                    ))

                else:
                    print("❌ Failed to fetch RegimenPro JSON. Status:", regimen_response.status_code)

            except Exception as e:
                print(f"❌ Error loading RegimenPro JSON for {regimen_url}: {e}")

# Write comparison CSV
with open(comparison_csv, 'w', newline='') as compfile:
    writer = csv.DictWriter(compfile, fieldnames=comparison_fieldnames)
    writer.writeheader()
    for row in comparison_rows:
        writer.writerow(row)
