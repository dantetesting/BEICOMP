from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime, timedelta

# ==============================================================================
# FUNGSI PARSING TANGGAL - SEKARANG MENDUKUNG 3 FORMAT
# ==============================================================================
def parse_promo_date(date_text, competitor):
    try:
        if competitor == "Hartono":
            cleaned_text = date_text.replace("Periode Promo:", "").strip()
            if ' - ' in cleaned_text:
                start_str, end_str = cleaned_text.split(' - ')
                # Handle cases where start date only specifies the day
                if len(start_str.split()) == 1 and ',' not in start_str:
                    end_date_obj = datetime.strptime(end_str.replace(",", ""), "%b %d %Y")
                    start_date_obj = end_date_obj.replace(day=int(start_str.replace(",", "")))
                else:
                    end_date_obj = datetime.strptime(end_str.replace(",", ""), "%b %d %Y")
                    start_date_obj = datetime.strptime(start_str.replace(",", ""), "%b %d %Y")
                return start_date_obj.strftime("%Y-%m-%d"), end_date_obj.strftime("%Y-%m-%d")
            elif 'Hingga' in cleaned_text:
                today = datetime.now()
                start_date_str = today.strftime("%Y-%m-%d")
                month_map = {'januari': 'Jan', 'februari': 'Feb', 'maret': 'Mar', 'april': 'Apr', 'mei': 'May', 'juni': 'Jun', 'juli': 'Jul', 'agustus': 'Aug', 'september': 'Sep', 'oktober': 'Oct', 'november': 'Nov', 'desember': 'Dec'}
                end_str = cleaned_text.replace("Hingga ", "").replace("Berlaku Setiap Hari", "").strip()
                month_id, year_str = end_str.split()
                month_en = month_map.get(month_id.lower())
                end_date = datetime.strptime(f"{month_en} {year_str}", "%b %Y")
                next_month = end_date.replace(day=28) + timedelta(days=4)
                last_day_of_month = next_month - timedelta(days=next_month.day)
                return start_date_str, last_day_of_month.strftime("%Y-%m-%d")

        elif competitor == "Electronic City":
            # Format: "Masa berlaku 17 - 18 August 2025"
            cleaned_text = date_text.replace("Masa berlaku ", "").strip()
            parts = cleaned_text.split(' ')
            start_day = parts[0]
            end_day = parts[2]
            month_id = parts[3]
            year_str = parts[4]
            month_map_id_to_en = {
                'januari': 'January', 'februari': 'February', 'maret': 'March', 'april': 'April', 
                'mei': 'May', 'juni': 'June', 'juli': 'July', 'agustus': 'August', 
                'september': 'September', 'oktober': 'October', 'november': 'November', 'desember': 'December'
            }
            month_en = month_map_id_to_en.get(month_id.lower(), month_id)

            start_date_obj = datetime.strptime(f"{start_day} {month_en} {year_str}", "%d %B %Y")
            end_date_obj = datetime.strptime(f"{end_day} {month_en} {year_str}", "%d %B %Y")
            return start_date_obj.strftime("%Y-%m-%d"), end_date_obj.strftime("%Y-%m-%d")
            
        return "", ""
    except Exception:
        return "", ""

# ==============================================================================
# HELPER: EXTRACT PRODUCT DATA (Placeholder Logic)
# ==============================================================================
def extract_product_details(card, competitor):
    details = {
        "product_name": "",
        "model_number": "",
        "normal_price": "",
        "promo_price": ""
    }
    
    # NOTE: This section adds the requested fields. Actual price scraping requires more specific HTML selectors.
    if competitor == "Hartono":
        title_text = card.find('strong').get_text(strip=True) if card.find('strong') else ""
        details["product_name"] = title_text.split('—')[0].strip()
        
    elif competitor == "Electronic City":
        price_tags = card.find_all('p', class_='price')
        if len(price_tags) >= 2:
            details["normal_price"] = price_tags[0].get_text(strip=True)
            details["promo_price"] = price_tags[1].get_text(strip=True)
        else:
             sale_price = card.find('span', class_='sale-price')
             if sale_price:
                 details["promo_price"] = sale_price.get_text(strip=True)

    elif competitor == "Erablue":
        details["product_name"] = card.find('h3').get_text(strip=True) if card.find('h3') else ""
    
    return details

# ==============================================================================
# BROWSER INITIALIZATION HELPER (FIXED FOR GITHUB ACTIONS)
# ==============================================================================
def initialize_browser():
    # CRITICAL FIX: Explicitly set browser executable path for GitHub Actions runner
    options = uc.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    # This path is where browser-actions/setup-chrome places the executable on Ubuntu runners
    options.binary_location = '/usr/bin/google-chrome' 
    
    # FIX: Add a default argument expected in headless environments 
    options.add_argument("--remote-debugging-port=9222")

    # The undetected_chromedriver will now use the stable version installed by the GitHub Action
    driver = uc.Chrome(options=options)
    return driver

