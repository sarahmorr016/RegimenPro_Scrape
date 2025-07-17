import csv
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# File paths
input_csv = "/Users/sarahmorrison/Desktop/RegimenPro/productScraper/Biopelle_Inc./biopelle_product_urls.csv"
output_csv = "/Users/sarahmorrison/Desktop/Biopelle_Scraped_Products.csv"
comparison_csv = "/Users/sarahmorrison/Desktop/biopelle_comparison.csv"

# Field definitions
fieldnames = [
    "Product URL",
    "Product Name",
    "Product Description",
    "SKU",
    "Product Price",
    "Ingredients",
    "Benefits",
    "Skin Concerns"
]

comparison_fieldnames = [
    "Product URL",
    "Field",
    "Biopelle Value",
    "RegimenPro Value", 
    "Match?"
]

comparison_rows = []

def compare_fields(source_data, regimen_data, product_url):
    rows = []
    for key in source_data:
        if key in regimen_data:
            biopelle_val = source_data[key].strip()
            regimen_val = regimen_data[key].strip()

            if key == "Product Price":
                try:
                    biopelle_float = float(biopelle_val.replace("$", "").strip())
                    regimen_float = float(regimen_val.replace("$", "").strip())
                    is_match = "✅ Yes" if biopelle_float == regimen_float else "❌ No"
                except:
                    is_match = "⚠️ Invalid price format"
            else:
                is_match = "✅ Yes" if biopelle_val.lower() == regimen_val.lower() else "❌ No"

            rows.append({
                "Product URL": product_url,
                "Field": key,
                "Biopelle Value": biopelle_val,
                "RegimenPro Value": regimen_val,
                "Match?": is_match
            })
    return rows

# Write scraped output
with open(output_csv, 'w', newline='') as outfile:
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()

    with open(input_csv, mode="r", newline='') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            biopelle_url = row["Product Urls"].strip()
            regimen_url = row["RegimenPro Urls"].strip()
            print("Loaded Biopelle URL:", biopelle_url)
            print("Loaded RegimenPro URL:", regimen_url)

            sku = "No SKU found"

            try:
                parsed = urlparse(biopelle_url)
                clean_path = parsed.scheme + "://" + parsed.netloc + parsed.path
                json_url = clean_path + ".json"
                json_response = requests.get(json_url)
                if json_response.status_code == 200:
                    json_data = json_response.json()
                    sku = json_data["product"]["variants"][0].get("sku", "No SKU found")
            except Exception as e:
                print(f"Error getting SKU from JSON for {biopelle_url}: {e}")

            try:
                response = requests.get(biopelle_url)
                if response.status_code != 200:
                    print(f"Failed to retrieve Biopelle HTML. Status code: {response.status_code}")
                    continue

                soup = BeautifulSoup(response.text, 'html.parser')

                product_name = soup.find("h1", class_="product__title")
                name = product_name.text.strip() if product_name else "No product name found"

                product_description = soup.find("p", class_="product__description")
                description = product_description.text.strip() if product_description else "No product description found"

                price_tag = soup.find("p", class_="price")
                price = "No product price found"
                if price_tag:
                    dollar_span = price_tag.find("span", attrs={"aria-label": True})
                    if dollar_span:
                        price = dollar_span["aria-label"].strip()

                product_ingredients = soup.find("aside", id="product-ingredients")
                ingredients = product_ingredients.text.strip() if product_ingredients else "No ingredients found"

                benefits = []
                benefits_list = soup.find("ul", class_="product__details-list")
                if benefits_list:
                    items = benefits_list.find_all("li", class_="product__details-item")
                    for item in items:
                        span = item.find("span")
                        if span:
                            benefits.append(span.text.strip())

                skin_concerns = []
                details_sections = soup.find_all("div", class_="product__details-column")
                for section in details_sections:
                    title = section.find("p", class_="product__details-title")
                    if title and title.get_text(strip=True).upper() == "SKIN CONCERN":
                        ul = section.find("ul", class_="product__details-list")
                        if ul:
                            items = ul.find_all("li", class_="product__details-item")
                            for item in items:
                                span = item.find("span")
                                if span:
                                    skin_concerns.append(span.text.strip())

                writer.writerow({
                    "Product URL": biopelle_url,
                    "Product Name": name,
                    "Product Description": description,
                    "SKU": sku,
                    "Product Price": price,
                    "Ingredients": ingredients,
                    "Benefits": ", ".join(benefits),
                    "Skin Concerns": ", ".join(skin_concerns)
                })

                # --- Scrape RegimenPro JSON ---
                try:
                    regimen_json_url = regimen_url + ".json"
                    regimen_response = requests.get(regimen_json_url)
                    if regimen_response.status_code == 200:
                        regimen_data = regimen_response.json()
                        regimen_product = regimen_data.get("product", {})
                        raw_html = regimen_product.get("body_html", "")
                        soup = BeautifulSoup(raw_html, 'html.parser')

                        description_tag = soup.find("p", class_="product__description")
                        clean_description = description_tag.get_text(strip=True) if description_tag else "No description found"

                        regimen_fields = {
                            "Product Name": regimen_product.get("title", "No name"),
                            "Product Description": clean_description,
                            "SKU": regimen_product["variants"][0].get("sku", "No SKU"),
                            "Product Price": regimen_product["variants"][0].get("price", "No price")
                        }

                        scraped_data = {
                            "Product Name": name,
                            "Product Description": description,
                            "SKU": sku,
                            "Product Price": price
                        }

                        diff_rows = compare_fields(scraped_data, regimen_fields, biopelle_url)
                        comparison_rows.extend(diff_rows)
                    else:
                        print(f"Failed to load RegimenPro JSON: {regimen_response.status_code}")
                except Exception as e:
                    print(f"Error comparing with RegimenPro URL {regimen_url}: {e}")

            except Exception as e:
                print(f"An error occurred while processing {biopelle_url}: {e}")

# Write comparison CSV
with open(comparison_csv, 'w', newline='') as compfile:
    comp_writer = csv.DictWriter(compfile, fieldnames=comparison_fieldnames)
    comp_writer.writeheader()
    for row in comparison_rows:
        comp_writer.writerow(row)
