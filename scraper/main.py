import asyncio

from utils.connection.loader import *
from utils.connection.proxy import *
from utils.crawler.details_crawler import *
from utils.crawler.listings_crawler import *
from utils.services.nearby import *
from utils.services.vision import *

def main():
    config = load_config("config.json")
    env_dict = load_env_variables(".env")
    headers, proxy_server_dict, proxy_http_dict = get_proxies(env_dict, config)

    csv_path = config['GENERAL']['CSV_PATH']

    # Load existing links if CSV exists
    if os.path.exists(csv_path):
        df_existing = pd.read_csv(csv_path)
        existing_links = set(df_existing['Link'].dropna().tolist())
    else:
        existing_links = set()

    for page_num in range(1,65):
        url = f"https://www.fincaraiz.com.co/arriendo/apartamentos/bogota/bogota-dc/publicado-ultimos-7-dias/pagina{page_num}?&ordenListado=3"
        cards = scrape_listing_page(url=url, headers=headers, proxies=proxy_http_dict)
        print(len(cards), "cards found on page:", page_num)
        typology_pattern = config['CRAWLERS']['LISTINGS']['TYPOLOGY_PATTERN']

        for card in cards:
            card_info = scrape_listing_card(card=card,
                                            existing_links=existing_links,
                                            typology_pattern=typology_pattern)
            if card_info and card_info["Link"] not in existing_links:
                details = asyncio.run(scrape_details_page(headless=config['CRAWLERS']['DETAIL']['HEADLESS'],
                                                        proxy=proxy_server_dict,
                                                        headers=headers,
                                                        url=card_info["Link"],
                                                        img_folder=config['GENERAL']['IMAGE_DIR'],
                                                        timeout=config['CRAWLERS']['DETAIL']['TIMEOUT']['REQUEST_TIMEOUT'],
                                                        element_timeout=config['CRAWLERS']['DETAIL']['TIMEOUT']['ELEMENT_TIMEOUT']))
                if details:
                    description = describe_apartment_images(api_key=env_dict['OPENAI_API_KEY'],
                                                        prompt_text=config['OPENAI']['PROMPT'],
                                                        model=config['OPENAI']['MODEL'],
                                                        image_detail=config['OPENAI']['IMAGE_DETAIL'],
                                                        max_tokens=config['OPENAI']['MAX_TOKENS'],
                                                        image_dir=config['GENERAL']['IMAGE_DIR'])

                    places = get_nearby_places(api_key=env_dict['MAPS_API_KEY'],
                                            latitude=details['coordinates'][0],
                                            longitude=details['coordinates'][1],
                                            radius=config['MAPS_NEARBY']['RADIUS'],
                                            included_types=config['MAPS_NEARBY']['INCLUDED_TYPES'])

                    save_scraped_data(csv_path, card_info, details, description, places)
                    existing_links.add(card_info["Link"])

        print("Scraping completed for page:", page_num)

if __name__ == "__main__":
    main()
