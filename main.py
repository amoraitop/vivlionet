import requests
import sys
import csv
import os
import re
import json
import base64
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# --- ΡΥΘΜΙΣΕΙΣ ---
BIBLIONET_URL = "https://biblionet.gr"
SEARCH_URL = "https://biblionet.gr/συνθετη-αναζητηση?q="

def search_book(title):
    """ Αναζητά το βιβλίο και επιστρέφει το URL του στη Βιβλιονέτ. """
    search_url = SEARCH_URL + title.replace(" ", "+")
    
    try:
        response = requests.get(search_url)
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
        if link.startswith("http"):
            return link
        else:
            return BIBLIONET_URL + link
            
    return None

def save_url_as_pdf(driver, url, pdf_path):
    """ Χρησιμοποιεί το Chrome DevTools Protocol για εκτύπωση σε PDF. """
    driver.get(url)
    # Αναμονή για φόρτωση της σελίδας
    time.sleep(2)
    
    # Ρυθμίσεις εκτύπωσης
    print_options = {
        'landscape': False,
        'displayHeaderFooter': False,
        'printBackground': True,
        'preferCSSPageSize': True,
    }
    
    # Εκτέλεση της εντολής εκτύπωσης μέσω CDP
    result = driver.execute_cdp_cmd("Page.printToPDF", print_options)
    
    with open(pdf_path, "wb") as f:
        f.write(base64.b64decode(result['data']))

def main():
    print("--- Biblionet URL Finder & Review Extractor ---")
    if len(sys.argv) > 1:
        book_title = " ".join(sys.argv[1:])
    else:
        book_title = input("Εισάγετε τον τίτλο του βιβλίου: ").strip()
    
    if not book_title:
        print("Δεν δόθηκε τίτλος.")
        return

    print(f"Αναζήτηση για: '{book_title}'...")
    book_url = search_book(book_title)
    
    if book_url:
        print(f"\nΒρέθηκε: {book_url}")
        reviews_url = book_url + "#bookPresentations"
        
        try:
            print("Λήψη και επεξεργασία παρουσιάσεων...")
            review_response = requests.get(reviews_url)
            review_response.raise_for_status()
            
            soup = BeautifulSoup(review_response.text, "html.parser")
            presentations_section = soup.find(id="bookPresentations")
            
            data_rows = []
            headers = ["Συντάκτης", "Τίτλος", "URL Κριτικής", "Μέσο", "Ημερομηνία"]
            
            if presentations_section:
                table = presentations_section.find("table")
                if table:
                    rows = table.find_all("tr")
                    for row in rows:
                        cols = row.find_all(["td", "th"])
                        if not cols: continue
                        cols_text = [ele.get_text(strip=True) for ele in cols]
                        if "Συντάκτης" in cols_text: continue

                        if len(cols) >= 5:
                            author = cols[1].get_text(strip=True)
                            title_cell = cols[2]
                            title_text = title_cell.get_text(strip=True)
                            a_tag = title_cell.find("a", href=True)
                            link = a_tag["href"] if a_tag else ""
                            if link and not link.startswith("http"):
                                link = BIBLIONET_URL + (link if link.startswith("/") else "/" + link)
                            medium = cols[3].get_text(strip=True)
                            date = cols[4].get_text(strip=True)
                            data_rows.append([author, title_text, link, medium, date])

            # Αποθήκευση σε CSV
            csv_filename = "reviews.csv"
            with open(csv_filename, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";") 
                writer.writerow(headers)
                writer.writerows(data_rows)
                
            if data_rows:
                print(f"Αποθηκεύτηκαν {len(data_rows)} εγγραφές στο '{csv_filename}'.")
                
                print("\nΛήψη κριτικών ως PDF μέσω Selenium...")
                pdf_dir = "reviews_pdfs"
                if not os.path.exists(pdf_dir):
                    os.makedirs(pdf_dir)

                # Ρύθμιση Selenium
                chrome_options = Options()
                chrome_options.add_argument("--headless")
                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)

                try:
                    for row in data_rows:
                        author = row[0]
                        url = row[2]
                        if not url: continue
                        
                        safe_name = re.sub(r'[\\/*?:"<>|]', "", author).strip() or "unknown"
                        pdf_path = os.path.join(pdf_dir, f"{safe_name}.pdf")
                        
                        counter = 1
                        while os.path.exists(pdf_path):
                            pdf_path = os.path.join(pdf_dir, f"{safe_name}_{counter}.pdf")
                            counter += 1
                            
                        print(f"Δημιουργία PDF για: {author} ({url})")
                        try:
                            if url.lower().endswith(".pdf"):
                                r = requests.get(url)
                                with open(pdf_path, "wb") as f:
                                    f.write(r.content)
                            else:
                                save_url_as_pdf(driver, url, pdf_path)
                        except Exception as e:
                            print(f"Σφάλμα στο {author}: {e}")
                finally:
                    driver.quit()
            else:
                print("Δεν βρέθηκαν παρουσιάσεις.")

        except Exception as e:
            print(f"Σφάλμα: {e}")
    else:
        print("\nΤο βιβλίο δεν βρέθηκε.")

if __name__ == "__main__":
    main()
