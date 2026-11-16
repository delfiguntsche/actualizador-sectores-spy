import requests
import pandas as pd
import numpy as np
from io import BytesIO
import os

try:
    from google.colab import files
    EN_COLAB = True
except ImportError:
    EN_COLAB = False

ARCHIVO_EXCEL = "AAII_Sentiment_Historico.xlsx"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.aaii.com/sentimentsurvey/sent_results"
}

def descargar_desde_xls_oficial():
    url_xls = "https://www.aaii.com/files/surveys/sentiment.xls"
    resp = requests.get(url_xls, headers=headers, timeout=25)
    resp.raise_for_status()
    
    if b"<html" in resp.content[:500].lower():
        raise ValueError("AAII devolvió HTML en lugar del archivo XLS.")
        
    df_raw = pd.read_excel(BytesIO(resp.content), skiprows=3)
    df_raw.columns = [str(c).strip() for c in df_raw.columns]
    
    col_fecha = [c for c in df_raw.columns if 'date' in c.lower()][0]
    col_bull = [c for c in df_raw.columns if 'bullish' in c.lower() and 'avg' not in c.lower() and 'spread' not in c.lower()][0]
    col_neut = [c for c in df_raw.columns if 'neutral' in c.lower() and 'avg' not in c.lower()][0]
    col_bear = [c for c in df_raw.columns if 'bearish' in c.lower() and 'avg' not in c.lower()][0]
    
    df = df_raw[[col_fecha, col_bull, col_neut, col_bear]].copy()
    df.columns = ['Fecha', 'Bullish', 'Neutral', 'Bearish']
    
    df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
    df = df.dropna(subset=['Fecha', 'Bullish', 'Neutral', 'Bearish'])
    
    for col in ['Bullish', 'Neutral', 'Bearish']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        if df[col].max() <= 1.05:
            df[col] = df[col] * 100
            
    return df.dropna()

def descargar_desde_tabla_web():
    url_web = "https://www.aaii.com/sentimentsurvey/sent_results"
    resp = requests.get(url_web, headers=headers, timeout=20)
    resp.raise_for_status()
    
    tablas = pd.read_html(resp.text)
    df = tablas[0].copy()
    df.columns = ['Fecha', 'Bullish', 'Neutral', 'Bearish']
    
    anio_actual = pd.Timestamp.now().year
    def parsear_fecha(f_str):
        f_str = str(f_str).strip()
        dt = pd.to_datetime(f_str, errors='coerce')
        if pd.isna(dt):
            dt = pd.to_datetime(f"{f_str} {anio_actual}", errors='coerce')
            if pd.notna(dt) and dt > pd.Timestamp.now() + pd.Timedelta(days=7):
                dt = dt - pd.DateOffset(years=1)
        return dt

    df['Fecha'] = df['Fecha'].apply(parsear_fecha)
    for col in ['Bullish', 'Neutral', 'Bearish']:
        df[col] = df[col].astype(str).str.replace('%', '').str.strip()
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
    return df.dropna()

# 1. Descargar serie completa oficial (desde 1987) o respaldo web
try:
    df_nuevo = descargar_desde_xls_oficial()
    print("Descarga exitosa desde el archivo histórico oficial completo (.xls) de AAII.")
except Exception as e:
    print(f"Aviso: No se pudo descargar el .xls directo ({e}). Usando tabla web pública...")
    df_nuevo = descargar_desde_tabla_web()

df_nuevo['Fecha'] = df_nuevo['Fecha'].dt.strftime('%Y-%m-%d')

# 2. Combinar con el historial existente si ya existe el archivo en el repo
if os.path.exists(ARCHIVO_EXCEL):
    df_existente = pd.read_excel(ARCHIVO_EXCEL)
    df_existente['Fecha'] = pd.to_datetime(df_existente['Fecha']).dt.strftime('%Y-%m-%d')
    df_final = pd.concat([df_existente[['Fecha', 'Bullish', 'Neutral', 'Bearish']], df_nuevo])
else:
    df_final = df_nuevo

df_final = df_final.drop_duplicates(subset=['Fecha'], keep='last').sort_values('Fecha').reset_index(drop=True)

# 3. Calcular métricas analíticas sobre toda la serie histórica
for col in ['Bullish', 'Neutral', 'Bearish']:
    df_final[col] = df_final[col].round(2)

df_final['Bull_Bear_Spread'] = (df_final['Bullish'] - df_final['Bearish']).round(2)
df_final['Spread_MA_8W'] = df_final['Bull_Bear_Spread'].rolling(window=8, min_periods=1).mean().round(2)

# Percentil histórico del Spread (0 a 100%) comparado contra toda la historia desde 1987
df_final['Percentil_Historico_Spread'] = (df_final['Bull_Bear_Spread'].rank(pct=True) * 100).round(1)

def clasificar_sentimiento(row):
    if row['Bearish'] >= 50.0:
        return "Pesimismo Extremo (Señal Contrarian Alcista)"
    elif row['Bullish'] >= 50.0:
        return "Optimismo Extremo (Señal Contrarian Bajista)"
    elif row['Bull_Bear_Spread'] > 15.0:
        return "Alcista Elevado"
    elif row['Bull_Bear_Spread'] < -15.0:
        return "Bajista Elevado"
    else:
        return "Neutral / Rango Normal"

df_final['Regimen_Sentimiento'] = df_final.apply(clasificar_sentimiento, axis=1)

print(f"Serie completa cargada: {len(df_final)} semanas (desde {df_final['Fecha'].min()} hasta {df_final['Fecha'].max()})")

if EN_COLAB:
    display(df_final.head(3))
    display(df_final.tail(5))

df_final.to_excel(ARCHIVO_EXCEL, index=False)

if EN_COLAB:
    files.download(ARCHIVO_EXCEL)
