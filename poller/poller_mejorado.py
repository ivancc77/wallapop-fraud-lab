import requests
import json
import os
import time
from datetime import datetime, timezone
from collections import Counter
import statistics

# --- CONFIGURACIÓN ---
SEARCH_KEYWORDS = "iphone"
ARCHIVO_MAESTRO = "wallapop_master.json"  # Nombre fijo del archivo
UMBRAL_RIESGO = 40

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

def obtener_ids_existentes(ruta_archivo):
    """Lee el archivo maestro y devuelve un set con los IDs ya guardados."""
    ids = set()
    if not os.path.exists(ruta_archivo):
        return ids
    
    print(f"[*] Leyendo base de datos existente en {ruta_archivo}...")
    try:
        with open(ruta_archivo, "r", encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if not linea: continue
                try:
                    doc = json.loads(linea)
                    if "id" in doc:
                        ids.add(doc["id"])
                except:
                    continue
    except Exception as e:
        print(f"[!] Error leyendo archivo maestro: {e}")
    
    print(f"[*] {len(ids)} anuncios ya existentes en la base de datos.")
    return ids

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
            
    print(f"[*] Total descargado de la API: {len(all_items)} items.")
    return all_items

def guardar_datos_incrementales(items):
    # Definir ruta (en carpeta ingestion si existe, si no, local)
    if os.path.exists("../ingestion"):
        ruta_completa = os.path.join("..", "ingestion", ARCHIVO_MAESTRO)
    else:
        ruta_completa = ARCHIVO_MAESTRO

    # 1. Cargar IDs que ya tenemos para no duplicar
    ids_existentes = obtener_ids_existentes(ruta_completa)

    # 2. Calcular estadísticas del lote actual
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
    
    nuevos_guardados = 0
    omitidos_por_riesgo = 0

    # 3. Abrir en modo 'a' (append) para añadir al final sin borrar lo anterior
    print(f"[*] Escribiendo nuevos datos en {ruta_completa}...")
    with open(ruta_completa, "a", encoding="utf-8") as f:
        for item in items:
            item_id = item.get("id")
            
            # FILTRO DE DUPLICADOS
            if item_id in ids_existentes:
                continue

            risk_score, risk_factors = calcular_riesgo(item, stats_lote)

            # FILTRO 2: RIESGO BAJO 
            if risk_score < UMBRAL_RIESGO:
                omitidos_por_riesgo += 1
                continue # Saltamos este item y no lo escribimos
            
            ts_millis = item.get("created_at")
            if ts_millis:
                fecha_publicacion = datetime.fromtimestamp(ts_millis / 1000.0, timezone.utc).isoformat()
            else:
                fecha_publicacion = datetime.now(timezone.utc).isoformat()
            
            # Intentar obtener URL de imagen (si existe)
            imagenes = item.get("images", [])
            img_url = imagenes[0].get("urls", {}).get("medium") if imagenes else None

            doc = {
                "id": item_id,
                "title": item.get("title"),
                "description": item.get("description"),
                "price": item.get("price", {}).get("amount"),
                "currency": item.get("price", {}).get("currency"),
                "category_id": item.get("category_id"),
                "user_id": item.get("user_id"),
                "image_url": img_url,  # Guardamos la URL para el visor
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
            ids_existentes.add(item_id) # Lo añadimos al set en memoria por si sale repetido en el mismo lote
            nuevos_guardados += 1

    print(f"[*] Proceso finalizado. Se han añadido {nuevos_guardados} anuncios sospechosos.")
    print(f"    - Omitidos por riesgo bajo (<{UMBRAL_RIESGO}): {omitidos_por_riesgo}")

if __name__ == "__main__":
    items = buscar_items_paginados()
    guardar_datos_incrementales(items)