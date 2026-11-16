import os
import pandas as pd
import requests
from datetime import datetime, timedelta

# 1. Consultar la API de CNN con fecha explícita (1 año atrás) y encabezados de navegador
fecha_inicio = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
url = f"https://production.dataviz.cnn.io/index/fearandgreed/graphdata/{fecha_inicio}"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.cnn.com",
    "Referer": "https://www.cnn.com/markets/fear-and-greed",
}

resp = requests.get(url, headers=headers, timeout=30)
print("Código de respuesta CNN:", resp.status_code)
resp.raise_for_status()
data = resp.json()

# 2. Extraer el dato actual
actual = data["fear_and_greed"]
fecha_hoy = actual["timestamp"][:10]
score_hoy = round(float(actual["score"]), 2)
rating_hoy = actual["rating"].title()

# 3. Extraer la serie histórica diaria
historico_raw = data["fear_and_greed_historical"]["data"]
df_nuevo = pd.DataFrame(historico_raw)
df_nuevo["Fecha"] = pd.to_datetime(df_nuevo["x"], unit="ms").dt.strftime("%Y-%m-%d")
df_nuevo["Puntaje"] = df_nuevo["y"].astype(float).round(2)
df_nuevo["Sentimiento"] = df_nuevo["rating"].str.title()

df_nuevo = df_nuevo[["Fecha", "Puntaje", "Sentimiento"]].drop_duplicates(
    subset=["Fecha"], keep="last"
)

fila_hoy = pd.DataFrame([{"Fecha": fecha_hoy, "Puntaje": score_hoy, "Sentimiento": rating_hoy}])
df_nuevo = pd.concat([df_nuevo, fila_hoy]).drop_duplicates(subset=["Fecha"], keep="last")

# 4. Combinar con el Excel existente si ya fue creado
archivo_excel = "CNN_Fear_and_Greed_Historico.xlsx"

if os.path.exists(archivo_excel):
    df_existente = pd.read_excel(archivo_excel)
    df_existente["Fecha"] = df_existente["Fecha"].astype(str).str.strip()
    df_final = pd.concat([df_existente, df_nuevo]).drop_duplicates(
        subset=["Fecha"], keep="last"
    )
else:
    df_final = df_nuevo

df_final = df_final.sort_values("Fecha").reset_index(drop=True)

# 5. Guardar el Excel actualizado
df_final.to_excel(archivo_excel, index=False)
print(f"Guardado con éxito ({fecha_hoy}): {score_hoy} - {rating_hoy}")
