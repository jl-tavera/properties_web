import requests
from scraper.utils.processing.geocalc import calculate_distance

# Unified search function
def get_nearby_places_combined(api_key:str, 
                               latitude:float, 
                               longitude:float, 
                               radius: int ,
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
        "languageCode": "es-CO"
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        return []

    data = response.json()
    results = []
    for place in data.get("places", []):
        loc = place.get("location", {})
        dist = calculate_distance(lat1 = latitude, 
                                  lon1=longitude, 
                                  lat2= loc["latitude"], 
                                  lon2 = loc["longitude"]) if loc else None
        results.append({
            "name": place.get("displayName", {}).get("text", ""),
            "address": place.get("formattedAddress", ""),
            "types": place.get("types", []),
            "distance_km": round(dist, 2) if dist else None
        })

    return results



# Example usage
api_key = "AIzaSyD0NGH4rFgsAciNSwUPfgIqnPvdWT1C7Fw"
latitude = 4.657228974520381
longitude = -74.1244125366211
places = get_nearby_places_combined(api_key, latitude, longitude)
for place in places:
    print(f"{place['name']} - {place['distance_km']} km away ({', '.join(place['types'])})")