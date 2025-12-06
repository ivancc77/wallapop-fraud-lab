import requests
import json
import os
import time
from datetime import datetime, timezone
from collections import Counter
import statistics
import re

# --- CONFIGURACIÓN ---
SEARCH_KEYWORDS = "iphone"
ARCHIVO_MAESTRO = "wallapop_master.json"
UMBRAL_RIESGO_MINIMO = 40 

# --- 1. DICCIONARIO DE PRECIOS MÍNIMOS DE REFERENCIA ---
# (Precios orientativos de segunda mano. Si baja mucho de aquí, es estafa).
# IMPORTANTE: Ordenar de más específico a menos (15 Pro Max antes que 15).
PRECIOS_REFERENCIA = {
    "16 pro max": 1100, "16 pro": 950, "iphone 16": 800,
    "15 pro max": 850, "15 pro": 750, "15 plus": 650, "iphone 15": 550,
    "14 pro max": 700, "14 pro": 600, "14 plus": 500, "iphone 14": 450,
    "13 pro max": 550, "13 pro": 480, "iphone 13": 350,
    "12 pro max": 400, "12 pro": 350, "iphone 12": 250,
    "11 pro max": 300, "11 pro": 280, "iphone 11": 200,
    "iphone x": 150, "iphone xr": 150, "iphone xs": 160
}

# --- 2. FILTROS Y KEYWORDS ---
PALABRAS_EXCLUIDAS = [
    "funda", "cargador", "case", "cristal", "tempered", "protector", "cable",
    "auriculares", "adaptador", "caja vacía", "box only", "icloud", "bloqueo"
]

KEYWORDS_CRITICAS = [
    "bizum", "transferencia", "ingreso", "envío incluido", "solo envío",
    "encontrado", "réplica", "clon", "imitación", "1:1", "demo",
    "whatsapp", "telegram", "6", "no negociable" # El 6 para detectar tlf
]

KEYWORDS_SOSPECHOSAS = [
    "urgente", "viaje", "regalo", "indeseado", "sin factura",
    "leer bien", "no mareantes", "piezas", "sin face id", "tara"
]

NUM_PAGINAS = 5 
URL_API = "https://api.wallapop.com/api/v3/search"
HEADERS = {"Host": "api.wallapop.com", "X-DeviceOS": "0", "User-Agent": "Mozilla/5.0"}

def obtener_ids_existentes(ruta_archivo):
    ids = set()
    if not os.path.exists(ruta_archivo): return ids
    try:
        with open(ruta_archivo, "r", encoding="utf-8") as f:
            for linea in f:
                if linea.strip():
                    try:
                        doc = json.loads(linea)
                        if "id" in doc: ids.add(doc["id"])
                    except: continue
    except: pass
    return ids

def calcular_riesgo_inteligente(item, stats_lote):
    score = 0
    razones = []
    
    precio = item.get("price", {}).get("amount", 0)
    titulo = (item.get("title") or "").lower()
    descripcion = (item.get("description") or "").lower()
    texto_completo = titulo + " " + descripcion
    user_id = item.get("user_id")

    # ==============================================================================
    # 1. ANÁLISIS DE PRECIO SEGMENTADO (La clave de la mejora)
    # ==============================================================================
    modelo_detectado = None
    precio_ref = 0

    # Buscamos qué modelo es en el título
    for modelo, precio_min in PRECIOS_REFERENCIA.items():
        if modelo in titulo:
            modelo_detectado = modelo
            precio_ref = precio_min
            break # Paramos en la primera coincidencia (la más específica)

    if modelo_detectado:
        # Tenemos referencia específica (ej: iPhone 15 Pro)
        if precio < (precio_ref * 0.4): # Menos del 40% del valor de ref
            score += 95
            razones.append(f"PRECIO IMPOSIBLE para {modelo_detectado} ({precio}€ vs Ref {precio_ref}€)")
        elif precio < (precio_ref * 0.6): # Menos del 60%
            score += 60
            razones.append(f"Precio muy bajo para {modelo_detectado}")
    else:
        # NO detectamos modelo exacto -> Usamos la media del lote (Plan B)
        precio_medio = stats_lote['precio_medio']
        if precio_medio > 0 and precio < (precio_medio * 0.4):
            score += 40
            razones.append(f"Precio bajo vs Media general ({precio}€ vs {precio_medio:.0f}€)")

    # ==============================================================================
    # 2. KEYWORDS Y PATRONES
    # ==============================================================================
    
    # Detección de teléfonos en texto (6xx xxx xxx)
    if re.search(r'\b[67]\d{2}[\s.-]?\d{3}[\s.-]?\d{3}\b', texto_completo):
        score += 50
        razones.append("Teléfono camuflado en descripción")

    # Keywords Críticas
    criticas = [kw for kw in KEYWORDS_CRITICAS if kw in texto_completo]
    if criticas:
        score += 50
        razones.append(f"ALERTA: {', '.join(set(criticas))}")

    # Keywords Sospechosas
    sospechosas = [kw for kw in KEYWORDS_SOSPECHOSAS if kw in texto_completo]
    if sospechosas:
        score += 15 * len(sospechosas)
        razones.append(f"Sospechoso: {', '.join(set(sospechosas))}")

    # Vendedor Masivo
    num_anuncios = stats_lote['conteo_vendedores'].get(user_id, 0)
    if num_anuncios >= 3:
        score += 25
        razones.append(f"Vendedor masivo ({num_anuncios} items)")

    # Descripción Corta
    if len(descripcion) < 15:
        score += 10
        razones.append("Descripción insuficiente")

    return min(score, 100), razones

