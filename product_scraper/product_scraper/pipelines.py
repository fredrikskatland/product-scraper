# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
# pipelines.py

from itemadapter import ItemAdapter
import json
from sqlalchemy.exc import IntegrityError
from product_scraper.models import get_session, Product


class ProductScraperPipeline:
    def process_item(self, item, spider):
        return item

class SQLitePipeline:
    """
    Pipeline that writes items into a SQLite database using SQLAlchemy.
    """

    def __init__(self, db_path=None):
        """
        Initialize the pipeline with the database path.
        """
        self.db_path = db_path

    @classmethod
    def from_crawler(cls, crawler):
        """
        Scrapy convention: read settings to get the DB path if configured.
        """
        db_path = crawler.settings.get("SQLITE_DB_PATH", "sqlite:///products.db")
        return cls(db_path)

    def open_spider(self, spider):
        """
        Called when the spider is opened. We'll set up our DB session here.
        """
        self.session = get_session(db_path=self.db_path)

    def close_spider(self, spider):
        """
        Called when the spider is closed. We'll close the session here.
        """
        self.session.close()

    def process_item(self, item, spider):
        """
        Save each item to the database.
        """
        product = Product()
        product.shop = item.get("shop")
        product.url = item.get("url")
        product.product_name = item.get("product_name")
        product.price = item.get("price")
        product.brand = item.get("brand")
        product.description = item.get("description")

        # If we declared 'extras' as JSON, we can just assign the Python dict
        # If it's Text, we might do: product.extras = json.dumps(item.get("extras", {}))
        product.extras = item.get("extras", {})

        try:
            self.session.add(product)
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            spider.logger.warning(f"IntegrityError on item: {item}")

        return item
