import csv
import json
import requests
from bs4 import BeautifulSoup
import html
from datetime import datetime

# File paths (update to your local file locations)
input_csv = "/Users/sarahmorrison/Desktop/RegimenPro/productScraper/Dermasensa/Dermasensa_product_urls.csv"
output_csv = "/Users/sarahmorrison/Desktop/Dermasensa_Scraped_Products.csv"
comparison_csv = "/Users/sarahmorrison/Desktop/Dermasensa_comparison.csv"

# Fields to extract
FIELDS = [
    "Product Name",
    "Product Description",
    "SKU",
    "Product Price",
    "Ingredients",
    "Usage Instructions",
    "Expert Tip"
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
        ingredients = usage = expert_tip = "N/A"

        raw_html = product.get("body_html", "")
        decoded_html = html.unescape(raw_html)
        soup = BeautifulSoup(decoded_html, 'html.parser')

        # Description from <p> tags
        p_tags = soup.find_all("p")
        description = " ".join(p.get_text(strip=True) for p in p_tags)

        # Accordion info from <dt>/<dd>
        for dt in soup.find_all("dt"):
            label = dt.get_text(strip=True).lower()
            dd = dt.find_next_sibling("dd")
            if not dd:
                continue
            value = dd.get_text(strip=True)
            if "expert" in label:
                expert_tip = value
            elif "use" in label:
                usage = value
            elif "ingredient" in label:
                ingredients = value

        return {
            "Product Name": title,
            "Product Description": description,
            "SKU": sku,
            "Product Price": price,
            "Ingredients": ingredients,
            "Usage Instructions": usage,
            "Expert Tip": expert_tip
        }
    except Exception as e:
        print(f"Error parsing product data: {e}")
        return {field: "N/A" for field in FIELDS}

def compare_fields(d_data, r_data):
    comparison_rows = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for field in ["Product Name", "Product Description", "SKU", "Product Price"]:
        derm_val = d_data.get(field, "N/A")
        reg_val = r_data.get(field, "N/A")
        match = "✅ Yes" if derm_val.strip() == reg_val.strip() else "❌ No"
        comparison_rows.append({
            "Field": field,
            "Dermasensa Value": derm_val,
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
            derm_url = row["Product Urls"].strip()
            reg_url = row["RegimenPro Urls"].strip()

            print("\n--- Processing ---")
            print("Dermasensa URL:", derm_url)
            print("RegimenPro URL:", reg_url)

            derm_data_raw = extract_json_data(derm_url)
            reg_data_raw = extract_json_data(reg_url)

            derm_data = parse_product_data(derm_data_raw) if derm_data_raw else {field: "N/A" for field in FIELDS}
            reg_data = parse_product_data(reg_data_raw) if reg_data_raw else {field: "N/A" for field in FIELDS}

            # Scraped output
            derm_data_row = {
                "Product URL": derm_url,
                **derm_data,
                "Date/Time Captured": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            scraped_rows.append(derm_data_row)

            # Shopify Admin URL
            shopify_product_id = reg_data_raw["product"].get("id", "") if reg_data_raw else ""
            shopify_admin_url = f"https://admin.shopify.com/store/regimenmd/products/{shopify_product_id}"

            # Comparison output
            per_product_comparison = compare_fields(derm_data, reg_data)
            for entry in per_product_comparison:
                entry["Product URL"] = derm_url
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
            "Product URL", "Shopify Admin URL", "Field", "Dermasensa Value", "RegimenPro Value", "Match?", "Date/Time Captured"
        ])
        writer.writeheader()
        writer.writerows(comparison_rows)

    print("✅ Done! Files saved to:")
    print("   -", output_csv)
    print("   -", comparison_csv)

if __name__ == "__main__":
    main()
