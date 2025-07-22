import csv
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from datetime import datetime

# === File paths ===
input_csv = "/Users/sarahmorrison/Desktop/RegimenPro/productScraper/Rationale/rationale_product_urls.csv"
output_csv = "/Users/sarahmorrison/Desktop/Rationale_Scraped_Products.csv"
comparison_csv = "/Users/sarahmorrison/Desktop/rationale_comparison.csv"

# === Output Fields ===
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
    "Rationale Value",
    "RegimenPro Value",
    "Match?",
    "Date/Time Captured"
]

comparison_rows = []

# === Description extraction ===
def extract_description(body_html):
    try:
        soup = BeautifulSoup(body_html, "html.parser")
        paragraphs = soup.find_all("p")
        if paragraphs:
            return paragraphs[0].get_text(strip=True)
        return soup.get_text(strip=True)  # fallback to all text
    except Exception as e:
        print("Error extracting description:", e)
        return "No description"

# === Field comparison ===
def compare_fields(rationale_data, regimen_data, product_url, timestamp):
    rows = []
    for key in rationale_data:
        if key in regimen_data:
            val1 = rationale_data[key].strip()
            val2 = regimen_data[key].strip()

            if key == "Product Price":
                try:
                    v1 = float(val1.replace("$", "").strip())
                    v2 = float(val2.replace("$", "").strip())
                    match = "✅ Yes" if v1 == v2 else "❌ No"
                except:
                    match = "⚠️ Invalid format"
            else:
                match = "✅ Yes" if val1.lower() == val2.lower() else "❌ No"

            rows.append({
                "Product URL": product_url,
                "Field": key,
                "Rationale Value": val1,
                "RegimenPro Value": val2,
                "Match?": match,
                "Date/Time Captured": timestamp
            })
    return rows

# === Main Script ===
with open(output_csv, 'w', newline='') as outfile:
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()

    with open(input_csv, mode="r", newline='') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            rationale_url = row["Product Urls"].strip()
            regimen_url = row["RegimenPro Urls"].strip()
            print("Loaded Rationale URL:", rationale_url)
            print("Loaded RegimenPro URL:", regimen_url)

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            name = description = price = sku = "N/A"

            try:
                # === Rationale JSON ===
                parsed = urlparse(rationale_url)
                clean_url = parsed.scheme + "://" + parsed.netloc + parsed.path
                json_url = clean_url + ".json"
                res = requests.get(json_url)
                if res.status_code == 200:
                    product = res.json()["product"]
                    name = product.get("title", "N/A").strip()
                    description = extract_description(product.get("body_html", ""))
                    price = product["variants"][0].get("price", "N/A")
                    sku = product["variants"][0].get("sku", "No SKU")
                else:
                    print(f"Failed to retrieve Rationale JSON for {rationale_url}")

                # === Write scraped Rationale data ===
                writer.writerow({
                    "Product URL": rationale_url,
                    "Product Name": name,
                    "Product Description": description,
                    "SKU": sku,
                    "Product Price": price,
                    "Date/Time Captured": timestamp
                })

                # === RegimenPro JSON ===
                regimen_json_url = regimen_url + ".json"
                res2 = requests.get(regimen_json_url)
                if res2.status_code == 200:
                    regimen_product = res2.json().get("product", {})
                    rp_name = regimen_product.get("title", "N/A").strip()
                    rp_description = extract_description(regimen_product.get("body_html", ""))
                    rp_price = regimen_product["variants"][0].get("price", "N/A")
                    rp_sku = regimen_product["variants"][0].get("sku", "No SKU")

                    rationale_data = {
                        "Product Name": name,
                        "Product Description": description,
                        "SKU": sku,
                        "Product Price": price
                    }

                    regimen_data = {
                        "Product Name": rp_name,
                        "Product Description": rp_description,
                        "SKU": rp_sku,
                        "Product Price": rp_price
                    }

                    rows = compare_fields(rationale_data, regimen_data, rationale_url, timestamp)
                    comparison_rows.extend(rows)
                else:
                    print(f"Failed to retrieve RegimenPro JSON: {res2.status_code}")

            except Exception as e:
                print(f"Error processing {rationale_url}: {e}")

# === Write comparison CSV ===
with open(comparison_csv, 'w', newline='') as compfile:
    writer = csv.DictWriter(compfile, fieldnames=comparison_fieldnames)
    writer.writeheader()
    writer.writerows(comparison_rows)
