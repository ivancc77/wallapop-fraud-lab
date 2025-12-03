import requests
import json
import os
import time
from datetime import datetime, timezone  # <--- IMPORTANTE: Importamos timezone
from collections import Counter
import statistics

# --- CONFIGURACIÓN ---
SEARCH_KEYWORDS = "iphone" 
PALABRAS_SOSPECHOSAS = [
    "urgente", "bloqueado", "icloud", "sin factura", "envío gratis", 
    "solo whatsapp", "indiviso", "réplica", "clon", "imitación", 
    "sin face id", "tara", "no enciende", "piezas"
]

NUM_PAGINAS = 5 

URL_API = "https://api.wallapop.com/api/v3/search"
HEADERS = {
    "Host": "api.wallapop.com",
    "X-DeviceOS": "0",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*"
}

def calcular_riesgo(item, stats_lote):
    score = 0
    razones = []
    
    precio = item.get("price", {}).get("amount", 0)
    titulo = (item.get("title") or "").lower()
    descripcion = (item.get("description") or "").lower()
    user_id = item.get("user_id")

    precio_medio = stats_lote['precio_medio']
    if precio_medio > 0 and 10 < precio < (precio_medio * 0.5):
        score += 50
        razones.append(f"Precio muy bajo (Media: {precio_medio:.0f}€)")

    num_anuncios = stats_lote['conteo_vendedores'].get(user_id, 0)
    if num_anuncios >= 4:
        score += 30
        razones.append(f"Vendedor masivo ({num_anuncios} anuncios)")

    encontradas = [kw for kw in PALABRAS_SOSPECHOSAS if kw in titulo or kw in descripcion]
    if encontradas:
        score += 20 * len(encontradas)
        razones.append(f"Keywords sospechosas: {', '.join(encontradas)}")

    if len(descripcion) < 10:
        score += 10
        razones.append("Descripción muy corta")

    return min(score, 100), razones

def buscar_items_paginados():
    all_items = []
    print(f"[*] Descargando anuncios de '{SEARCH_KEYWORDS}'...")
    
    for i in range(NUM_PAGINAS):
        params = {
            "keywords": SEARCH_KEYWORDS,
            "order_by": "newest",
            "time_filter": "today", 
            "latitude": "40.4168",
            "longitude": "-3.7038",
            "source": "search_box",
            "start": i * 40
        }
        try:
            response = requests.get(URL_API, headers=HEADERS, params=params, timeout=10)
            response.raise_for_status()
            items = response.json().get("data", {}).get("section", {}).get("payload", {}).get("items", [])
            if not items: break
            all_items.extend(items)
            time.sleep(0.5) 
        except Exception as e:
            print(f"    [!] Error paginando: {e}")
            break
            
    print(f"[*] Total descargado: {len(all_items)} items.")
    return all_items

def guardar_datos(items):
    if items:
        precios = [i.get("price", {}).get("amount", 0) for i in items if i.get("price", {}).get("amount", 0) > 10]
        precio_medio_lote = statistics.median(precios) if precios else 400
        vendedores = [i.get("user_id") for i in items]
        conteo_vendedores = Counter(vendedores)
    else:
        precio_medio_lote = 400
        conteo_vendedores = {}

    stats_lote = {
        "precio_medio": precio_medio_lote,
        "conteo_vendedores": conteo_vendedores
    }
    
    fecha_hora = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_fichero = f"wallapop_smartphones_{fecha_hora}.json"
    
    if os.path.exists("../ingestion"):
        ruta_completa = os.path.join("..", "ingestion", nombre_fichero)
    else:
        ruta_completa = nombre_fichero

    print(f"[*] Guardando en {ruta_completa}")
    
    with open(ruta_completa, "w", encoding="utf-8") as f:
        # 1. Items reales
        for item in items:
            risk_score, risk_factors = calcular_riesgo(item, stats_lote)
            
            ts_millis = item.get("created_at")
            if ts_millis:
                # CAMBIO: Añadimos timezone.utc
                fecha_publicacion = datetime.fromtimestamp(ts_millis / 1000.0, timezone.utc).isoformat()
            else:
                # CAMBIO: Añadimos timezone.utc
                fecha_publicacion = datetime.now(timezone.utc).isoformat()

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
                    "crawled_at": datetime.now(timezone.utc).isoformat(),
                    "created_at": fecha_publicacion
                },
                "enrichment": {
                    "risk_score": risk_score,
                    "risk_factors": risk_factors,
                    "suspicious_keywords": [kw for kw in PALABRAS_SOSPECHOSAS if kw in (item.get("description") or "")]
                }
            }
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")

        # 2. Item Fantasma (Monitor Check)
        ahora_utc = datetime.now(timezone.utc) # CAMBIO: UTC explícito
        fake_id = f"TEST_AUTO_{ahora_utc.strftime('%H%M%S')}"
        
        doc_fake = {
            "id": fake_id,
            "title": ">>> ITEM DE CONTROL <<<",
            "description": "Item generado para validar latencia y timezone.",
            "price": 66.6, 
            "currency": "EUR",
            "category_id": "0000",
            "user_id": "bot_monitor",
            "location": { "geo": { "lat": 40.4168, "lon": -3.7038 }, "city": "Check" },
            "timestamps": {
                "crawled_at": ahora_utc.isoformat(),
                "created_at": ahora_utc.isoformat() # Se pintará en la hora EXACTA actual
            },
            "enrichment": {
                "risk_score": 100, 
                "risk_factors": ["Test Item"],
                "suspicious_keywords": ["test"]
            }
        }
        f.write(json.dumps(doc_fake, ensure_ascii=False) + "\n")
        print(f"    [+] Item fantasma inyectado: {fake_id} (Hora UTC: {ahora_utc})")

if __name__ == "__main__":
    items = buscar_items_paginados()
    guardar_datos(items)