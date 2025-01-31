import os
import yaml
import scrapy
from scrapy import Selector
from product_scraper.items import ProductScraperItem
from scrapy_playwright.page import PageMethod


class UniversalSpider(scrapy.Spider):
    name = "universal_spider"

    def __init__(self, config_file=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if not config_file:
            raise ValueError("You must provide a 'config_file' argument, e.g. -a config_file=shop1.yaml")

        # Load YAML
        with open(config_file, 'r') as f:
            self.config = yaml.safe_load(f)

        self.shop_name = self.config.get("name", "unknown_shop")
        self.sitemap_url = self.config.get("sitemap_url")
        if not self.sitemap_url:
            raise ValueError("No 'sitemap_url' found in config.")

        # Optional ignore patterns
        self.ignore_patterns = self.config.get("ignore_patterns", [])

    def start_requests(self):
        """
        1) Send a request to fetch the sitemap_url.
        2) We'll parse the returned XML in parse_sitemap.
        """
        

        yield scrapy.Request(
            url=self.sitemap_url,
            callback=self.parse_sitemap
        )

    def parse_sitemap(self, response):
        sel = Selector(text=response.text, type="xml")
        loc_list = sel.xpath('//*[local-name()="url"]/*[local-name()="loc"]/text()').getall()

        for loc in loc_list:
            loc = loc.strip()
            if any(pattern in loc for pattern in self.ignore_patterns):
                continue

            yield scrapy.Request(
                url=loc
                , callback=self.parse_product
                , cookies = {
                    # The key is the cookie name, the value is the cookie value
                    "CookieInformationConsent": '{"website_uuid":"52df4073-8d76-4ae7-8ae2-056b80c5f4b5","timestamp":"2025-01-30T21:22:48.268Z","consent_url":"https://www.barnashus.no/voksi/breeze-light-vognpose-softgrape-fields","consent_website":"barnashus.no","consent_domain":"www.barnashus.no","user_uid":"b6d439ef-8095-4104-a466-62189ff83d34","consents_approved":["cookie_cat_necessary","cookie_cat_functional","cookie_cat_statistic","cookie_cat_marketing","cookie_cat_unclassified"],"consents_denied":[],"user_agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"}'
                }
                , meta={
                    "playwright": True,
                    "playwright_page_methods": [
                        PageMethod("wait_for_selector", 'p'), 
                    ]
                }
                )

    def parse_product(self, response):
        """
        Parse the actual product detail page using the selectors from the config.
        """
        selectors = self.config.get("selectors", {})
        extras_selectors = self.config.get("extras", {})

        item = ProductScraperItem()
        item['shop'] = self.shop_name
        item['url'] = response.url

        # Standard fields
        item['product_name'] = self.extract_field(response, selectors.get('product_name'))
        item['price']        = self.extract_field(response, selectors.get('price'))
        item['brand']        = self.extract_field(response, selectors.get('brand'))
        item['description']  = self.extract_field(response, selectors.get('description'))

        # Extras
        item['extras'] = {}
        for field_name, field_config in extras_selectors.items():
            val = self.extract_field(response, field_config)
            if val:
                item['extras'][field_name] = val

        yield item

    # ---------------------------------------------------------------------
    # Helper Methods
    # ---------------------------------------------------------------------

    def extract_field(self, response, field_config):
        """
        If field_config is a string, do single extraction.
        If it's a dict with {'selector': '...', 'join_text': True}, do multiple extraction + join.
        """
        if not field_config:
            return None
        
        if isinstance(field_config, str):
            # single extraction
            return self.extract_first(response, field_config)
        
        # assume dict with "selector" and optional "join_text"
        sel = field_config.get("selector")
        join_text = field_config.get("join_text", False)
        if not sel:
            return None

        if join_text:
            all_parts = self.extract_all(response, sel)
            return " ".join(all_parts).strip() if all_parts else None
        else:
            return self.extract_first(response, sel)

    def extract_first(self, response, selector):
        """
        Utility: If '::' in the selector -> CSS, else XPath.
        Return first result or None.
        """
        if not selector:
            return None
        if '::' in selector:
            return response.css(selector).get(default="").strip() or None
        else:
            return response.xpath(selector).get(default="").strip() or None

    def extract_all(self, response, selector):
        """
        Utility: gather all text, strip each, return as list of strings.
        """
        if not selector:
            return []
        if '::' in selector:
            return [t.strip() for t in response.css(selector).getall() if t.strip()]
        else:
            return [t.strip() for t in response.xpath(selector).getall() if t.strip()]
