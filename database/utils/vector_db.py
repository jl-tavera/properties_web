import os
import ast
import json
import warnings
import pandas as pd
from qdrant_client import models, QdrantClient
from sentence_transformers import SentenceTransformer

warnings.filterwarnings('ignore')
encoder = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

client = QdrantClient(
        url="http://localhost:6333"
)

class Document:
    def __init__(self, page_content, metadata):
        self.page_content = page_content
        self.metadata = metadata

# Convert DataFrame rows into Document objects
def df_to_documents(df):
    documents = []
    for _, row in df.iterrows():
        metadata = {
            "link": row["link"],
            "price": row["price"],
            "bedrooms": row["bedrooms"],
            "bathrooms": row["bathrooms"],
            "area": row["area"],
            "agency": row["agency"],
            "coordinates": row["coordinates"],
            "facilities": row["facilities"],
            "upload_date": row["upload_date"],
            "stratum": row["stratum"],
            "parking_lots": row["parking_lots"],
            "floor": row["floor"],
            "construction_age_min": row["construction_age_min"],
            "construction_age_max": row["construction_age_max"],
            "places": row["places"],
            "location": row["location"],
            "transportation": row["transportation"],
        }
        document = Document(page_content=row["description"], metadata=metadata)
        documents.append(document)
    return documents