# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class ProductScraperItem(scrapy.Item):
    shop = scrapy.Field()
    url = scrapy.Field()
    product_name = scrapy.Field()
    price = scrapy.Field()
    brand = scrapy.Field()
    description = scrapy.Field()
    # ... any other standard fields for your domain

    # For site-specific features, you have two main options:
    # 1) Add an "extras" dict field for anything custom:
    extras = scrapy.Field()