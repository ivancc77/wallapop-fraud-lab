import requests
import json
import os
from datetime import datetime

# --- CONFIGURACIÓN ---
SEARCH_KEYWORDS = "iphone" 
PRECIO_MERCADO = 400.0 
PALABRAS_SOSPECHOSAS = ["urgente", "bloqueado", "icloud", "sin factura", "envío gratis", "solo whatsapp", "indiviso"]

URL_API = "https://api.wallapop.com/api/v3/search"
HEADERS = {
    "Host": "api.wallapop.com",
    "X-DeviceOS": "0",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*"
}

def calcular_riesgo(item):
    score = 0
    razones = []
    precio = item.get("price", {}).get("amount", 0)
    titulo = (item.get("title") or "").lower()
    descripcion = (item.get("description") or "").lower()

    if 0 < precio < (PRECIO_MERCADO * 0.5):
        score += 40
        razones.append("Precio anómalamente bajo")

    encontradas = [kw for kw in PALABRAS_SOSPECHOSAS if kw in titulo or kw in descripcion]
    if encontradas:
        score += 20 * len(encontradas)
        razones.append(f"Keywords sospechosas: {', '.join(encontradas)}")

    if len(descripcion) < 15:
        score += 10
        razones.append("Descripción muy corta")

    return min(score, 100), razones

def buscar_items_hoy():
    params = {
        "keywords": SEARCH_KEYWORDS,
        "order_by": "newest",
        "time_filter": "today", 
        "latitude": "40.4168",
        "longitude": "-3.7038",
        "source": "search_box"
    }

    print(f"[*] Buscando anuncios recientes de '{SEARCH_KEYWORDS}'...")
    try:
        response = requests.get(URL_API, headers=HEADERS, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("data", {}).get("section", {}).get("payload", {}).get("items", [])
    except Exception as e:
        print(f"[!] Error: {e}")
        return []

def guardar_datos(items):
    if not items:
        print("[!] No se encontraron items.")
        return

    fecha_hora = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_fichero = f"wallapop_smartphones_{fecha_hora}.json"
    
    # Guardar en carpeta hermana 'ingestion' si existe
    if os.path.exists("../ingestion"):
        ruta_completa = os.path.join("..", "ingestion", nombre_fichero)
    else:
        ruta_completa = nombre_fichero

    print(f"[*] Guardando {len(items)} items en {ruta_completa}...")
    
    with open(ruta_completa, "w", encoding="utf-8") as f:
        for item in items:
            risk_score, risk_factors = calcular_riesgo(item)
            
            # --- CORRECCIÓN DE FECHAS ---
            # [cite_start]Wallapop envía 'created_at' como un número largo (milisegundos) [cite: 221]
            ts_millis = item.get("created_at")
            
            if ts_millis:
                # Convertimos milisegundos a fecha ISO legible
                fecha_publicacion = datetime.fromtimestamp(ts_millis / 1000.0).isoformat()
            else:
                # Si falla, usamos la actual como fallback
                fecha_publicacion = datetime.now().isoformat()

            doc = {
                "id": item.get("id"),
                "title": item.get("title"),
                "description": item.get("description"),
                "price": item.get("price", {}).get("amount"),
                "currency": item.get("price", {}).get("currency"),
                "category_id": item.get("category_id"),
                "user_id": item.get("user_id"),
                "location": {
                    "geo": {
                        "lat": item.get("location", {}).get("latitude"),
                        "lon": item.get("location", {}).get("longitude")
                    },
                    "city": item.get("location", {}).get("city")
                },
                "timestamps": {
                    "crawled_at": datetime.now().isoformat(), # Cuándo pasaste el script
                    "created_at": fecha_publicacion           # CUÁNDO SE PUBLICÓ EL ANUNCIO
                },
                "enrichment": {
                    "risk_score": risk_score,
                    "risk_factors": risk_factors,
                    "suspicious_keywords": [kw for kw in PALABRAS_SOSPECHOSAS if kw in (item.get("description") or "")]
                }
            }
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    items = buscar_items_hoy()
    guardar_datos(items)