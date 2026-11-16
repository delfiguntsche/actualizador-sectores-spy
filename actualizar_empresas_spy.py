import os
import pandas as pd
import requests
import yfinance as yf
from datetime import datetime
from io import StringIO

# 1. Obtener listado oficial de las empresas del S&P 500 desde Wikipedia
url_wiki = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
resp = requests.get(url_wiki, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
tabla_sp500 = pd.read_html(StringIO(resp.text))[0]

# Limpiar tickers para Yahoo Finance (ej. BRK.B -> BRK-B)
tabla_sp500['Ticker'] = tabla_sp500['Symbol'].str.replace('.', '-', regex=False)
info_empresas = tabla_sp500[['Ticker', 'Security', 'GICS Sector']].copy()
info_empresas.columns = ['Ticker', 'Empresa', 'Sector']

# 2. Consultar Market Cap en bloques de 100
tickers = info_empresas['Ticker'].tolist()
market_caps = {}

for i in range(0, len(tickers), 100):
    lote = tickers[i:i+100]
    data_lote = yf.Tickers(" ".join(lote))
    for t in lote:
        try:
            mc = data_lote.tickers[t].fast_info.get('marketCap', 0)
            if mc and mc > 0:
                market_caps[t] = mc
        except Exception:
            pass

# 3. Calcular el peso porcentual individual de cada empresa
df_mc = pd.DataFrame(list(market_caps.items()), columns=['Ticker', 'MarketCap'])
df_mes = pd.merge(info_empresas, df_mc, on='Ticker', how='inner')

total_mc = df_mes['MarketCap'].sum()
df_mes['Ponderacion_%'] = (df_mes['MarketCap'] / total_mc * 100).round(4)

# Validación de seguridad
if len(df_mes) < 480 or df_mes['Ponderacion_%'].sum() < 95:
    raise ValueError(f"Error: Solo se leyeron {len(df_mes)} empresas.")

mes_actual = datetime.now().strftime('%Y-%m')
df_mes.insert(0, 'Fecha', mes_actual)

# Seleccionar columnas finales y ordenar de mayor a menor peso
df_mes = df_mes[['Fecha', 'Ticker', 'Empresa', 'Sector', 'Ponderacion_%']]
df_mes = df_mes.sort_values(by='Ponderacion_%', ascending=False).reset_index(drop=True)

# 4. Guardar o actualizar el Excel histórico de empresas
archivo_excel = "SP500_Empresas_Historico.xlsx"

if os.path.exists(archivo_excel):
    df_hist = pd.read_excel(archivo_excel)
    df_hist['Fecha'] = df_hist['Fecha'].astype(str).str.strip()
    # Si el mes actual ya existe, lo reemplaza con los datos más recientes del cierre
    df_hist = df_hist[df_hist['Fecha'] != mes_actual]
    df_final = pd.concat([df_hist, df_mes], ignore_index=True)
else:
    df_final = df_mes

df_final.to_excel(archivo_excel, index=False)
print(f"Mes {mes_actual} guardado: {len(df_mes)} empresas. Top 1: {df_mes.iloc[0]['Ticker']} ({df_mes.iloc[0]['Ponderacion_%']}%)")
