import requests
from utils.processing.geocalc import calculate_distance

# Unified search function
def get_nearby_places(api_key:str, 
                      latitude:float, 
                      longitude:float, 
                      radius: int,
                      included_types: list ) -> list:
    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.types,places.location"
    }

    payload = {
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": latitude,
                    "longitude": longitude
                },
                "radius": radius
            }
        },
        "includedTypes": included_types,
        "languageCode": "es-CO"  # Ya pides respuesta en español
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        return []

    data = response.json()
    resultados = []
    for lugar in data.get("places", []):
        loc = lugar.get("location", {})
        dist = calculate_distance(lat1=latitude, 
                                  lon1=longitude, 
                                  lat2=loc.get("latitude"), 
                                  lon2=loc.get("longitude")) if loc else None
        resultados.append({
            "nombre": lugar.get("displayName", {}).get("text", ""),
            "dirección": lugar.get("formattedAddress", ""),
            "tipos": lugar.get("types", []),
            "distancia_km": round(dist, 2) if dist else None
        })

    return resultados

