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

    headless = config['CRAWLERS']['DETAIL']['HEADLESS']
    img_folder = config['GENERAL']['IMAGE_DIR']
    timeout = config['CRAWLERS']['DETAIL']['TIMEOUT']['REQUEST_TIMEOUT']
    element_timeout = config['CRAWLERS']['DETAIL']['TIMEOUT']['ELEMENT_TIMEOUT']

    url = "https://www.fincaraiz.com.co/arriendo/casas-y-apartamentos/bogota/bogota-dc/publicado-ultimos-30-dias?&ordenListado=3"
    cards = scrape_listing_page(url=url, headers=headers, proxies=proxy_http_dict)
    links = []
    typology_pattern = config['CRAWLERS']['LISTINGS']['TYPOLOGY_PATTERN']
    for card in cards:
        card_info = scrape_listing_card(card=card, 
                                        existing_links=links,
                                        typology_pattern=typology_pattern)
        if card_info:
                result = asyncio.run(scrape_details_page(headless=headless,
                                                         proxy =proxy_server_dict,
                                                         headers=headers,
                                                         url=card_info["Link"],
                                                         img_folder=img_folder,
                                                         timeout=timeout,
                                                         element_timeout=element_timeout))
                if result:
                     description = describe_apartment_images(api_key=env_dict['OPENAI_API_KEY'],
                                                             prompt_text=config['OPENAI']['PROMPT'],
                                                             model=config['OPENAI']['MODEL'],
                                                             image_detail=config['OPENAI']['IMAGE_DETAIL'],
                                                             max_tokens=config['OPENAI']['MAX_TOKENS'],
                                                             image_dir=img_folder)

                     print(description)

    return None


if __name__ == "__main__":
    main()