# ==============================================================================
# SCRAPER HARTONO
# ==============================================================================
def scrape_hartono():
    print("\n--- Memulai Scrape Hartono ---")
    driver = initialize_browser()
    url = "https://myhartono.com/en/promo-pilihan"
    print(f"Mengunjungi URL: {url}...")
    promotions = []
    try:
        driver.get(url)
        time.sleep(10)
        html_content = driver.page_source
    except Exception as e:
        print(f"Error saat navigasi browser Hartono: {e}")
        driver.quit()
        return []
    driver.quit()
    soup = BeautifulSoup(html_content, 'html.parser')
    promo_cards = soup.find_all('div', class_='ty-column3')
    if not promo_cards: return []
    print(f"SUKSES! Menemukan {len(promo_cards)} promosi Hartono.")
    
    for card in promo_cards:
        try:
            title_element = card.find('strong')
            if not title_element: continue
            date_element = card.find('p')
            link_element = card.find_all('a')[-1]
            
            title = title_element.get_text(strip=True)
            date_range_text = date_element.get_text(strip=True) if date_element else ""
            promo_url = link_element['href']
            start_date, end_date = parse_promo_date(date_range_text, "Hartono")
            
            product_details = extract_product_details(card, "Hartono")
            
            promo_data = {
                "competitor": "Hartono", 
                "title": title, 
                "startDate": start_date, 
                "endDate": end_date, 
                "details": date_range_text, 
                "url": promo_url,
                "product_name": product_details["product_name"],
                "model_number": product_details["model_number"],
                "normal_price": product_details["normal_price"],
                "promo_price": product_details["promo_price"]
            }
            promotions.append(promo_data)
        except Exception: continue
    return promotions

# ==============================================================================
# SCRAPER ELECTRONIC CITY
# ==============================================================================
def scrape_electronic_city():
    print("\n--- Memulai Scrape Electronic City ---")
    driver = initialize_browser()
    url = "https://www.eci.id/promo"
    print(f"Mengunjungi URL: {url}...")
    promotions = []
    try:
        driver.get(url)
        wait = WebDriverWait(driver, 30)
        wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "card-promo")))
        time.sleep(3)
        html_content = driver.page_source
        soup = BeautifulSoup(html_content, 'html.parser')
        promo_cards = soup.find_all('div', class_='card-promo')
        print(f"SUKSES! Menemukan {len(promo_cards)} promosi Electronic City.")
        for card in promo_cards:
            try:
                title = card.find('div', class_='ft-sz-13').get_text(strip=True)
                details = card.find('div', class_='ft-sz-12').get_text(strip=True)
                promo_url = "https://eci.id" + card.find('a')['href']
                start_date, end_date = parse_promo_date(details, "Electronic City")
                
                product_details = extract_product_details(card, "Electronic City") 

                promo_data = {
                    "competitor": "Electronic City", 
                    "title": title, 
                    "startDate": start_date, 
                    "endDate": end_date, 
                    "details": details, 
                    "url": promo_url,
                    "product_name": title,
                    "model_number": "", 
                    "normal_price": product_details["normal_price"], 
                    "promo_price": product_details["promo_price"]
                }
                promotions.append(promo_data)
            except Exception: continue
    except Exception as e:
        print(f"Error saat navigasi atau mem-parsing Electronic City: {e}")
    finally:
        driver.quit()
    return promotions

# ==============================================================================
# SCRAPER ERABLUE
# ==============================================================================
def scrape_erablue():
    print("\n--- Memulai Scrape Erablue ---")
    driver = initialize_browser()
    url = "https://www.erablue.id/promosi"
    print(f"Mengunjungi URL: {url}...")
    promotions = []
    try:
        driver.get(url)
        wait = WebDriverWait(driver, 30)
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "li.itemhv")))
        time.sleep(3)
        html_content = driver.page_source
        soup = BeautifulSoup(html_content, 'html.parser')
        promo_cards = soup.find_all('li', class_='itemhv')
        print(f"SUKSES! Menemukan {len(promo_cards)} promosi Erablue.")
        for card in promo_cards:
            try:
                title = card.find('h3').get_text(strip=True)
                details = card.find('p').get_text(strip=True)
                promo_url = card.find('a')['href']
                
                product_details = extract_product_details(card, "Erablue") 
                
                promo_data = {
                    "competitor": "Erablue", 
                    "title": title, 
                    "startDate": "", 
                    "endDate": "", 
                    "details": details, 
                    "url": promo_url,
                    "product_name": product_details["product_name"],
                    "model_number": "", 
                    "normal_price": "", 
                    "promo_price": ""
                }
                promotions.append(promo_data)
            except Exception: continue
    except Exception as e:
        # Changed this to a print statement to ensure the Python script does not crash and the action continues
        print(f"Error saat navigasi atau mem-parsing Erablue: {e}")
    finally:
        driver.quit()
    return promotions

# ==============================================================================
# EKSEKUSI UTAMA
# ==============================================================================
if __name__ == "__main__":
    all_promotions = []
    
    # The individual scrapers now handle their own browser initialization and cleanup
    all_promotions.extend(scrape_hartono())
    all_promotions.extend(scrape_electronic_city())
    all_promotions.extend(scrape_erablue())

    output_file = 'promotions.json'
    with open(output_file, 'w') as f:
        json.dump(all_promotions, f, indent=4)
        
    print(f"\nScraping Selesai. Data disimpan ke {output_file}")
    print(f"Total promosi yang berhasil di-parse: {len(all_promotions)}")
