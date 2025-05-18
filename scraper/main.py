from utils.connection.loader import *
from utils.connection.proxy import *
from utils.crawler.details_crawler import *
from utils.crawler.listings_crawler import *
from utils.services.nearby import *
from utils.services.vision import *


def main():
    config = load_config("config.json")
    env_dict = load_env_variables(".env")

    return None


if __name__ == "__main__":
    main()
