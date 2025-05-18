import re
import pandas as pd

def parse_date_text(fecha_str):
    """
    Converts a Spanish date string like '5 de abril de 2025' into a pandas Timestamp.
    """
    # Mapping Spanish month names to their numeric equivalents
    meses = {
        'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
        'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
        'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
    }

    try:
        # Extract day, month, and year
        partes = fecha_str.lower().split(" de ")
        if len(partes) != 3:
            raise ValueError(f"Invalid date format: {fecha_str}")
        
        dia = partes[0].zfill(2)
        mes = meses.get(partes[1])
        anio = partes[2]

        if not mes:
            raise ValueError(f"Unknown month name: {partes[1]}")

        # Combine into ISO format
        fecha_iso = f"{anio}-{mes}-{dia}"
        return pd.to_datetime(fecha_iso)

    except Exception as e:
        print(f"Error parsing date: {e}")
        return pd.NaT
    
def extract_translate3d(style_str):
    match = re.search(r"translate3d\(([-\d.]+)px,\s*([-\d.]+)px", style_str)
    return (float(match.group(1)), float(match.group(2))) if match else (None, None)