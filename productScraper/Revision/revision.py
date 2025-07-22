import csv
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from datetime import datetime
from difflib import SequenceMatcher
import unicodedata
import html

# === File paths ===
input_csv = "/Users/sarahmorrison/Desktop/RegimenPro/productScraper/Revision/revision_product_urls.csv"
output_csv = "/Users/sarahmorrison/Desktop/Revision_Scraped_Products.csv"
comparison_csv = "/Users/sarahmorrison/Desktop/revision_comparison.csv"

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
    "Revision Value",
    "RegimenPro Value",
    "Match?",
    "Date/Time Captured"
]

comparison_rows = []

# === Normalize strings (preserve leading 0s) ===
def normalize_string(s):
    return ' '.join(unicodedata.normalize("NFKD", str(s)).strip().split())

# === Strip product name from beginning of description & decode HTML ===
def extract_description(body_html, product_name=""):
    try:
        soup = BeautifulSoup(html.unescape(body_html), "html.parser")
        paragraphs = soup.find_all("p")
        text = paragraphs[0].get_text(strip=True) if paragraphs else soup.get_text(strip=True)
        if product_name and text.lower().startswith(product_name.lower()):
            return text[len(product_name):].lstrip(" :–-").strip()
        return text
    except Exception as e:
        print("Error extracting description:", e)
        return "No description"

# === Compare fields ===
def compare_fields(revision_data, regimen_data, product_url, timestamp):
    rows = []
    for key in revision_data:
        if key in regimen_data:
            val1 = normalize_string(revision_data[key])
            val2 = normalize_string(regimen_data[key])

            if key == "Product Price":
                try:
                    v1 = float(val1.replace("$", "").replace(",", ""))
                    v2 = float(val2.replace("$", "").replace(",", ""))
                    match = "✅ Yes" if v1 == v2 else "❌ No"
                except:
                    match = "⚠️ Invalid format"
            elif key == "Product Description":
                ratio = SequenceMatcher(None, val1.lower(), val2.lower()).ratio()
                match = "✅ Yes" if ratio > 0.85 else f"❌ No ({round(ratio * 100)}% match)"
            else:
                match = "✅ Yes" if val1 == val2 else "❌ No"

            rows.append({
                "Product URL": product_url,
                "Field": key,
                "Revision Value": val1,
                "RegimenPro Value": val2,
                "Match?": match,
                "Date/Time Captured": timestamp
            })
    return rows

# === Main execution ===
with open(output_csv, 'w', newline='') as outfile:
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()

    with open(input_csv, mode="r", newline='') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            revision_url = row["Product Urls"].strip()
            regimen_url = row["RegimenPro Urls"].strip()
            print("Loaded Revision URL:", revision_url)
            print("Loaded RegimenPro URL:", regimen_url)

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            name = description = price = sku = "N/A"

            try:
                # === Revision scrape ===
                parsed = urlparse(revision_url)
                clean_url = parsed.scheme + "://" + parsed.netloc + parsed.path
                json_url = clean_url + ".json"
                res = requests.get(json_url)
                if res.status_code == 200:
                    product = res.json()["product"]
                    name = product.get("title", "N/A").strip()
                    description = extract_description(product.get("body_html", ""), name)
                    price = str(product["variants"][0].get("price", "N/A"))
                    sku = str(product["variants"][0].get("sku", "No SKU"))
                else:
                    print(f"❌ Failed to retrieve Revision JSON for {revision_url} - {res.status_code}")

                writer.writerow({
                    "Product URL": str(revision_url),
                    "Product Name": str(name),
                    "Product Description": str(description),
                    "SKU": str(sku),
                    "Product Price": str(price),
                    "Date/Time Captured": str(timestamp)
                })

                # === RegimenPro scrape ===
                regimen_json_url = regimen_url + ".json"
                res2 = requests.get(regimen_json_url)
                if res2.status_code == 200:
                    regimen_product = res2.json().get("product", {})
                    rp_name = regimen_product.get("title", "N/A").strip()
                    rp_description = extract_description(regimen_product.get("body_html", ""), rp_name)
                    rp_price = str(regimen_product["variants"][0].get("price", "N/A"))
                    rp_sku = str(regimen_product["variants"][0].get("sku", "No SKU"))

                    revision_data = {
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

                    rows = compare_fields(revision_data, regimen_data, revision_url, timestamp)
                    comparison_rows.extend(rows)
                else:
                    print(f"❌ Failed to retrieve RegimenPro JSON for {regimen_url} - {res2.status_code}")

            except Exception as e:
                print(f"❗ Error processing {revision_url}: {e}")

# === Write comparison CSV ===
with open(comparison_csv, 'w', newline='') as compfile:
    writer = csv.DictWriter(compfile, fieldnames=comparison_fieldnames)
    writer.writeheader()
    for row in comparison_rows:
        writer.writerow({k: str(v) for k, v in row.items()})
