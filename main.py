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

def save_page_as_txt(driver, txt_path):
    """ Λαμβάνει το κείμενο της σελίδας και το αποθηκεύει σε TXT. """
    try:
        # Λήψη του κειμένου από το body της σελίδας
        body_text = driver.find_element("tag name", "body").text
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(body_text)
        return True
    except Exception as e:
        print(f"  Σφάλμα κατά την εξαγωγή κειμένου: {e}")
        return False

def main():
    print("--- Biblionet URL Finder & Text Extractor (Automatic) ---")
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
                
                print("\nΑυτόματη λήψη περιεχομένου ως TXT μέσω Selenium...")
                txt_dir = "reviews_txt"
                if not os.path.exists(txt_dir):
                    os.makedirs(txt_dir)

                # Ρύθμιση Selenium (Headless για αυτόματη λειτουργία)
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
                        txt_path = os.path.join(txt_dir, f"{safe_name}.txt")
                        
                        counter = 1
                        while os.path.exists(txt_path):
                            txt_path = os.path.join(txt_dir, f"{safe_name}_{counter}.txt")
                            counter += 1
                            
                        print(f"Επεξεργασία: {author} ({url})")
                        try:
                            if url.lower().endswith(".pdf"):
                                print(f"  Παράλειψη (αρχείο PDF): {url}")
                            else:
                                driver.get(url)
                                time.sleep(2) # Αναμονή για φόρτωση
                                if save_page_as_txt(driver, txt_path):
                                    print(f"  Αποθηκεύτηκε: {txt_path}")
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