def buscar_items_paginados():
    all_items = []
    print(f"[*] Buscando '{SEARCH_KEYWORDS}'...")
    
    for i in range(NUM_PAGINAS):
        params = {
            "keywords": SEARCH_KEYWORDS,
            "order_by": "newest",
            "time_filter": "today", 
            "latitude": "40.4168", "longitude": "-3.7038",
            "source": "search_box",
            "start": i * 40
        }
        try:
            r = requests.get(URL_API, headers=HEADERS, params=params, timeout=10)
            items = r.json().get("data", {}).get("section", {}).get("payload", {}).get("items", [])
            if not items: break
            all_items.extend(items)
            time.sleep(0.5) 
        except: break
    return all_items

def guardar_datos_incrementales(items):
    if os.path.exists("../ingestion"):
        ruta_completa = os.path.join("..", "ingestion", ARCHIVO_MAESTRO)
    elif os.path.exists("ingestion"):
        ruta_completa = os.path.join("ingestion", ARCHIVO_MAESTRO)
    else:
        ruta_completa = ARCHIVO_MAESTRO

    ids_existentes = obtener_ids_existentes(ruta_completa)

    # Calculamos stats generales por si acaso
    if items:
        precios = [i.get("price", {}).get("amount", 0) for i in items if i.get("price", {}).get("amount", 0) > 50]
        precio_medio_lote = statistics.median(precios) if precios else 400
        vendedores = [i.get("user_id") for i in items]
        conteo_vendedores = Counter(vendedores)
    else:
        precio_medio_lote = 400
        conteo_vendedores = {}

    stats_lote = {"precio_medio": precio_medio_lote, "conteo_vendedores": conteo_vendedores}
    
    nuevos = 0
    omitidos = 0

    print(f"[*] Procesando {len(items)} items...")
    
    with open(ruta_completa, "a", encoding="utf-8") as f:
        for item in items:
            titulo = item.get("title", "").lower()
            
            # Filtros básicos
            if any(p in titulo for p in PALABRAS_EXCLUIDAS): continue
            if SEARCH_KEYWORDS.lower() not in titulo: continue 
            if item.get("id") in ids_existentes: continue

            # --- RIESGO INTELIGENTE ---
            risk_score, risk_factors = calcular_riesgo_inteligente(item, stats_lote)

            if risk_score < UMBRAL_RIESGO_MINIMO:
                omitidos += 1
                continue 
            
            # Preparar documento
            ts_millis = item.get("created_at")
            fecha_pub = datetime.fromtimestamp(ts_millis/1000.0, timezone.utc).isoformat() if ts_millis else datetime.now(timezone.utc).isoformat()
            
            imagenes = item.get("images", [])
            img_url = imagenes[0].get("urls", {}).get("medium") if imagenes else None

            all_kw = KEYWORDS_CRITICAS + KEYWORDS_SOSPECHOSAS
            found_kw = [kw for kw in all_kw if kw in (titulo + " " + (item.get("description") or "").lower())]

            doc = {
                "id": item.get("id"),
                "title": item.get("title"),
                "description": item.get("description"),
                "price": item.get("price", {}).get("amount"),
                "currency": item.get("price", {}).get("currency"),
                "category_id": item.get("category_id"),
                "user_id": item.get("user_id"),
                "image_url": img_url,
                "location": {
                    "geo": { "lat": item.get("location", {}).get("latitude"), "lon": item.get("location", {}).get("longitude") },
                    "city": item.get("location", {}).get("city")
                },
                "timestamps": {
                    "crawled_at": datetime.now(timezone.utc).isoformat(),
                    "created_at": fecha_pub
                },
                "enrichment": {
                    "risk_score": risk_score,
                    "risk_factors": risk_factors,
                    "suspicious_keywords": found_kw
                }
            }
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")
            ids_existentes.add(item.get("id"))
            nuevos += 1

    print(f"[*] Guardados: {nuevos} | Omitidos: {omitidos}")

if __name__ == "__main__":
    items = buscar_items_paginados()
    guardar_datos_incrementales(items)