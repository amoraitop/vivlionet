import requests
import sys
import csv
import os
import re
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# --- ΡΥΘΜΙΣΕΙΣ ---
BIBLIONET_URL = "https://biblionet.gr"
SEARCH_URL = "https://biblionet.gr/συνθετη-αναζητηση?q="

def search_book(title):
    """ Αναζητά το βιβλίο και επιστρέφει το URL του στη Βιβλιονέτ. """
    search_url = SEARCH_URL + title.replace(" ", "+")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Σφάλμα σύνδεσης: {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    first_result = soup.find("a", class_="book-title")
    
    if not first_result:
        results_container = soup.find("div", class_="products")
        if results_container:
            first_result = results_container.find("a", href=True)

    if first_result and first_result.get("href"):
        link = first_result["href"]
        return link if link.startswith("http") else BIBLIONET_URL + link
    return None

def save_page_as_txt(driver, txt_path):
    """ Καθαρίζει τη σελίδα και αποθηκεύει το κύριο κείμενο. """
    try:
        html_content = driver.page_source
        soup = BeautifulSoup(html_content, "html.parser")

        # Αφαίρεση άχρηστων στοιχείων
        for element in soup(["script", "style", "nav", "footer", "header", "aside", "form", "iframe"]):
            element.decompose()

        # Στόχευση στο κυρίως περιεχόμενο
        main_content = soup.find("article") or \
                       soup.find("div", class_=re.compile(r'content|article|post|entry|main|body', re.I)) or \
                       soup.find("main")

        if main_content:
            paragraphs = main_content.find_all("p")
            text = "\n\n".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text()) > 25])
        else:
            paragraphs = soup.find_all("p")
            text = "\n\n".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text()) > 25])

        if len(text) < 300:
            text = soup.get_text(separator="\n", strip=True)

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)
        return True
    except Exception as e:
        print(f"  Σφάλμα επεξεργασίας: {e}")
        return False

def main():
    # ΕΝΤΟΠΙΣΜΟΣ ΦΑΚΕΛΟΥ ΤΟΥ SCRIPT
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("--- Biblionet URL Finder & Clean Text Extractor ---")
    book_title = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("Εισάγετε τίτλο βιβλίου: ").strip()
    
    if not book_title: return

    print(f"Αναζήτηση: '{book_title}'...")
    book_url = search_book(book_title)
    
    if not book_url:
        print("Το βιβλίο δεν βρέθηκε.")
        return

    print(f"Βρέθηκε: {book_url}")
    reviews_url = book_url + "#bookPresentations"
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        review_response = requests.get(reviews_url, headers=headers)
        soup = BeautifulSoup(review_response.text, "html.parser")
        
        data_rows = []
        pres_section = soup.find(id="bookPresentations")
        if pres_section and pres_section.find("table"):
            for row in pres_section.find("table").find_all("tr")[1:]:
                cols = row.find_all("td")
                if len(cols) >= 5:
                    author = cols[1].get_text(strip=True)
                    link_tag = cols[2].find("a", href=True)
                    link = link_tag["href"] if link_tag else ""
                    if link and not link.startswith("http"):
                        link = BIBLIONET_URL + ("" if link.startswith("/") else "/") + link
                    data_rows.append([author, link])

        if not data_rows:
            print("Δεν βρέθηκαν κριτικές.")
            return

        # ΟΡΙΣΜΟΣ PATHS ΣΤΟΝ ΦΑΚΕΛΟ ΤΟΥ PROJECT
        csv_path = os.path.join(base_dir, "reviews.csv")
        txt_dir = os.path.join(base_dir, "reviews_txt")
        
        if not os.path.exists(txt_dir): os.makedirs(txt_dir)

        # Αποθήκευση CSV (για έλεγχο)
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["Συντάκτης", "URL"])
            writer.writerows(data_rows)

        # Selenium Setup
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        driver = webdriver.Chrome(options=chrome_options)

        try:
            for author, url in data_rows:
                if not url or url.lower().endswith(".pdf"): continue
                
                safe_name = re.sub(r'[\\/*?:"<>|]', "", author).strip() or "review"
                txt_path = os.path.join(txt_dir, f"{safe_name}.txt")
                
                idx = 1
                original_path = txt_path
                while os.path.exists(txt_path):
                    txt_path = f"{original_path[:-4]}_{idx}.txt"
                    idx += 1

                print(f"Λήψη κριτικής: {author}")
                try:
                    driver.get(url)
                    time.sleep(4)
                    save_page_as_txt(driver, txt_path)
                except Exception as e:
                    print(f"  Αποτυχία στο {url}: {e}")
                
        finally:
            driver.quit()
            print(f"\nΗ διαδικασία ολοκληρώθηκε!")
            print(f"Αρχεία αποθηκεύτηκαν στο: {base_dir}")

    except Exception as e:
        print(f"Σφάλμα: {e}")

if __name__ == "__main__":
    main()