#!/usr/bin/env python

import os
from elasticsearch import Elasticsearch
from dotenv import load_dotenv

def main():
    # Load environment variables from .env file if it exists
    load_dotenv()

    # Configuration from environment variables with defaults
    ES_HOST = os.getenv("ES_HOST", "http://localhost:9200")
    ES_USER = os.getenv("ES_USER")
    ES_PASSWORD = os.getenv("ES_PASSWORD")

    # Setup Elasticsearch client with authentication if provided
    if ES_USER and ES_PASSWORD:
        es = Elasticsearch(hosts=[ES_HOST], http_auth=(ES_USER, ES_PASSWORD), verify_certs=False)
    else:
        es = Elasticsearch(hosts=[ES_HOST], verify_certs=False)

    print(f"Connected to Elasticsearch at {ES_HOST}")

    # Confirm deletion
    confirmation = input("WARNING: This will delete ALL indices in Elasticsearch. Type 'DELETE' to confirm: ")
    if confirmation != "DELETE":
        print("Deletion cancelled.")
        return

    try:
        # Delete all indices
        response = es.indices.delete(index="data_chunks")
        print("All indices deleted successfully:")
        print(response)
    except Exception as e:
        print("Error deleting indices:", e)

if __name__ == "__main__":
    main()
