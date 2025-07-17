import csv
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from datetime import datetime
import html

# File paths
input_csv = "/Users/sarahmorrison/Desktop/RegimenPro/productScraper/MM_Skincare/MM_Skincare_product_urls.csv"
output_csv = "/Users/sarahmorrison/Desktop/MM_Skincare_Scraped_Products.csv"
comparison_csv = "/Users/sarahmorrison/Desktop/mm_skincare_comparison.csv"

# Fields to extract and compare
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
    "Shopify Admin URL",
    "Field",
    "MM Skincare Value",
    "RegimenPro Value",
    "Match?",
    "Date/Time Captured"
]

comparison_rows = []

def compare_fields(mm_data, regimen_data, product_url, shopify_admin_url, timestamp):
    rows = []
    for key in mm_data:
        if key in regimen_data:
            mm_val = mm_data[key].strip()
            regimen_val = regimen_data[key].strip()

            if key == "Product Price":
                try:
                    mm_float = float(mm_val.replace("$", "").strip())
                    regimen_float = float(regimen_val.replace("$", "").strip())
                    is_match = "✅ Yes" if mm_float == regimen_float else "❌ No"
                except:
                    is_match = "⚠️ Invalid price format"
            else:
                is_match = "✅ Yes" if mm_val.lower() == regimen_val.lower() else "❌ No"

            rows.append({
                "Product URL": product_url,
                "Shopify Admin URL": shopify_admin_url,
                "Field": key,
                "MM Skincare Value": mm_val,
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
            mm_url = row["Product Urls"].strip()
            regimen_url = row["RegimenPro Urls"].strip()

            print("\n--- Processing ---")
            print("MM Skincare URL:", mm_url)
            print("RegimenPro URL:", regimen_url)

            mm_name = mm_description = mm_price = mm_sku = "Not found"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            try:
                mm_json_url = mm_url + ".json"
                mm_response = requests.get(mm_json_url)
                if mm_response.status_code == 200:
                    mm_data = mm_response.json()
                    product = mm_data["product"]
                    mm_name = product.get("title", "No name")
                    mm_sku = product["variants"][0].get("sku", "No SKU")
                    mm_price = product["variants"][0].get("price", "No price")

                    raw_html = product.get("body_html", "")
                    decoded_html = html.unescape(raw_html)
                    soup = BeautifulSoup(decoded_html, 'html.parser')
                    mm_description = soup.get_text(separator=" ", strip=True)

                else:
                    print("❌ Failed to fetch MM JSON. Status:", mm_response.status_code)
                    continue

            except Exception as e:
                print(f"❌ Error loading MM JSON for {mm_url}: {e}")
                continue

            # ✅ Write to output CSV
            writer.writerow({
                "Product URL": mm_url,
                "Product Name": mm_name,
                "Product Description": mm_description,
                "SKU": mm_sku,
                "Product Price": mm_price,
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

                    mm_scraped = {
                        "Product Name": mm_name,
                        "Product Description": mm_description,
                        "SKU": mm_sku,
                        "Product Price": mm_price
                    }

                    regimen_scraped = {
                        "Product Name": regimen_name,
                        "Product Description": regimen_description,
                        "SKU": regimen_sku,
                        "Product Price": regimen_price
                    }

                    comparison_rows.extend(compare_fields(
                        mm_scraped, regimen_scraped, mm_url, shopify_admin_url, timestamp
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
