import os
import json
import pandas as pd
from dotenv import load_dotenv


def load_config(config_filename="config.json"):
    base_dir = os.path.dirname(os.path.abspath(__file__))  
    scraper_dir = os.path.abspath(os.path.join(base_dir, "../../"))  
    config_path = os.path.join(scraper_dir, config_filename)

    with open(config_path, "r") as f:
        return json.load(f)

def load_env_variables(env_path=".env"):
    load_dotenv(dotenv_path=env_path)  

    env_dict = {key: value for key, value in os.environ.items()}
    return env_dict

def to_json_safe(obj):
    if isinstance(obj, set):
        return json.dumps(list(obj))
    else:
        return json.dumps(obj)

def save_scraped_data(csv_path, card_info, details, description, places):
    row = {
        "Link": card_info.get("Link"),
        "Price": card_info.get("Price"),
        "Bedrooms": card_info.get("Bedrooms"),
        "Bathrooms": card_info.get("Bathrooms"),
        "Area": card_info.get("Area"),
        "Agency": card_info.get("Agency"),
        "Location": card_info.get("Location"),
        "Datetime_Added": card_info.get("Datetime_Added"),
        "coordinates": to_json_safe(details.get("coordinates")),
        "administracion": details.get("administracion"),
        "facilities": to_json_safe(details.get("facilities")),
        "upload_date": details.get("upload_date"),
        "technical_data": to_json_safe(details.get("technical_data")),
        "description": f'"{description}"',
        "places": to_json_safe(places)
    }

    df_row = pd.DataFrame([row])

    if not os.path.exists(csv_path):
        df_row.to_csv(csv_path, index=False, mode='w')
    else:
        df_row.to_csv(csv_path, index=False, mode='a', header=False)

    print(f"Saved data for link: {card_info.get('Link')}")