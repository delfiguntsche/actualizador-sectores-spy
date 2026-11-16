import pandas as pd
import requests
import yfinance as yf
from datetime import datetime
from io import StringIO

# 1. Traer lista de empresas del S&P 500 y su sector oficial
url_wiki = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
resp = requests.get(url_wiki, headers={"User-Agent": "Mozilla/5.0"})
tabla_sp500 = pd.read_html(StringIO(resp.text))[0]
tabla_sp500['Ticker'] = tabla_sp500['Symbol'].str.replace('.', '-', regex=False)
mapa_sectores = dict(zip(tabla_sp500['Ticker'], tabla_sp500['GICS Sector']))

# 2. Consultar Market Cap en bloques de 100
tickers = list(mapa_sectores.keys())
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

# 3. Calcular los porcentajes sectoriales
df_mc = pd.DataFrame(list(market_caps.items()), columns=['Ticker', 'MarketCap'])
df_mc['Sector'] = df_mc['Ticker'].map(mapa_sectores).str.strip().str.lower()
sectores = (df_mc.groupby('Sector')['MarketCap'].sum() / df_mc['MarketCap'].sum() * 100).to_dict()

nuevos_datos = {
    'Real Estate': round(sectores.get('real estate', 0), 2),
    'Materials': round(sectores.get('materials', 0), 2),
    'Utilities': round(sectores.get('utilities', 0), 2),
    'Energy': round(sectores.get('energy', 0), 2),
    'Industrials': round(sectores.get('industrials', 0), 2),
    'Healthcare': round(sectores.get('health care', 0), 2),
    'Financials': round(sectores.get('financials', 0), 2),
    'Consumer Staples': round(sectores.get('consumer staples', 0), 2),
    'Consumer Discretionary': round(sectores.get('consumer discretionary', 0), 2),
    'Communication Services': round(sectores.get('communication services', 0), 2),
    'Information Technology': round(sectores.get('information technology', 0), 2),
}
nuevos_datos['Total'] = round(sum(nuevos_datos.values()), 2)

# Validación de seguridad
if nuevos_datos['Total'] < 95:
    raise ValueError(f"Error: Suma dio {nuevos_datos['Total']}%")

# 4. Leer el Excel del repositorio y actualizarlo
archivo_excel = "SP500_Sectores_Historico.xlsx"
df_hist = pd.read_excel(archivo_excel)
df_hist = df_hist.loc[:, ~df_hist.columns.str.contains('^Unnamed')]
df_hist['Fecha'] = df_hist['Fecha'].astype(str).str.strip()

mes_actual = datetime.now().strftime('%Y-%m')
nuevos_datos['Fecha'] = mes_actual

if mes_actual in df_hist['Fecha'].values:
    for col, val in nuevos_datos.items():
        df_hist.loc[df_hist['Fecha'] == mes_actual, col] = val
    print(f"Fila {mes_actual} actualizada.")
else:
    nueva_fila = pd.DataFrame([nuevos_datos])[df_hist.columns]
    df_hist = pd.concat([df_hist, nueva_fila], ignore_index=True)
    print(f"Nueva fila {mes_actual} agregada.")

# 5. Sobrescribir el mismo archivo Excel
df_hist.to_excel(archivo_excel, index=False)
