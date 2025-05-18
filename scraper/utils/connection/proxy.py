import os
import csv
import re
import random

def get_request_headers(config):
    
    filepath = config['PROXY']['USER_AGENTS_PATH']
    accept_language = config['PROXY']['ACCEPT_LANGUAGE']
    accept = config['PROXY']['ACCEPT']

    with open(filepath, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        agents = [row["user_agent"] for row in reader]
        if not agents:
            raise ValueError(f"No user agents found in {filepath}")

    # Choose one at random
    random_user_agent = random.choice(agents)
    # Build headers
    headers = {
        "User-Agent": random_user_agent,
        "Accept-Language": accept_language,
        "Accept": accept,
    }
    return headers

def proxy_dicts(env_dict):

    proxy = env_dict.get("PROXY")
    match = re.match(r"http://(.*?):(.*?)@(.*):(\d+)", proxy)
    if not match:
        raise ValueError("Proxy format is invalid.")
    username, password, host, port = match.groups()

    proxy_server_dict =  {
        "server": f"http://{host}:{port}",
        "username": username,
        "password": password
    }

    proxy_http_dict = {
        "http": proxy,
        "https": proxy
    }

    return proxy_server_dict, proxy_http_dict

def get_proxies(env_dict, config):
    proxy_server_dict, proxy_http_dict = proxy_dicts(env_dict)
    headers = get_request_headers(config)
    return headers, proxy_server_dict, proxy_http_dict