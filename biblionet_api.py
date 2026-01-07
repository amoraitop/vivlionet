import requests
import json
import getpass
import sys
import os
from dotenv import load_dotenv

# Load variables from .env file if it exists
load_dotenv()

# --- CONFIGURATION ---
# You can put your credentials here or in a .env file
BIBLIONET_USERNAME = "amoraitop@gmail.com"
BIBLIONET_PASSWORD = "M!ty3bbc2u3vXt8"
# ---------------------

class BiblionetClient:
    BASE_URL = "https://biblionet.gr/webservice"

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def _make_request(self, endpoint, params=None):
        """
        Helper method to make GET requests to the API.
        Automatically includes authentication credentials.
        """
        if params is None:
            params = {}
        
        # Add credentials to parameters
        params['username'] = self.username
        params['password'] = self.password

        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()  
            
            # The API returns JSON
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"Network error: {str(e)}"}
        except json.JSONDecodeError:
            return {"error": "Failed to decode JSON response. Check credentials or API status."}

    def get_title_by_isbn(self, isbn):
        params = {'isbn': isbn}
        return self._make_request('get_title', params)

    def get_title_by_id(self, title_id):
        params = {'title': title_id}
        return self._make_request('get_title', params)

def main():
    print("--- Biblionet Python API Client ---")
    
    # Use hardcoded, env, or prompt
    username = BIBLIONET_USERNAME
    if not username:
        username = input("Enter Biblionet Username: ").strip()
        
    password = BIBLIONET_PASSWORD
    if not password:
        password = getpass.getpass("Enter Biblionet Password: ").strip()

    if not username or not password:
        print("Error: Username and Password are required.")
        sys.exit(1)

    client = BiblionetClient(username, password)

    while True:
        print("\nOptions:")
        print("1. Search by ISBN")
        print("2. Search by Biblionet ID")
        print("q. Quit")
        
        choice = input("Select an option: ").strip().lower()

        if choice == '1':
            isbn = input("Enter ISBN: ").strip()
            if isbn:
                print(f"Searching for ISBN: {isbn}...")
                result = client.get_title_by_isbn(isbn)
                print(json.dumps(result, indent=4, ensure_ascii=False))
        
        elif choice == '2':
            tid = input("Enter Biblionet ID: ").strip()
            if tid:
                print(f"Searching for ID: {tid}...")
                result = client.get_title_by_id(tid)
                print(json.dumps(result, indent=4, ensure_ascii=False))

        elif choice == 'q':
            print("Exiting.")
            break
        
        else:
            print("Invalid option.")

if __name__ == "__main__":
    main()
