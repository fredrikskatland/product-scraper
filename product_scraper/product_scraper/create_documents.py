import os
import re

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Adjust this import to match your actual package/module structure.
# For example, if models.py is at the same level:
from models import Product, Base

###################################
# Optional numeric field handling #
###################################

NUMERIC_FIELDS = {"price"}

def parse_numeric(value: str):
    """
    Given a string like '2400,-' or '1,899.95' or '6',
    return a float. If parsing fails, return None.
    """
    cleaned = re.sub(r"[^0-9,\.]", "", value)
    # If there's a comma but no period, treat comma as decimal
    if "," in cleaned and "." not in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None

def sanitize_metadata(metadata: dict) -> dict:
    """
    Convert or omit any values that might be invalid for your vector DB or pipeline.
    - Remove leading colons from strings.
    - Convert "price" to an integer if possible.
    - Convert known numeric fields (like 'dropp', 'weight') to float.
    """
    cleaned = {}
    for key, value in metadata.items():
        if value is None:
            continue

        # 1) If it's a string, remove leading colons like ": something"
        if isinstance(value, str):
            # This regex removes any colon (and optional whitespace) at the start of the string
            # e.g. ": Lightweight PU sole" -> "Lightweight PU sole"
            value = re.sub(r"^\s*:\s*", "", value)

        # 2) Special handling for known numeric fields
        if key in NUMERIC_FIELDS:
            if isinstance(value, str):
                numeric_val = parse_numeric(value)
                if numeric_val is not None:
                    # If it's specifically "price", convert float -> int
                    if key == "price":
                        value = int(numeric_val)
                    else:
                        # e.g. weight or dropp can remain float
                        value = numeric_val
                # If parse fails, we leave value as-is (the raw string), or choose to skip
            elif isinstance(value, (int, float)):
                # If it's already numeric but "price" must be an integer
                if key == "price":
                    value = int(value)

        # 3) Ensure the final type is acceptable (e.g. str, int, float, bool, list[str])
        if isinstance(value, (bool, int, float, str)):
            cleaned[key] = value
        elif isinstance(value, list):
            # Convert each element to string
            str_list = [str(elem) if elem is not None else "N/A" for elem in value]
            cleaned[key] = str_list
        else:
            # fallback: convert to string
            cleaned[key] = str(value)

    return cleaned

########################
# Building the Document
########################

def build_page_content(product: Product) -> str:
    """
    Constructs a single string with the main fields + any extras.
    Adjust to your liking.
    """
    lines = []
    if product.product_name:
        lines.append(f"Product Name: {product.product_name}")
    if product.brand:
        lines.append(f"Brand: {product.brand}")
    if product.description:
        lines.append(f"Description: {product.description}")
    if product.price:
        lines.append(f"Price: {product.price}")
    if product.url:
        lines.append(f"URL: {product.url}")
    if product.shop:
        lines.append(f"Shop: {product.shop}")
    
    # Include extras in the page content if you like:
    if product.extras:
        lines.append("Extras:")
        for k, v in product.extras.items():
            lines.append(f"  - {k}: {v}")

    return "\n\n".join(lines)

def build_metadata(product: Product) -> dict:
    """
    Builds a dictionary of metadata from the product fields + extras.
    We'll later sanitize it.
    """
    metadata = {
        "shop": product.shop,
        "url": product.url,
        "product_name": product.product_name,
        #"price": product.price,
        #"brand": product.brand,
        "description": product.description,
    }
    # Merge extras into metadata if you want them at top level
    # Alternatively, store them under a single key: e.g. metadata["extras"] = product.extras
    if product.extras:
        for k, v in product.extras.items():
            metadata[k] = v

    return metadata

########################
# Main entry point
########################

def create_documents(db_path=None):
    """
    Connects to the SQLite DB, fetches all Product rows, builds
    a list of LangChain Document objects.
    """
    from langchain_core.documents import Document  # or from langchain.schema import Document
    # Adjust your import to the actual Document location
    
    # If no db_path is given, fallback to 'products.db' in current dir
    if not db_path:
        db_path = "products.db"

    # If the path is relative, or if you need to ensure a full path:
    # db_path = os.path.abspath(db_path)

    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database file not found: {db_path}")

    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    session = Session()

    # Query all rows from the products table
    products = session.query(Product).all()

    documents = []
    for product in products:
        page_content = build_page_content(product)
        raw_metadata = build_metadata(product)
        clean_meta = sanitize_metadata(raw_metadata)

        doc = Document(page_content=page_content, metadata=clean_meta)
        documents.append(doc)

    session.close()
    return documents

if __name__ == "__main__":
    # Example usage
    docs = create_documents("products.db")
    print(f"Created {len(docs)} documents.")
    if docs:
        print("\nExample Document 'page_content':\n", docs[1].page_content)
        print("\nMetadata:", docs[1].metadata)
