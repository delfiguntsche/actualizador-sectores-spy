import os
import pandas as pd
import requests

# 1. Consultar la API oficial de CNN Fear & Greed
url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.cnn.com/markets/fear-and-greed",
}

resp = requests.get(url, headers=headers, timeout=30)
resp.raise_for_status()
data = resp.json()

# 2. Extraer el dato actual
actual = data["fear_and_greed"]
fecha_hoy = actual["timestamp"][:10]
score_hoy = round(float(actual["score"]), 2)
rating_hoy = actual["rating"].title()

# 3. Extraer la serie histórica diaria disponible (~1 año hacia atrás)
historico_raw = data["fear_and_greed_historical"]["data"]
df_nuevo = pd.DataFrame(historico_raw)
df_nuevo["Fecha"] = pd.to_datetime(df_nuevo["x"], unit="ms").dt.strftime("%Y-%m-%d")
df_nuevo["Puntaje"] = df_nuevo["y"].astype(float).round(2)
df_nuevo["Sentimiento"] = df_nuevo["rating"].str.title()

df_nuevo = df_nuevo[["Fecha", "Puntaje", "Sentimiento"]].drop_duplicates(
    subset=["Fecha"], keep="last"
)

# Asegurar que el registro de hoy esté actualizado
fila_hoy = pd.DataFrame([{"Fecha": fecha_hoy, "Puntaje": score_hoy, "Sentimiento": rating_hoy}])
df_nuevo = pd.concat([df_nuevo, fila_hoy]).drop_duplicates(subset=["Fecha"], keep="last")

# 4. Combinar con el Excel existente en el repositorio para no perder fechas antiguas
archivo_excel = "CNN_Fear_and_Greed_Historico.xlsx"

if os.path.exists(archivo_excel):
    df_existente = pd.read_excel(archivo_excel)
    df_existente["Fecha"] = df_existente["Fecha"].astype(str).str.strip()
    df_final = pd.concat([df_existente, df_nuevo]).drop_duplicates(
        subset=["Fecha"], keep="last"
    )
    print("Histórico existente actualizado con nuevos registros.")
else:
    df_final = df_nuevo
    print("Archivo inicial creado con el histórico disponible en CNN.")

df_final = df_final.sort_values("Fecha").reset_index(drop=True)

# 5. Guardar en el repositorio
df_final.to_excel(archivo_excel, index=False)
print(f"Último registro guardado ({fecha_hoy}): {score_hoy} - {rating_hoy}")
