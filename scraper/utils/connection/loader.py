import os
import json
from dotenv import load_dotenv


def load_config(config_path):
    with open(config_path, "r") as f:
        config = json.load(f)
    return config

def load_env_variables(env_path=".env"):
    load_dotenv(dotenv_path=env_path)  

    env_dict = {key: value for key, value in os.environ.items()}
    return env_dict