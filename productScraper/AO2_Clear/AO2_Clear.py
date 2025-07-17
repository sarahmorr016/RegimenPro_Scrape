import csv
import requests
from bs4 import BeautifulSoup
import json
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
}

# File paths
input_csv = "/Users/sarahmorrison/Desktop/RegimenPro/productScraper/AO2_Clear/ao2_clear_product_urls.csv"
output_csv = "/Users/sarahmorrison/Desktop/AO2_Scraped_Products.csv"
comparison_csv = "/Users/sarahmorrison/Desktop/ao2_comparison.csv"

# Fields
fieldnames = [
    "Product URL",
    "Product Name",
    "Product Description",
    "SKU",
    "Product Price",
    "Ingredients"
]

comparison_fieldnames = [
    "Product URL",
    "Field",
    "AO2 Clear Value",
    "RegimenPro Value",
    "Match?"
]

comparison_rows = []

def normalize_text(s):
    return s.strip().lower().replace('\n', '').replace('\r', '') if s else "N/A"

# Open output CSV for AO2 Clear data
with open(output_csv, 'w', newline='') as outfile:
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()

    # Read input URLs
    with open(input_csv, mode="r", newline='') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            ao2_url = row["Product Urls"]
            regimenpro_url = row["RegimenPro Urls"]
            print("Loaded URL:", ao2_url)

            # --- Scrape AO2 Clear ---
            ao2_data = {
                "Product URL": ao2_url,
                "Product Name": "N/A",
                "Product Description": "N/A",
                "SKU": "N/A",
                "Product Price": "N/A",
                "Ingredients": "N/A"
            }

            try:
                ao2_response = requests.get(ao2_url, headers=HEADERS, timeout=10)
                ao2_soup = BeautifulSoup(ao2_response.text, 'html.parser')

                h1 = ao2_soup.find("h1")
                if h1:
                    ao2_data["Product Name"] = normalize_text(h1.text)

                desc_tag = ao2_soup.find("div", class_="woocommerce-product-details__short-description")
                if desc_tag:
                    ao2_data["Product Description"] = normalize_text(desc_tag.get_text())

                price_container = ao2_soup.find("span", class_="woocommerce-Price-amount")
                if price_container:
                    bdi = price_container.find("bdi")
                    if bdi:
                        # Get all text nodes inside <bdi> and remove currency symbols
                        raw_price = ''.join(bdi.find_all(string=True)).strip()
                        ao2_data["Product Price"] = normalize_text(raw_price.replace('$', '').replace(',', ''))
                        print("AO2 Raw Price Text:", raw_price)

                sku_tag = ao2_soup.find("span", class_="sku")
                if sku_tag:
                    ao2_data["SKU"] = normalize_text(sku_tag.text)

                ingredients_header = ao2_soup.find("h2", string=lambda s: s and "ingredients" in s.lower())
                if ingredients_header:
                    ingredients_div = ingredients_header.find_next("div")
                    if ingredients_div:
                        ao2_data["Ingredients"] = normalize_text(ingredients_div.get_text())

            except Exception as e:
                print("AO2 Clear error:", e)

            # Write AO2 data row
            writer.writerow(ao2_data)

            # --- Scrape RegimenPro JSON ---
            regimenpro_data = {
                "Product Name": "N/A",
                "Product Description": "N/A",
                "SKU": "N/A",
                "Product Price": "N/A",
                "Ingredients": "N/A"
            }

            try:
                rp_response = requests.get(regimenpro_url, timeout=10)
                rp_soup = BeautifulSoup(rp_response.text, "html.parser")

                # Look for embedded Shopify product JSON
                product_json = None
                for script in rp_soup.find_all("script"):
                    if script.string and "Shopify.product = " in script.string:
                        match = re.search(r"Shopify\.product\s*=\s*({.*?});", script.string, re.DOTALL)
                        if match:
                            product_json = json.loads(match.group(1))
                            break

                if product_json:
                    regimenpro_data["Product Name"] = normalize_text(product_json.get("title", "N/A"))

                    html_blob = product_json.get("body_html", "")
                    if html_blob:
                        soup_blob = BeautifulSoup(html_blob, "html.parser")
                        regimenpro_data["Product Description"] = normalize_text(soup_blob.get_text())

                        ingredients_header = soup_blob.find(string=lambda s: "ingredient" in s.lower())
                        if ingredients_header:
                            parent = ingredients_header.find_parent()
                            if parent:
                                next_elem = parent.find_next()
                                if next_elem:
                                    regimenpro_data["Ingredients"] = normalize_text(next_elem.get_text())

                    variant = product_json.get("variants", [{}])[0]
                    regimenpro_data["Product Price"] = normalize_text(str(variant.get("price", "N/A")))
                    regimenpro_data["SKU"] = normalize_text(variant.get("sku", "N/A"))

            except Exception as e:
                print("RegimenPro JSON error:", e)

            # --- Compare and store ---
            for field in fieldnames[1:]:
                val1 = ao2_data[field]
                val2 = regimenpro_data[field]
                comparison_rows.append({
                    "Product URL": ao2_url,
                    "Field": field,
                    "AO2 Clear Value": val1,
                    "RegimenPro Value": val2,
                    "Match?": "✅" if normalize_text(val1) == normalize_text(val2) else "❌"
                })

# --- Write comparison file ---
with open(comparison_csv, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=comparison_fieldnames)
    writer.writeheader()
    writer.writerows(comparison_rows)
