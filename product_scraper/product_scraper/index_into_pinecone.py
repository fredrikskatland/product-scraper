"""
index_into_pinecone.py

This module demonstrates how to index local scraped documents (from a SQLite DB)
into a Pinecone vector index using LangChain. It:

1. Reads environment variables for Pinecone and OpenAI API keys.
2. Connects to (and if needed, creates) a Pinecone index.
3. Wraps the Pinecone index with LangChain's PineconeVectorStore.
4. Tracks metadata of inserted documents using SQLRecordManager.
5. Creates a LangChain 'Index' object and prints it for verification.

To run:

  1. Set environment variables:
     - $env:PINECONE_API_FINN="your-pinecone-api-key"
     - $env:OPENAI_API_KEY="your-openai-api-key"
  2. Ensure you have all dependencies installed (langchain, pinecone, etc.).
  3. Execute: python index_into_pinecone.py
     or add the --test flag: python index_into_pinecone.py --test
"""

import os
import time
import argparse

# Pinecone imports
from pinecone import Pinecone, ServerlessSpec

# LangChain imports
from langchain.indexes import SQLRecordManager
from langchain.indexes import index as LangchainIndex
from langchain_openai import OpenAIEmbeddings  # or langchain_community.embeddings
from langchain_pinecone import PineconeVectorStore

# Local import: your script that creates Document objects
from create_documents import create_documents

# loading .env file
from dotenv import load_dotenv
load_dotenv()

def main():
    """
    Main entry point: sets up Pinecone, creates/loads a vector index, and prints a LangChain Index object.

    Raises:
        ValueError: If PINECONE_API_FINN or OPENAI_API_KEY environment variables are not set.
    """

    # -------------------------------------------------------------------
    # 1. Parse command-line arguments to detect if we're running in test mode.
    # -------------------------------------------------------------------
    parser = argparse.ArgumentParser(description="Index documents into a Pinecone vector store.")
    parser.add_argument("--test", action="store_true", help="Use a '-test' suffix on the index name.")
    args = parser.parse_args()

    # -------------------------------------------------------------------
    # 2. Grab the API keys from environment variables
    # -------------------------------------------------------------------
    pinecone_api_key = os.getenv("PINECONE_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not pinecone_api_key or not openai_api_key:
        raise ValueError("Please set the PINECONE_API_KEY and OPENAI_API_KEY environment variables.")

    # -------------------------------------------------------------------
    # 3. Create LangChain Embeddings object
    # -------------------------------------------------------------------
    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)

    # -------------------------------------------------------------------
    # 4. Initialize Pinecone client
    # -------------------------------------------------------------------
    pc = Pinecone(api_key=pinecone_api_key)

    # -------------------------------------------------------------------
    # 5. Determine index name with optional '-test' suffix
    # -------------------------------------------------------------------
    
    base_index_name = os.getenv("INDEX_NAME")
    if not base_index_name:
        raise ValueError("Please set the INDEX_NAME environment variable.")

    if args.test:
        index_name = f"{base_index_name}-test"
    else:
        index_name = base_index_name

    # -------------------------------------------------------------------
    # 6. Create the index if it doesn't exist
    # -------------------------------------------------------------------
    existing_indexes = [idx["name"] for idx in pc.list_indexes()]
    if index_name not in existing_indexes:
        print(f"Creating Pinecone index: {index_name}")
        pc.create_index(
            name=index_name,
            dimension=1536,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        # Wait for the new index to become ready
        while not pc.describe_index(index_name).status["ready"]:
            time.sleep(1)

    # -------------------------------------------------------------------
    # 7. Reference the existing (or newly created) index
    # -------------------------------------------------------------------
    index = pc.Index(index_name)

    # -------------------------------------------------------------------
    # 8. Create a PineconeVectorStore for LangChain
    # -------------------------------------------------------------------
    vectorstore = PineconeVectorStore(index=index, embedding=embeddings)

    # -------------------------------------------------------------------
    # 9. Set up a local record manager (optionally suffix the namespace too)
    # -------------------------------------------------------------------
    local_namespace = f"pinecone/{index_name}"
    record_manager = SQLRecordManager(
        namespace=local_namespace, 
        db_url="sqlite:///record_manager_cache.sql"
    )
    record_manager.create_schema()  # ensure DB tables exist

    # -------------------------------------------------------------------
    # 10. Create or load your documents from the local SQLite DB
    # -------------------------------------------------------------------
    db_path = os.getenv("DB_PATH")
    documents = create_documents(db_path=db_path)

    print(documents[5])  # print the first document for verification

    # -------------------------------------------------------------------
    # 11. Build a LangChain 'Index' object that ties everything together
    # -------------------------------------------------------------------
    lc_index = LangchainIndex(
        documents,
        record_manager,
        vectorstore,
        cleanup="scoped_full",   # remove documents only within this scope if re-indexing
        source_id_key="url",     # use 'url' from metadata as the source identifier
    )

    # Printing the index primarily for debugging/verification
    print(lc_index)
    print(f"Successfully indexed documents into: {index_name}")


if __name__ == "__main__":
    main()
