import os
import csv
import re
import random

def get_request_headers(filepath="data/scraping/user_agents.csv"):
    """
    Load user agents from a CSV and return a headers dict
    with a randomly chosen User-Agent.
    """
    # Load all user agents
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
        "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8"
    }
    return headers

def parse_proxy_config(proxy_url):
    match = re.match(r"http://(.*?):(.*?)@(.*):(\d+)", proxy_url)
    if not match:
        raise ValueError("Proxy format is invalid.")
    username, password, host, port = match.groups()
    return {
        "server": f"http://{host}:{port}",
        "username": username,
        "password": password
    }