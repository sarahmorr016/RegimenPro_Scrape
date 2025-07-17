import csv
import json
import requests
from bs4 import BeautifulSoup
import html
from datetime import datetime
from difflib import SequenceMatcher

# File paths
input_csv = "/Users/sarahmorrison/Desktop/RegimenPro/productScraper/Lumisque/Lumisque_product_urls.csv"
output_csv = "/Users/sarahmorrison/Desktop/Lumisque_Scraped_Products.csv"
comparison_csv = "/Users/sarahmorrison/Desktop/Lumisque_Comparison.csv"

FIELDS = [
    "Product Name",
    "Product Description",
    "SKU",
    "Product Price"
]

def extract_json_data(url, append_json=True):
    try:
        full_url = url + ".json" if append_json else url
        response = requests.get(full_url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Failed to fetch JSON from {url}: {e}")
        return None

def parse_product_data(json_data):
    try:
        product = json_data["product"]
        title = product.get("title", "").strip()
        sku = product["variants"][0].get("sku", "").strip()
        price = product["variants"][0].get("price", "").strip()

        raw_html = product.get("body_html", "")
        decoded_html = html.unescape(raw_html)
        soup = BeautifulSoup(decoded_html, "html.parser")
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

def fuzzy_match(str1, str2, threshold=0.8):
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio() >= threshold

def compare_fields(lumisque_data, regimen_data):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    comparison = []

    for field in FIELDS:
        lum_val = lumisque_data.get(field, "N/A")
        reg_val = regimen_data.get(field, "N/A")

        if field in ["Product Name", "Product Description"]:
            match = "✅ Yes" if fuzzy_match(lum_val, reg_val) else "❌ No"
        else:
            match = "✅ Yes" if lum_val.strip() == reg_val.strip() else "❌ No"

        comparison.append({
            "Field": field,
            "Lumisque Value": lum_val,
            "RegimenPro Value": reg_val,
            "Match?": match,
            "Date/Time Captured": timestamp
        })

    return comparison

def main():
    scraped_data = []
    comparison_data = []

    with open(input_csv, newline='') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            manu_url = row["Product Urls"].strip()
            reg_url = row["RegimenPro Urls"].strip()

            print("🔄 Processing:")
            print("Lumisque URL:", manu_url)
            print("RegimenPro URL:", reg_url)

            # No need to strip for Lumisque
            manu_json = extract_json_data(manu_url, append_json=True)
            reg_json = extract_json_data(reg_url, append_json=True)

            manu_data = parse_product_data(manu_json) if manu_json else {field: "N/A" for field in FIELDS}
            reg_data = parse_product_data(reg_json) if reg_json else {field: "N/A" for field in FIELDS}

            scraped_row = {
                "Product URL": manu_url,
                **manu_data,
                "Date/Time Captured": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            scraped_data.append(scraped_row)

            shopify_product_id = reg_json["product"]["id"] if reg_json else ""
            shopify_admin_url = f"https://admin.shopify.com/store/regimenmd/products/{shopify_product_id}"

            for comp in compare_fields(manu_data, reg_data):
                comp["Product URL"] = manu_url
                comp["Shopify Admin URL"] = shopify_admin_url
                comparison_data.append(comp)

    # Save scraped CSV
    with open(output_csv, "w", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["Product URL"] + FIELDS + ["Date/Time Captured"])
        writer.writeheader()
        writer.writerows(scraped_data)

    # Save comparison CSV
    with open(comparison_csv, "w", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            "Product URL", "Shopify Admin URL", "Field",
            "Lumisque Value", "RegimenPro Value", "Match?", "Date/Time Captured"
        ])
        writer.writeheader()
        writer.writerows(comparison_data)

    print("\n✅ DONE! Files saved:")
    print(" -", output_csv)
    print(" -", comparison_csv)

if __name__ == "__main__":
    main()
