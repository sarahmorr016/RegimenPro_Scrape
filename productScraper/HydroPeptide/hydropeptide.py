import csv
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

input_csv = "/Users/sarahmorrison/Desktop/RegimenPro/productScraper/HydroPeptide/hydropeptide_product_urls.csv"
output_csv = "/Users/sarahmorrison/Desktop/Hydropeptide_Scraped_Products.csv"
comparison_csv = "/Users/sarahmorrison/Desktop/hydropeptide_comparison.csv"

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
    "HydroPeptide Value",
    "RegimenPro Value", 
    "Match?"
]

comparison_rows = []

def compare_fields(source_data, regimen_data, product_url):
    rows = []
    for key in source_data:
        if key in regimen_data:
            hydro_val = source_data[key].strip()
            regimen_val = regimen_data[key].strip()

            if key == "Product Price":
                try:
                    hydro_val_float = float(hydro_val.replace("$", "").strip())
                    regimen_val_float = float(regimen_val.replace("$", "").strip())
                    is_match = "✅ Yes" if hydro_val_float == regimen_val_float else "❌ No"
                except:
                    is_match = "⚠️ Invalid price format"
            else:
                is_match = "✅ Yes" if hydro_val.lower() == regimen_val.lower() else "❌ No"

            rows.append({
                "Product URL": product_url,
                "Field": key,
                "HydroPeptide Value": source_data[key],
                "RegimenPro Value": regimen_data[key],
                "Match?": is_match
            })
    return rows

with open(output_csv, 'w', newline='') as outfile:
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()

    with open(input_csv, mode="r", newline='') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            hydro_url = row["Product URL"].strip()
            regimen_url = row["RegimenPro Urls"].strip()
            print("Loaded HydroPeptide URL:", hydro_url)
            print("Loaded RegimenPro URL:", regimen_url)

            sku = "No SKU found"

            try:
                parsed = urlparse(hydro_url)
                clean_path = parsed.scheme + "://" + parsed.netloc + parsed.path
                json_url = clean_path + ".json"
                json_response = requests.get(json_url)
                if json_response.status_code == 200:
                    json_data = json_response.json()
                    sku = json_data["product"]["variants"][0].get("sku", "No SKU found")
            except Exception as e:
                print(f"Error getting SKU from JSON for {hydro_url}: {e}")

            try:   
                response = requests.get(hydro_url)
                if response.status_code != 200:
                    print(f"Failed to retrieve HydroPeptide HTML. Status code: {response.status_code}")
                    continue

                soup = BeautifulSoup(response.text, 'html.parser')

                product_name = soup.find("h1", class_="product__title")
                name = product_name.text.strip() if product_name else "No product name found"

                product_description = soup.find("p", class_="product__description")
                description = product_description.text.strip() if product_description else "No product description found"

                product_price = soup.find("meta", itemprop="price")
                price = product_price["content"] if product_price else "No product price found"

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
                    "Product URL": hydro_url,
                    "Product Name": name,
                    "Product Description": description,
                    "SKU": sku,
                    "Product Price": price,
                    "Ingredients": ingredients,
                    "Benefits": ", ".join(benefits),
                    "Skin Concerns": ", ".join(skin_concerns)
                })

                # RegimenPro JSON using correct URL
                try:
                    regimen_json_url = regimen_url + ".json"
                    regimen_response = requests.get(regimen_json_url)
                    if regimen_response.status_code == 200:
                        regimen_data = regimen_response.json()
                        regimen_product = regimen_data.get("product", {})
                        raw_html = regimen_product.get("body_html", "")
                        soup = BeautifulSoup(raw_html, 'html.parser')

                        # Try to extract just the product description
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

                        diff_rows = compare_fields(scraped_data, regimen_fields, hydro_url)
                        comparison_rows.extend(diff_rows)
                    else:
                        print(f"Failed to load RegimenPro JSON: {regimen_response.status_code}")
                except Exception as e:
                    print(f"Error comparing with RegimenPro URL {regimen_url}: {e}")

            except Exception as e:
                print(f"An error occurred while processing {hydro_url}: {e}")

# Write comparison CSV
with open(comparison_csv, 'w', newline='') as compfile:
    comp_writer = csv.DictWriter(compfile, fieldnames=comparison_fieldnames)
    comp_writer.writeheader()
    for row in comparison_rows:
        comp_writer.writerow(row)
