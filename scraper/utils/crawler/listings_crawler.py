import re
import requests
import bs4
from bs4 import BeautifulSoup
from datetime import datetime


'''
LISTING PAGE 
'''


def scrape_listing_page(url: str, 
                        headers: dict, 
                        proxies: dict) -> list:
    
    session = requests.Session()
    session.headers.update(headers)

    response = session.get(url, proxies=proxies, verify=False, timeout=20)
    soup = BeautifulSoup(response.content, "html.parser")
    cards = soup.find_all("div", class_="listingCard")
    return cards


def scrape_listing_card(card: bs4.element.Tag, 
                        existing_links:list, 
                        typology_pattern: re.Pattern) -> dict:
    link_tag = card.find('a', class_='lc-cardCover')
    link = "https://www.fincaraiz.com.co" + link_tag['href'] if link_tag else None
    if not link or link in existing_links:
        return None  

    price_tag = card.find('div', class_='lc-price')
    price = price_tag.get_text(strip=True) if price_tag else None

    location_tag = card.find('strong', class_='lc-location')
    location = location_tag.get_text(strip=True) if location_tag else None

    typology_tag = card.find('div', class_='lc-typologyTag')
    typology = typology_tag.get_text(strip=True) if typology_tag else None
    typology_pattern = re.compile(typology_pattern)

    bedrooms = bathrooms = area = None
    if typology:
        match = typology_pattern.search(typology)
        if match:
            bedrooms, bathrooms, area = match.groups()

    agency_tag = card.find('strong', class_='body body-2 high')
    agency = agency_tag.get_text(strip=True) if agency_tag else None

    now = datetime.now()
    now = now.strftime("%Y-%m-%d %H:%M:%S")

    card_info = {
            "Link": link,
            "Price": price,
            "Bedrooms": bedrooms,
            "Bathrooms": bathrooms,
            "Area": area,
            "Agency": agency,
            "Location": location,
            "Datetime_Added": now
        }

    return card_info
