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
        
        # Try to get a list of sitemap URLs; if not provided, fallback to a single sitemap_url.
        self.sitemap_urls = self.config.get("sitemap_urls")
        if not self.sitemap_urls:
            sitemap_url = self.config.get("sitemap_url")
            if not sitemap_url:
                raise ValueError("No 'sitemap_url' or 'sitemap_urls' found in config.")
            self.sitemap_urls = [sitemap_url]

        # Optional ignore patterns
        self.ignore_patterns = self.config.get("ignore_patterns", [])

    def start_requests(self):
        """
        For each sitemap URL provided, send a request to fetch it.
        """
        for url in self.sitemap_urls:
            yield scrapy.Request(
                url=url,
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
        if not selector:
            return None
        s = selector.strip()
        # If the selector starts with '/', '.', or '(', treat it as XPath.
        if s[0] in ('/', '.', '('):
            return response.xpath(selector).get(default="").strip() or None
        else:
            return response.css(selector).get(default="").strip() or None


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
