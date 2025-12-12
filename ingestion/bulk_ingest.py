import json
import requests
import glob
import os
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURACIÓN ---
ES_URL = "https://192.168.153.3:9200" 
INDEX_NAME = "wallapop-items"
AUTH = ('elastic', 'mlJZP3AuDE0pr4q1Rwq8')
ARCHIVO_MAESTRO = "wallapop_master.json"

def bulk_ingest():
    # Buscar el archivo maestro
    if os.path.exists(ARCHIVO_MAESTRO):
        ruta_archivo = ARCHIVO_MAESTRO
    elif os.path.exists(f"../ingestion/{ARCHIVO_MAESTRO}"):
        ruta_archivo = f"../ingestion/{ARCHIVO_MAESTRO}"
    elif os.path.exists(f"../poller/{ARCHIVO_MAESTRO}"):
        # Por si acaso se guarda en poller
        ruta_archivo = f"../poller/{ARCHIVO_MAESTRO}"
    else:
        print(f"[!] No encuentro {ARCHIVO_MAESTRO}. Ejecuta el poller primero.")
        return

    print(f"[*] Leyendo base de datos: {ruta_archivo}")

    bulk_data = ""
    count = 0

    with open(ruta_archivo, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            try:
                doc = json.loads(line)
                meta = {"index": {"_index": INDEX_NAME}}
                if "id" in doc: meta["index"]["_id"] = doc["id"]
                
                bulk_data += json.dumps(meta) + "\n"
                bulk_data += json.dumps(doc) + "\n"
                count += 1
            except: continue

    if count == 0: 
        print("[!] Archivo vacío.")
        return

    print(f"[*] Sincronizando {count} documentos con Elastic...")

    try:
        response = requests.post(
            f"{ES_URL}/_bulk",
            headers={"Content-Type": "application/x-ndjson"},
            data=bulk_data.encode('utf-8'),
            auth=AUTH,
            timeout=60, # Aumentamos tiempo por si el archivo es grande
            verify=False 
        )

        if response.status_code == 200:
            print(f"[*] ¡ÉXITO! Base de datos sincronizada.")
        else:
            print(f"[!] Error HTTP {response.status_code}: {response.text}")

    except Exception as e:
        print(f"[!] Error de conexión: {e}")

if __name__ == "__main__":
    bulk_ingest()