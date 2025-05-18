import os
import json
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