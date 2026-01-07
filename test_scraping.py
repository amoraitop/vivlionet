import requests
from bs4 import BeautifulSoup

BIBLIONET_URL = "https://biblionet.gr/"
SEARCH_URL = "https://biblionet.gr/συνθετη-αναζητηση?q="

def search_book(title):
    search_url = SEARCH_URL + title.replace(" ", "+")
    print(f"Searching: {search_url}")
    response = requests.get(search_url)
    print(f"Status Code: {response.status_code}")
    soup = BeautifulSoup(response.text, "html.parser")

    # Βρίσκουμε το πρώτο αποτέλεσμα
    first_result = soup.find("a", class_="book-title")  
    if first_result:
        return BIBLIONET_URL + first_result["href"]
    return None

def get_book_details(book_url):
    """ Παίρνει το όνομα του συγγραφέα και τα links των βιβλιοκριτικών. """
    response = requests.get(book_url)
    soup = BeautifulSoup(response.text, "html.parser")

    # Βρίσκουμε τον συγγραφέα
    author_tag = soup.find("a", class_="author-name")
    author = author_tag.text.strip() if author_tag else "Άγνωστος Συγγραφέας"

    # Βρίσκουμε τα links των βιβλιοκριτικών
    review_links = []
    # In the original main.py, it was looking for "book_reviews.asp" in href
    # Let's see if we can find any review links
    for link in soup.find_all("a", href=True):
        if "/κριτική/" in link["href"] or "book_reviews.asp" in link["href"]:
            review_links.append(BIBLIONET_URL + link["href"])

    return author, review_links

title = "η δεσμοφύλακας"
url = search_book(title)
print(f"Result URL: {url}")
if url:
    author, reviews = get_book_details(url)
    print(f"Author: {author}")
    print(f"Reviews: {reviews}")
