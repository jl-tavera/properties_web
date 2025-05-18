import math

# Distance calculator (Haversine formula)
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371.0  # Radius of Earth in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def pixel_to_latlng(pixel_x, pixel_y, zoom):
    scale = 256 * 2**zoom
    lng = pixel_x / scale * 360.0 - 180.0
    n = math.pi - (2 * math.pi * pixel_y) / scale
    lat = math.degrees(math.atan(math.sinh(n)))
    return lat, lng