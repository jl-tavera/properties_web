import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def try_fix_unicode(text):
    if isinstance(text, str) and '\\u' in text:
        try:
            return text.encode('utf-8').decode('unicode_escape')
        except Exception:
            return text  # if decoding fails, return original
    else:
        return text


def read_and_clean_csv(file_path):
        # Read the CSV with latin1 encoding to avoid UnicodeDecodeError
    df = pd.read_csv(file_path= file_path, 
                     encoding="latin1")

    # Fix garbled text (mojibake) in all string columns
    for col in df.select_dtypes(include='object'):
        df[col] = df[col].apply(lambda x: x.encode('latin1').decode('utf-8') if isinstance(x, str) else x)
    return df

def load_json_format(df: pd.DataFrame, cols: list): 
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


def format_integer_cols(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    df = df.dropna(subset=[cols[0]])
    df = df.reset_index(drop=True)
    for col in cols:
        df[col] = df[col].astype(int)
        
    return df