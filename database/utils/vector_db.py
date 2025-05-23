import re
import pandas as pd
from qdrant_client import models, QdrantClient
from sentence_transformers import SentenceTransformer


CONTROLLED_VOCAB = {
    "tipo_de_vista": [
        "vista panorámica", "vista urbana", "vista cerrada", "vista interior", "sin vista"
    ],
    "iluminacion_natural": [
        "iluminación abundante", "iluminación moderada", "iluminación limitada"
    ],
    "acabados": [
        "acabados lujosos", "acabados modernos", "acabados sencillos",
        "acabados utilitarios", "acabados básicos"
    ],
    "estado_general": [
        "nuevo", "bien cuidado", "habitable", "por renovar", "en mal estado"
    ],
    "distribucion": [
        "distribución abierta", "distribución compartimentada",
        "diseño tradicional", "planta libre"
    ],
    "entorno_exterior": [
        "entorno urbano", "entorno suburbano", "entorno natural",
        "densamente construido", "con áreas verdes"
    ],
    "materiales_cocina": [
        "madera laminada", "granito", "acero inoxidable", "cerámica",
        "madera natural", "melamina"
    ],
    "estado_paredes_techos": [
        "en buen estado", "con desgaste", "con humedad", "recientemente renovados"
    ]
}

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
def extract_features_from_df(df: pd.DataFrame, col: str) -> pd.DataFrame:
    def extract_features(text: str) -> list[str]:
        features = []
        for keywords in CONTROLLED_VOCAB.values():
            for keyword in keywords:
                if re.search(rf"\b{re.escape(keyword)}\b", text.lower()):
                    features.append(keyword)
                    break  # one per category
        return features

    df["features"] = df[col].fillna("").apply(extract_features)
    return df


def prepare_apartment_embeddings(df: pd.DataFrame) -> pd.DataFrame:
    def process_row(row):
        location = row.get("location", "Ubicacion desconocida")
        agency = row.get("agency", "Inmobiliaria desconocida")
        price = row.get("price", "?")
        area = row.get("area", "?")
        bedrooms = row.get("bedrooms", "?")
        bathrooms = row.get("bathrooms", "?")
        stratum = row.get("stratum", "?")
        floor = row.get("floor", "?")
        facilities = ", ".join(row.get("facilities", []))
        features =  ", ".join(row.get("features", [])) or ""


        embedding_input = (
            f"Ubicación: {location}. "
            f"Agencia: {agency}. "
            f"Precio: {price} COP. "
            f"Área: {area} m². Habitaciones: {bedrooms}. Baños: {bathrooms}. "
            f"Estrato: {stratum}. Piso: {floor}. "
            f"Comodidades: {facilities}. "
            f"Características: {features}. "
        )

        return embedding_input

    # Create the input column
    df["embeddings_input"] = df.apply(process_row, axis=1)

    return df

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
            "location": row["location"][1:-1],
            "transportation": row["transportation"],
            "description": row["description"],
        }
        document = Document(page_content=row["embeddings_input"], metadata=metadata)
        documents.append(document)
    return documents

def create_collection(client, encoder, collection_name: str):
    # Creates a collection in Qdrant
    client.recreate_collection(
        collection_name=collection_name,
       vectors_config=models.VectorParams(
        size=encoder.get_sentence_embedding_dimension(),
        distance=models.Distance.COSINE,
    ),)

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