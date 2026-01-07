import requests
import ssl
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager

class TLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.maximum_version = ssl.TLSVersion.TLSv1_2
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)

session = requests.Session()
session.mount("https://", TLSAdapter())

url = "https://biblionet.diadrasis.net/wp-json/biblionetwebservice/get_title"
payload = {
    "username": "amoraitop@gmail.com",
    "password": "M!ty3bbc2u3vXt8",
    "title": "160747"
}

response = session.post(url, json=payload)
print(response.text)
