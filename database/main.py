import os
import pandas as pd
from utils.gpt import *
from utils.preprocessing import *
from utils.vector_db import *


def main(file_path:str) -> pd.DataFrame:
    api_key = os.getenv("OPENAI_API_KEY")

    raw_path = os.path.join(file_path, "raw/listings.csv")
    clean_path = os.path.join(file_path, "clean/listings.csv")

    df = read_and_clean_csv(file_path= raw_path)

    json_cols = ['coordinates', 'facilities', 'technical_data']
    integer_cols = [ 'Bedrooms', 'Bathrooms', 'Area', 'td_Estrato']
    fillna_cols = ['construction_age_min', 'construction_age_max', 'td_Piso N°', 'td_Parqueaderos']
    drop_cols = ['td_Pisos interiores', 
                  'td_Administración', 
                  'td_Habitaciones',
                  'td_Antigüedad',
                  'td_Área Privada', 
                  'td_Área Construida',
                  'td_Baños',
                  'td_Estado',
                  'td_Tipo de Inmueble', 
                  'administracion', 
                  'Datetime_Added', 
                  'Location']
    rename_dict = {'Link': 'link',
                    'Price': 'price',
                    'Bedrooms': 'bedrooms',
                    'Bathrooms': 'bathrooms',
                    'Area': 'area',
                    'Agency': 'agency',
                    'td_Estrato': 'stratum',
                    'td_Parqueaderos': 'parking_lots',
                    'td_Piso N°': 'floor',
                    'places': 'places_input',
                    'description': 'description_input'}

    df = load_json_cols(df=df, cols=json_cols)
    df = calculate_total_price(df=df)
    df = expand_technical_data(df=df)
    df = parse_construction_age_range(df, "td_Antigüedad")
    df = format_integer_cols(df=df, cols=integer_cols)
    df = fillna_and_integer_cols(df=df, cols=fillna_cols)
    df = drop_and_rename_columns(df=df, cols_to_drop=drop_cols, cols_to_rename=rename_dict)
    df = llm_formating(df=df, api_key=api_key)
    df.to_csv(clean_path, index=False)


def populate_vector_db(file_path:str, 
                       collection_name:str) -> None:
    
    clean_path = os.path.join(file_path, "clean/listings.csv")
    df = read_and_clean_csv(clean_path)
    df.dropna(subset=['places'], inplace=True)
    encoder = create_encoder(model_name="paraphrase-multilingual-MiniLM-L12-v2")
    client = QdrantClient(url="http://localhost:6333")
    list_cols = ['coordinates', 'facilities', 'places', 'location', 'transportation']
    df = load_list_cols(df=df, cols=list_cols)
    # Create collection
    create_collection(client=client, encoder=encoder, collection_name=collection_name)

    # Populate collection
    documents = df_to_documents(df)
    populate_collection(client=client, 
                        encoder=encoder, 
                        df=df, 
                        collection_name=collection_name, 
                        documents=documents)
    
    print("Vector DB populated successfully.")



if __name__ == "__main__":
#    main(file_path='./database/assets/data')
    populate_vector_db(file_path='./database/assets/data',
                       collection_name='apartments')