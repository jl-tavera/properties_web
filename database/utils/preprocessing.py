import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from dotenv import load_dotenv

def load_env_variables(env_path=".env"):
    """
    Loads environment variables from a .env file.
    """
    load_dotenv(dotenv_path=env_path)

def try_fix_unicode(text):
    if isinstance(text, str) and '\\u' in text:
        try:
            return text.encode('utf-8').decode('unicode_escape')
        except Exception:
            return text  # if decoding fails, return original
    else:
        return text


def read_and_clean_csv(file_path:str):
        # Read the CSV with latin1 encoding to avoid UnicodeDecodeError
    print(file_path)
    df = pd.read_csv(filepath_or_buffer=file_path, encoding="latin1")


    # Fix garbled text (mojibake) in all string columns
    for col in df.select_dtypes(include='object'):
        df[col] = df[col].apply(lambda x: x.encode('latin1').decode('utf-8') if isinstance(x, str) else x)
    for col in df.select_dtypes(include='object'):
        df[col] = df[col].apply(try_fix_unicode)
    return df

def load_json_cols(df: pd.DataFrame, cols: list): 
    for col in cols:
        df[col] = df[col].apply(json.loads)
        if col == 'coordinates':
            df[col] = df[col].apply(tuple)

    return df

def calculate_total_price(df: pd.DataFrame) -> pd.DataFrame:
    df['administracion'] = df['administracion'].fillna(0)
    df['Price'] = df['Price'] + df['administracion']
    df['Price'] = df['Price'].astype(int)
    return df

def expand_technical_data(df: pd.DataFrame) -> pd.DataFrame:
    
    td_df = pd.json_normalize(df['technical_data'])
    td_df = td_df.add_prefix('td_')
    df_expanded = pd.concat([df.drop(columns=['technical_data']), td_df], axis=1)
    return df_expanded


def format_integer_cols(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    df = df.dropna(subset=[cols[0]])
    df = df.dropna(subset=['td_Estrato'])

    df = df.reset_index(drop=True)
    for col in cols:
        df[col] = df[col].astype(int)

    return df


def parse_construction_age_range(df, col_name):
    def parse_range(value):
        if not isinstance(value, str):
            return (np.nan, np.nan)  # Por ejemplo, para NaNs o valores no string
        
        value = value.lower().strip()

        if "menor a 1 año" in value:
            return (0, 1)
        elif "más de" in value:
            try:
                num = int(value.split("más de")[1].split("año")[0].strip())
                return (num + 1, 100)  # e.g., más de 30 → (31, inf)
            except:
                return (np.nan, np.nan)
        elif "a" in value:
            try:
                parts = value.split("a")
                min_age = int(parts[0].strip())
                max_age = int(parts[1].split("año")[0].strip())
                return (min_age, max_age)
            except:
                return (np.nan, np.nan)
        else:
            return (np.nan, np.nan)  # fallback para valores inesperados

    df["construction_age_min"], df["construction_age_max"] = zip(*df[col_name].map(parse_range))
    return df


def fillna_and_integer_cols(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    for col in cols:
        if col == 'td_Parqueaderos':
            df[col] = df[col].fillna(0)
        else:
            df[col] = df[col].fillna(-1)

        df[col] = df[col].astype(int)
    return df

def drop_and_rename_columns(df: pd.DataFrame, cols_to_drop: list, cols_to_rename: dict) -> pd.DataFrame:
    df = df.drop(columns=cols_to_drop)
    df = df.rename(columns=cols_to_rename)
    return df