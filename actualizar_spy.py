import pandas as pd
import requests
import yfinance as yf
from datetime import datetime
from io import StringIO

# 1. Traer lista oficial de empresas del S&P 500 y su sector desde Wikipedia
url_wiki = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
resp = requests.get(url_wiki, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
tabla_sp500 = pd.read_html(StringIO(resp.text))[0]

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

# 3. Calcular ponderaciones individuales por empresa
df_mc = pd.DataFrame(list(market_caps.items()), columns=['Ticker', 'MarketCap'])
df_emp_mes = pd.merge(info_empresas, df_mc, on='Ticker', how='inner')

total_mc = df_emp_mes['MarketCap'].sum()
df_emp_mes['Ponderacion_%'] = (df_emp_mes['MarketCap'] / total_mc * 100).round(4)

if len(df_emp_mes) < 480 or df_emp_mes['Ponderacion_%'].sum() < 95:
    raise ValueError(f"Error: Solo se leyeron {len(df_emp_mes)} empresas.")

mes_actual = datetime.now().strftime('%Y-%m')

# Preparar tabla de Empresas del mes
df_emp_final_mes = df_emp_mes[['Ticker', 'Empresa', 'Sector', 'Ponderacion_%']].copy()
df_emp_final_mes.insert(0, 'Fecha', mes_actual)
df_emp_final_mes = df_emp_final_mes.sort_values(by='Ponderacion_%', ascending=False).reset_index(drop=True)

# 4. Calcular ponderaciones por Sector (agrupando desde el mismo cálculo)
df_emp_mes['Sector_norm'] = df_emp_mes['Sector'].str.strip().str.lower()
sectores = (df_emp_mes.groupby('Sector_norm')['MarketCap'].sum() / total_mc * 100).to_dict()

nuevos_datos_sec = {
    'Fecha': mes_actual,
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
nuevos_datos_sec['Total'] = round(sum(v for k, v in nuevos_datos_sec.items() if k != 'Fecha'), 2)

# 5. Leer el Excel existente (Hoja 1 = Sectores, y Hoja 'Empresas' si ya existe)
archivo_excel = "SP500_Sectores_Historico.xlsx"
excel_file = pd.ExcelFile(archivo_excel)

# Actualizar pestaña Sectores (siempre lee la primera hoja, sin importar cómo se llamara antes)
df_sec_hist = pd.read_excel(excel_file, sheet_name=0)
df_sec_hist = df_sec_hist.loc[:, ~df_sec_hist.columns.str.contains('^Unnamed')]
df_sec_hist['Fecha'] = df_sec_hist['Fecha'].astype(str).str.strip()

if mes_actual in df_sec_hist['Fecha'].values:
    for col, val in nuevos_datos_sec.items():
        df_sec_hist.loc[df_sec_hist['Fecha'] == mes_actual, col] = val
else:
    nueva_fila = pd.DataFrame([nuevos_datos_sec])[df_sec_hist.columns]
    df_sec_hist = pd.concat([df_sec_hist, nueva_fila], ignore_index=True)

# Actualizar pestaña Empresas (si ya existía de meses anteriores, combina; si no, la crea)
if 'Empresas' in excel_file.sheet_names:
    df_emp_hist = pd.read_excel(excel_file, sheet_name='Empresas')
    df_emp_hist['Fecha'] = df_emp_hist['Fecha'].astype(str).str.strip()
    df_emp_hist = df_emp_hist[df_emp_hist['Fecha'] != mes_actual]
    df_emp_hist = pd.concat([df_emp_hist, df_emp_final_mes], ignore_index=True)
else:
    df_emp_hist = df_emp_final_mes

# 6. Guardar ambas pestañas dentro del MISMO archivo Excel
with pd.ExcelWriter(archivo_excel, engine='openpyxl') as writer:
    df_sec_hist.to_excel(writer, sheet_name='Sectores', index=False)
    df_emp_hist.to_excel(writer, sheet_name='Empresas', index=False)

print(f"Actualizado {mes_actual}: Sectores OK | {len(df_emp_final_mes)} empresas guardadas en la pestaña 'Empresas'.")
