import csv
import json
import requests
from bs4 import BeautifulSoup
import html
from datetime import datetime

# File paths (update for EltaMD)
input_csv = "/Users/sarahmorrison/Desktop/RegimenPro/productScraper/EltaMD/EltaMD_product_urls.csv"
output_csv = "/Users/sarahmorrison/Desktop/EltaMD_Scraped_Products.csv"
comparison_csv = "/Users/sarahmorrison/Desktop/EltaMD_comparison.csv"

FIELDS = [
    "Product Name",
    "Product Description",
    "SKU",
    "Product Price"
]

def extract_json_data(url):
    try:
        response = requests.get(url + ".json")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Failed to get JSON from {url}: {e}")
        return None

def parse_product_data(json_data):
    try:
        product = json_data["product"]
        title = product.get("title", "").strip()
        sku = product["variants"][0].get("sku", "").strip()
        price = product["variants"][0].get("price", "").strip()

        raw_html = product.get("body_html", "")
        decoded_html = html.unescape(raw_html)
        soup = BeautifulSoup(decoded_html, 'html.parser')

        # Extract visible text from body_html
        full_text = soup.get_text(separator=" ", strip=True)

        return {
            "Product Name": title,
            "Product Description": full_text,
            "SKU": sku,
            "Product Price": price
        }
    except Exception as e:
        print(f"Error parsing product data: {e}")
        return {field: "N/A" for field in FIELDS}

def compare_fields(manu_data, regimen_data):
    comparison_rows = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for field in FIELDS:
        manu_val = manu_data.get(field, "N/A")
        reg_val = regimen_data.get(field, "N/A")
        match = "✅ Yes" if manu_val.strip() == reg_val.strip() else "❌ No"
        comparison_rows.append({
            "Field": field,
            "EltaMD Value": manu_val,
            "RegimenPro Value": reg_val,
            "Match?": match,
            "Date/Time Captured": timestamp
        })
    return comparison_rows

def main():
    scraped_rows = []
    comparison_rows = []

    with open(input_csv, newline='') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            manu_url = row["Product Urls"].strip()
            reg_url = row["RegimenPro Urls"].strip()

            print("\n--- Processing ---")
            print("EltaMD URL:", manu_url)
            print("RegimenPro URL:", reg_url)

            manu_data_raw = extract_json_data(manu_url)
            reg_data_raw = extract_json_data(reg_url)

            manu_data = parse_product_data(manu_data_raw) if manu_data_raw else {field: "N/A" for field in FIELDS}
            reg_data = parse_product_data(reg_data_raw) if reg_data_raw else {field: "N/A" for field in FIELDS}

            manu_data_row = {
                "Product URL": manu_url,
                **manu_data,
                "Date/Time Captured": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            scraped_rows.append(manu_data_row)

            shopify_product_id = reg_data_raw["product"].get("id", "") if reg_data_raw else ""
            shopify_admin_url = f"https://admin.shopify.com/store/regimenmd/products/{shopify_product_id}"

            per_product_comparison = compare_fields(manu_data, reg_data)
            for entry in per_product_comparison:
                entry["Product URL"] = manu_url
                entry["Shopify Admin URL"] = shopify_admin_url
            comparison_rows.extend(per_product_comparison)

    # Write scraped CSV
    with open(output_csv, "w", newline='') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=["Product URL"] + FIELDS + ["Date/Time Captured"])
        writer.writeheader()
        writer.writerows(scraped_rows)

    # Write comparison CSV
    with open(comparison_csv, "w", newline='') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=[
            "Product URL", "Shopify Admin URL", "Field", "EltaMD Value", "RegimenPro Value", "Match?", "Date/Time Captured"
        ])
        writer.writeheader()
        writer.writerows(comparison_rows)

    print("✅ Done! Files saved to:")
    print("   -", output_csv)
    print("   -", comparison_csv)

if __name__ == "__main__":
    main()
