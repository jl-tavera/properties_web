import warnings
from qdrant_client import models, QdrantClient
from sentence_transformers import SentenceTransformer

def create_client(url: str):
    # Creates a Qdrant client instance
    return QdrantClient(url=url)

def create_encoder(model_name: str):
    # Creates a SentenceTransformer encoder instance
    return SentenceTransformer(model_name)

class Document:
    def __init__(self, page_content, metadata):
        self.page_content = page_content
        self.metadata = metadata

# Convert DataFrame rows into Document objects
def df_to_documents(df):
    documents = []
    for idx, row in df.iterrows():
        metadata = {
            "id": int(idx),
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

def create_collection(client, encoder, collection_name: str):
    # Creates a collection in Qdrant
    client.recreate_collection(
        collection_name=collection_name,
       vectors_config=models.VectorParams(
        size=encoder.get_sentence_embedding_dimension(),
        distance=models.Distance.COSINE,
    ),
    )

def populate_collection(client, encoder, df):
    docs = df_to_documents(df)
    # Populates the collection with documents
    points = [
        models.PointStruct(
            id=idx, 
            vector=encoder.encode(doc.page_content).tolist(), 
            payload={'metadata': doc.metadata, 'page_content': doc.page_content}
        )

    for idx, doc in enumerate(docs)]

    client.upload_points(
    collection_name="apartments",
    points=points,)