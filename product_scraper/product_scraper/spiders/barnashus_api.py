import scrapy
import json
from product_scraper.items import ProductScraperItem

class BarnasHusSpider(scrapy.Spider):
    name = "barnashus_api"
    allowed_domains = ["barnashus.no"]
    start_urls = [
            "https://www.barnashus.no/barneklar?count=99999",
            "https://www.barnashus.no/barnevogn?count=99999",
            "https://www.barnashus.no/bilstol?count=99999",
            "https://www.barnashus.no/barnesko?count=99999",
            "https://www.barnashus.no/barnerommet?count=99999",
            "https://www.barnashus.no/ut-pa-tur?count=99999",
            "https://www.barnashus.no/utstyr-til-barn-og-baby?count=99999",
            "https://www.barnashus.no/mamma?count=99999",
            "https://www.barnashus.no/lek-og-fritid?count=99999",
            ]

    custom_settings = {
        "DEFAULT_REQUEST_HEADERS": {
            "x-requested-with": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/109.0.0.0 Safari/537.36"),
        },
    }

    def parse(self, response):
        self.logger.info(f"Status code: {response.status}")
        self.logger.debug(f"Body snippet: {response.text[:200]!r}")
        """
        Step 1:
        - Parse the JSON from https://www.barnashus.no/barneklar
        - Extract the product URLs from the products array
        - Yield new requests (to the product detail endpoint)
        """
        try:
            data = json.loads(response.text)  # or response.json() in newer Scrapy versions
        except json.JSONDecodeError:
            self.logger.error("Failed to decode JSON from the products endpoint.")
            return

        products = data.get("products", [])
        for product in products:
            relative_url = product.get("url")
            if not relative_url:
                continue

            # Build a full URL if needed. In some cases, relative_url already 
            # starts with /, so let's be safe:
            product_url = response.urljoin(relative_url)

            yield scrapy.Request(
                url=product_url,
                headers={
                    "x-requested-with": "XMLHttpRequest",
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                    "User-Agent": "Mozilla/5.0 ...",
                },
                callback=self.parse_product
            )

    def parse_product(self, response):
        """
        Step 2:
        - Parse the product-level JSON to get the fields (displayName, price inclVat, brand, description)
        """
        try:
            product_data = json.loads(response.text)  # or response.json()
        except json.JSONDecodeError:
            self.logger.error(f"Failed to decode JSON from product detail: {response.url}")
            return

        # Create the item
        item = ProductScraperItem()

        # Fill in core fields
        item["shop"] = "barnashus"
        item["url"] = response.url

        item["product_name"] = product_data.get("displayName")
        item["price"] = (
            product_data.get("price", {})
                        .get("current", {})
                        .get("inclVat")
        )

        # brand name
        brand_info = product_data.get("brandInfo", {})
        item["brand"] = brand_info.get("brandName")

        # description
        jsonLd_list = product_data.get("jsonLd", [])
        if jsonLd_list and isinstance(jsonLd_list, list):
            # Typically, the first element in jsonLd has the product description
            item["description"] = jsonLd_list[0].get("description")

        # Optionally handle other fields or your "extras" dict
        item['extras'] = {}
        
        # Category
        tracking_product = product_data.get("trackingProduct", {})
        item["extras"]["category"] = tracking_product.get("category")

        # Color
        item["extras"]["color"] = product_data.get("colorName")


        yield item
