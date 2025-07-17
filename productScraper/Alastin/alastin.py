import csv
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

input_csv = "/Users/sarahmorrison/Desktop/RegimenPro/productScraper/Alastin/alastin_product_urls.csv"
output_csv = "/Users/sarahmorrison/Desktop/Alastin_Scraped_Products.csv"
comparison_csv = "/Users/sarahmorrison/Desktop/alastin_comparison.csv"

fieldnames = [
    "Product URL",
    "Product Name",
    "Product Description",
    "SKU",
    "Product Price",
    "Benefits"
]

comparison_fieldnames = [
    "Product URL",
    "Field",
    "Alastin Value",
    "RegimenPro Value", 
    "Match?"
]

comparison_rows = []

def normalize_text(s):
    return ' '.join(s.lower().replace(",", "").split())

def compare_fields(source_data, regimen_data, product_url):
    rows = []
    for key in source_data:
        if key in regimen_data:
            alastin_val = source_data[key].strip()
            regimen_val = regimen_data[key].strip()

            if key == "Product Price":
                try:
                    a_val = float(alastin_val.replace("$", "").strip())
                    r_val = float(regimen_val.replace("$", "").strip())
                    is_match = "✅ Yes" if a_val == r_val else "❌ No"
                except:
                    is_match = "⚠️ Invalid price format"
            else:
                is_match = "✅ Yes" if normalize_text(alastin_val) == normalize_text(regimen_val) else "❌ No"

            rows.append({
                "Product URL": product_url,
                "Field": key,
                "Alastin Value": alastin_val,
                "RegimenPro Value": regimen_val,
                "Match?": is_match
            })
    return rows

with open(output_csv, 'w', newline='') as outfile:
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()

    with open(input_csv, mode="r", newline='') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            alastin_url = row["Product URL"].strip()
            regimen_url = row["RegimenPro Urls"].strip()
            print("Loaded Alastin URL:", alastin_url)
            print("Loaded RegimenPro URL:", regimen_url)

            sku = name = description = price = "N/A"
            benefits_list = []

            try:
                parsed = urlparse(alastin_url.strip())
                json_url = parsed.scheme + "://" + parsed.netloc + parsed.path + ".json"
                json_response = requests.get(json_url)
                if json_response.status_code == 200:
                    json_data = json_response.json()
                    product = json_data["product"]
                    variant = product["variants"][0]

                    name = product.get("title", "No product name found")
                    raw_html = product.get("body_html", "")
                    description = BeautifulSoup(raw_html, "html.parser").get_text(strip=True) if raw_html else "No description found"
                    sku = variant.get("sku", "No SKU found")
                    price = variant.get("price", "No price found")
            except Exception as e:
                print(f"Error getting JSON for Alastin: {e}")

            try:
                response = requests.get(alastin_url)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    benefits_section = soup.find("ul", class_="list-column")
                    if benefits_section:
                        items = benefits_section.find_all("li")
                        for item in items:
                            benefits_list.append(item.text.strip())
            except Exception as e:
                print(f"Error fetching benefits from HTML: {e}")

            writer.writerow({
                "Product URL": alastin_url,
                "Product Name": name,
                "Product Description": description,
                "SKU": sku,
                "Product Price": price,
                "Benefits": ", ".join(benefits_list) if benefits_list else "No benefits found"
            })

            # REGIMENPRO: JSON comparison
            try:
                regimen_response = requests.get(regimen_url + ".json")
                if regimen_response.status_code == 200:
                    regimen_data = regimen_response.json()
                    regimen_product = regimen_data.get("product", {})
                    regimen_variant = regimen_product["variants"][0]

                    # Description
                    raw_html = regimen_product.get("body_html", "")
                    soup = BeautifulSoup(raw_html, 'html.parser')

                    # Try 1: first <p class="product__description">
                    description_tag = soup.find("p", class_="product__description")

                    # Try 2: fallback to first non-empty <p> tag
                    if not description_tag:
                        for p in soup.find_all("p"):
                            if p.get_text(strip=True):
                                description_tag = p
                                break

                    # Try 3: fallback to first non-empty <span> tag
                    if not description_tag:
                        for span in soup.find_all("span"):
                            if span.get_text(strip=True):
                                description_tag = span
                                break

                    clean_description = description_tag.get_text(strip=True)

                    # Benefits
                    regimen_benefits = []
                    benefit_dt = soup.find("dt", string=lambda t: t and "Benefits" in t)
                    if benefit_dt:
                        benefit_ul = benefit_dt.find_next("ul", class_="product__details-list")
                        if benefit_ul:
                            for li in benefit_ul.find_all("li", class_="product__details-item"):
                                span = li.find("span")
                                if span:
                                    regimen_benefits.append(span.text.strip())

                    regimen_fields = {
                        "Product Name": regimen_product.get("title", "No name"),
                        "Product Description": clean_description,
                        "SKU": regimen_variant.get("sku", "No SKU"),
                        "Product Price": regimen_variant.get("price", "No price"),
                    }

                    scraped_data = {
                        "Product Name": name,
                        "Product Description": description,
                        "SKU": sku,
                        "Product Price": price,
                    }

                    diff_rows = compare_fields(scraped_data, regimen_fields, alastin_url)
                    comparison_rows.extend(diff_rows)
                else:
                    print(f"Failed to retrieve RegimenPro JSON: {regimen_response.status_code}")
            except Exception as e:
                print(f"Error comparing with RegimenPro: {e}")

# Write final comparison report
with open(comparison_csv, 'w', newline='') as compfile:
    writer = csv.DictWriter(compfile, fieldnames=comparison_fieldnames)
    writer.writeheader()
    for row in comparison_rows:
        writer.writerow(row)
