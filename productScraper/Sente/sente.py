import csv
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from datetime import datetime
from difflib import SequenceMatcher
import unicodedata
import html

# === File paths ===
input_csv      = "/Users/sarahmorrison/Desktop/RegimenPro/productScraper/Sente/sente_product_urls.csv"
output_csv     = "/Users/sarahmorrison/Desktop/Sente_Scraped_Products.csv"
comparison_csv = "/Users/sarahmorrison/Desktop/sente_comparison.csv"

# === Columns for outputs ===
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
    "Sente Value",
    "RegimenPro Value",
    "Match?",
    "Date/Time Captured"
]

comparison_rows = []

# === Utility: normalize strings (preserve leading zeros) ===
def normalize_string(s):
    return ' '.join(unicodedata.normalize("NFKD", str(s)).strip().split())

# === Extract first paragraph, HTML-decode, strip product name if prefixed ===
def extract_description(body_html, product_name=""):
    try:
        text_html = html.unescape(body_html or "")
        soup = BeautifulSoup(text_html, "html.parser")
        ps   = soup.find_all("p")
        text = ps[0].get_text(strip=True) if ps else soup.get_text(strip=True)
        if product_name and text.lower().startswith(product_name.lower()):
            return text[len(product_name):].lstrip(" :–-").strip()
        return text
    except Exception as e:
        print(f"[!] Description parse error: {e}")
        return "No description"

# === Compare two dicts of fields, allow fuzzy match on description ===
def compare_fields(sente_data, regimen_data, product_url, timestamp):
    rows = []
    for key in sente_data:
        if key not in regimen_data:
            continue
        v1 = normalize_string(sente_data[key])
        v2 = normalize_string(regimen_data[key])

        if key == "Product Price":
            try:
                f1 = float(v1.replace("$","").replace(",",""))
                f2 = float(v2.replace("$","").replace(",",""))
                match = "✅ Yes" if f1 == f2 else "❌ No"
            except:
                match = "⚠️ Invalid format"
        elif key == "Product Description":
            ratio = SequenceMatcher(None, v1.lower(), v2.lower()).ratio()
            match = "✅ Yes" if ratio > 0.85 else f"❌ No ({round(ratio*100)}% match)"
        else:
            match = "✅ Yes" if v1 == v2 else "❌ No"

        rows.append({
            "Product URL": product_url,
            "Field":       key,
            "Sente Value": v1,
            "RegimenPro Value": v2,
            "Match?":      match,
            "Date/Time Captured": timestamp
        })
    return rows

# === Main Loop ===
with open(output_csv, 'w', newline='') as outf:
    writer = csv.DictWriter(outf, fieldnames=fieldnames)
    writer.writeheader()

    with open(input_csv, newline='') as inf:
        reader = csv.DictReader(inf)
        for row in reader:
            sente_url  = row["Product Urls"].strip()
            reg_url    = row["RegimenPro Urls"].strip()
            print("→ Sente:", sente_url)
            print("→ RegimenPro:", reg_url)

            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # defaults
            name = desc = sku = price = "N/A"

            # --- Scrape Sente JSON ---
            try:
                p = urlparse(sente_url)
                clean = f"{p.scheme}://{p.netloc}{p.path}"
                json_url = clean + ".json"
                r = requests.get(json_url)
                if r.status_code == 200:
                    prod = r.json()["product"]
                    name  = prod.get("title","N/A").strip()
                    desc  = extract_description(prod.get("body_html",""), name)
                    sku   = str(prod.get("variants",[{}])[0].get("sku","No SKU"))
                    price = str(prod.get("variants",[{}])[0].get("price","N/A"))
                else:
                    print(f"[!] Sente JSON {r.status_code} for {sente_url}")
            except Exception as e:
                print(f"[!] Error scraping Sente: {e}")

            # write scraped Sente row
            writer.writerow({
                "Product URL":          sente_url,
                "Product Name":         name,
                "Product Description":  desc,
                "SKU":                  sku,
                "Product Price":        price,
                "Date/Time Captured":   ts
            })

            # --- Scrape RegimenPro JSON ---
            try:
                rr = requests.get(reg_url + ".json")
                if rr.status_code == 200:
                    rp = rr.json().get("product",{})
                    rp_name = rp.get("title","N/A").strip()
                    rp_desc = extract_description(rp.get("body_html",""), rp_name)
                    rp_sku  = str(rp.get("variants",[{}])[0].get("sku","No SKU"))
                    rp_price= str(rp.get("variants",[{}])[0].get("price","N/A"))

                    sente_data = {
                        "Product Name":        name,
                        "Product Description": desc,
                        "SKU":                  sku,
                        "Product Price":        price
                    }
                    regimen_data = {
                        "Product Name":        rp_name,
                        "Product Description": rp_desc,
                        "SKU":                  rp_sku,
                        "Product Price":        rp_price
                    }
                    comparison_rows += compare_fields(sente_data, regimen_data, sente_url, ts)
                else:
                    print(f"[!] RegimenPro JSON {rr.status_code} for {reg_url}")
            except Exception as e:
                print(f"[!] Error scraping RegimenPro: {e}")

# === Write comparison CSV ===
with open(comparison_csv, 'w', newline='') as cf:
    writer = csv.DictWriter(cf, fieldnames=comparison_fieldnames)
    writer.writeheader()
    for r in comparison_rows:
        writer.writerow({k:str(v) for k,v in r.items()})
