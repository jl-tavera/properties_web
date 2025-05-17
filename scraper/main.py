import time
import re
import threading
from utils.scraping_utils import *
from utils.telegram_utils import *
from utils.processing_utils import *

LAST_UPDATE_ID = None

def run_scan():
    new_properties = []
    config = load_config("config.json")
    user_agents = load_user_agents()
    random_user_agent = choose_random_user_agent(user_agents)

    HEADERS = {
        "User-Agent": random_user_agent,
        "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8"
    }
    PROXIES = {
        "http": config["PROXY"],
        "https": config["PROXY"]
    }
    BOT_TOKEN = config["BOT_TOKEN"]
    CHAT_ID = config["CHAT_ID"]
    URLS = config["URLS"]
    COLS = config["COLS"]
    CSV_FILENAME = config["CSV_FILENAME"]

    TYPOLOGY_PATTERN = re.compile(r"(\d+)\s*Habs\.?\s*(\d+)\s*Baño[s]?\s*(\d+)\s*m²")

    links = existing_links(csv_filename=CSV_FILENAME)

    for url in URLS:
        ip_info = get_ip_info(proxies=PROXIES)
        cards = scrape_listing_page(url=url, headers=HEADERS, proxies=PROXIES)
        for card in cards:
            card_info = scrape_listing_card(card=card, existing_links=links,
                                            typology_pattern=TYPOLOGY_PATTERN, ip_info=ip_info)
            if card_info:
                msg = format_card_msg(card_info)
                print(msg)
                send_telegram_message(msg, chat_id=CHAT_ID, bot_token=BOT_TOKEN)
                links.add(card_info["Link"])
                new_properties.append(card_info)

    if new_properties:
        save_new_cards(csv_filename=CSV_FILENAME,
                       new_properties=new_properties,
                       csv_columns=COLS)
        msg = f"✅ Scraping completed. {len(new_properties)} new properties found."
        send_telegram_message(msg, chat_id=CHAT_ID, bot_token=BOT_TOKEN)
        print(msg)
    else:
        print("No new properties found.")


def manual_command_listener(bot_token, chat_id):
    global LAST_UPDATE_ID
    while True:
        try:
            updates = get_bot_updates(bot_token)

            if "result" in updates:
                for update in updates["result"]:
                    update_id = update["update_id"]

                    if LAST_UPDATE_ID is not None and update_id <= LAST_UPDATE_ID:
                        continue

                    message = update.get("message", {})
                    text = message.get("text", "")

                    if text.strip().lower() == "/scan":
                        send_telegram_message("🔍 Manual scan triggered.", chat_id, bot_token)
                        print("Manual scan command received.")
                        run_scan()

                    LAST_UPDATE_ID = update_id

            time.sleep(5)
        except Exception as e:
            print(f"❌ Error in manual listener: {e}")
            time.sleep(10)


def auto_scan_loop():
    while True:
        try:
            print("🕔 Running automatic scan...")
            run_scan()
            print("⏳ Next scan in 5 minutes...\n")
            time.sleep(300)
        except Exception as e:
            print(f"❌ Error in auto scan: {e}")
            time.sleep(60)


def main():
    config = load_config("config.json")
    BOT_TOKEN = config["BOT_TOKEN"]
    CHAT_ID = config["CHAT_ID"]

    threading.Thread(target=auto_scan_loop, daemon=True).start()
    threading.Thread(target=manual_command_listener, args=(BOT_TOKEN, CHAT_ID), daemon=True).start()

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
