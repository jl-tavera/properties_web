import json
import pandas as pd
from openai import OpenAI


def extract_place_info_from_text(input_text: str, api_key: str) -> dict:
    """
    Sends a JSON string of places to OpenAI and extracts structured information.

    Parameters:
        input_text (str): A JSON string representing a list of places.
        api_key (str): Your OpenAI API key.

    Returns:
        dict: A dictionary with keys:
            - 'places': list of all 'nombre' values
            - 'location': deduplicated list of neighborhoods from 'dirección'
            - 'transportation': 'nombre' values where 'tipos' includes 
                                'bus_stop' or 'transit_station'
    """
    client = OpenAI(api_key=api_key)

    system_prompt = (
        "You are a strict JSON parser. A user will give you a JSON string representing a list of places.\n"
        "Each place has 'nombre', 'dirección', 'tipos', and 'distancia_km'.\n\n"
        "Return ONLY a JSON object with:\n"
        "- 'places': list of all 'nombre' values\n"
        "- 'location': deduplicated list of neighborhood names found in 'dirección' "
        "(e.g., 'Santa Fé', 'Chapinero', etc.)\n"
        "- 'transportation': list of 'nombre' values where 'tipos' contains 'bus_stop' or 'transit_station'\n\n"
        "You must only return a valid JSON object with those three keys. Do not explain or say anything else."
    )

    # Define structured response format with a schema
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "place_extraction_schema",
            "schema": {
                "type": "object",
                "properties": {
                    "places": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "location": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "transportation": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["places", "location", "transportation"]
            }
        }
    }

    # Make request to OpenAI API
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": input_text}
        ],
        response_format=response_format
    )

    # Parse and return the JSON content
    return json.loads(response.choices[0].message.content)


def summarize_property_description(input_text: str, api_key: str) -> str:
    """
    Sends a property description to OpenAI and returns a concise, natural-language summary
    using controlled vocabulary for use in embeddings.

    Parameters:
        input_text (str): A paragraph describing a property.
        api_key (str): Your OpenAI API key.

    Returns:
        str: A short, coherent summary in natural language following a controlled vocabulary.
    """
    client = OpenAI(api_key=api_key)

    system_prompt = (
        "Eres un modelo que resume descripciones inmobiliarias. "
        "Tu tarea es generar un resumen breve (menos de 700 caracteres), natural y coherente del párrafo proporcionado, "
        "usando únicamente el siguiente vocabulario controlado:\n\n"
        "- tipo_de_vista: vista panorámica, vista urbana, vista cerrada, vista interior, sin vista\n"
        "- iluminacion_natural: iluminación abundante, iluminación moderada, iluminación limitada\n"
        "- acabados: acabados lujosos, acabados modernos, acabados sencillos, acabados utilitarios, acabados básicos\n"
        "- estado_general: nuevo, bien cuidado, habitable, por renovar, en mal estado\n"
        "- distribucion: distribución abierta, distribución compartimentada, diseño tradicional, planta libre\n"
        "- entorno_exterior: entorno urbano, entorno suburbano, entorno natural, densamente construido, con áreas verdes\n"
        "- materiales_cocina: madera laminada, granito, acero inoxidable, cerámica, madera natural, melamina\n"
        "- estado_paredes_techos: en buen estado, con desgaste, con humedad, recientemente renovados\n\n"
        "No incluyas metadatos estructurados como número de habitaciones, metros cuadrados o parqueadero.\n"
        "No repitas información redundante. Solo responde con el resumen en lenguaje natural. No expliques nada."
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": input_text}
        ]
    )

    return response.choices[0].message.content.strip()

def llm_formating(df: pd.DataFrame, api_key: str) -> pd.DataFrame:
    """
    Procesa simultáneamente descripciones de propiedades y mapeo de lugares en un DataFrame.

    - Para descripciones, utiliza 'description_input' -> 'description'
    - Para lugares, utiliza 'places_input' -> 'places', 'location', 'transportation'

    Parámetros:
        df (pd.DataFrame): DataFrame con columnas de entrada y a generar.
        api_key (str): API key para OpenAI.

    Retorna:
        pd.DataFrame: DataFrame con las columnas procesadas.
    """
    # Asegurar columnas de salida
    if "description" not in df.columns:
        df["description"] = None
    if "places" not in df.columns:
        df["places"] = None
    if "location" not in df.columns:
        df["location"] = None
    if "transportation" not in df.columns:
        df["transportation"] = None

    total = len(df)
    for i, row in df.iterrows():
        # --- Procesar descripción inmobiliaria ---
        if pd.isna(row["description"]) and pd.notna(row.get("description_input")):
            try:
                resumen = summarize_property_description(row["description_input"], api_key)
                df.at[i, "description"] = resumen
                print(f"[{i+1}/{total}] Descripción procesada correctamente")
            except Exception as e:
                print(f"[{i+1}/{total}] Error en descripción fila {i}: {e}")

        # --- Procesar mapeo de lugares ---
        if pd.isna(row["places"]) and pd.notna(row.get("places_input")):
            input_text = row["places_input"]
            try:
                result = extract_place_info_from_text(input_text, api_key)

                # Limpiar y convertir a strings para CSV
                df.at[i, "places"] = result["places"]
                df.at[i, "location"] = result["location"]
                df.at[i, "transportation"] = result["transportation"]


                print(f"[{i+1}/{total}] Lugares procesados correctamente")
            except Exception as e:
                print(f"[{i+1}/{total}] Error en lugares fila {i}: {e}")

    df.drop(columns=['description_input', 'places_input'], inplace=True)
    return df