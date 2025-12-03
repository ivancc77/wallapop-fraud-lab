import requests
import json
import os
from datetime import datetime

# --- 1. CONFIGURACIÓN ---
# Buscamos iPhones para asegurar datos hoy
SEARCH_KEYWORDS = "iphone" 
# Umbral de precio para detectar ofertas sospechosas
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
    """Calcula un score de riesgo del 0 al 100."""
    score = 0
    razones = []
    
    precio = item.get("price", {}).get("amount", 0)
    titulo = (item.get("title") or "").lower()
    descripcion = (item.get("description") or "").lower()

    # Regla A: Precio demasiado bajo
    if 0 < precio < (PRECIO_MERCADO * 0.5):
        score += 40
        razones.append("Precio anómalamente bajo")

    # Regla B: Palabras clave sospechosas
    encontradas = [kw for kw in PALABRAS_SOSPECHOSAS if kw in titulo or kw in descripcion]
    if encontradas:
        score += 20 * len(encontradas)
        razones.append(f"Keywords sospechosas: {', '.join(encontradas)}")

    # Regla C: Descripción muy corta
    if len(descripcion) < 15:
        score += 10
        razones.append("Descripción muy corta")

    return min(score, 100), razones

def buscar_items_hoy():
    """Descarga los anuncios publicados HOY."""
    params = {
        "keywords": SEARCH_KEYWORDS,
        "order_by": "newest",
        "time_filter": "today",  # REQUISITO DEL PDF
        "latitude": "40.4168",   # Madrid
        "longitude": "-3.7038",
        "source": "search_box"
    }

    print(f"[*] Conectando a Wallapop (Filtro: HOY, Query: '{SEARCH_KEYWORDS}')...")
    
    try:
        response = requests.get(URL_API, headers=HEADERS, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        items = data.get("data", {}).get("section", {}).get("payload", {}).get("items", [])
        
        print(f"[*] Se han descargado {len(items)} anuncios.")
        return items

    except Exception as e:
        print(f"[!] Error de conexión con Wallapop: {e}")
        return []

def guardar_datos(items):
    """Guarda los datos enriquecidos en un fichero JSON."""
    if not items:
        print("[!] No hay items para guardar.")
        return

    # Nombre de archivo: wallapop_categoria_YYYYMMDD.json
    fecha = datetime.now().strftime("%Y%m%d")
    nombre_fichero = f"wallapop_smartphones_{fecha}.json"

    print(f"[*] Procesando {len(items)} items y calculando riesgo...")
    
    with open(nombre_fichero, "w", encoding="utf-8") as f:
        for item in items:
            # 1. Calcular Riesgo
            risk_score, risk_factors = calcular_riesgo(item)
            
            # 2. Crear documento limpio para Elastic
            doc = {
                "id": item.get("id"),
                "title": item.get("title"),
                "description": item.get("description"),
                "price": item.get("price", {}).get("amount"),
                "currency": item.get("price", {}).get("currency"),
                "category_id": item.get("category_id"),
                "user_id": item.get("user_id"),
                # ESTRUCTURA CORREGIDA PARA EL MAPA:
                "location": {
                    "geo": {
                        "lat": item.get("location", {}).get("latitude"),
                        "lon": item.get("location", {}).get("longitude")
                    },
                    "city": item.get("location", {}).get("city")
                },
                "timestamps": {
                    "crawled_at": datetime.now().isoformat()
                },
                "enrichment": {
                    "risk_score": risk_score,
                    "risk_factors": risk_factors,
                    "suspicious_keywords": [kw for kw in PALABRAS_SOSPECHOSAS if kw in (item.get("description") or "")]
                }
            }
            
            # 3. Escribir una línea por objeto (NDJSON)
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")
            
    print(f"[*] ¡ÉXITO! Archivo guardado: {nombre_fichero}")

if __name__ == "__main__":
    items = buscar_items_hoy()
    guardar_datos(items)