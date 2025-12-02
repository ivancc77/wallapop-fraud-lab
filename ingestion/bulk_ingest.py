import json
import requests
import glob
import os

# --- CONFIGURACIÓN ---
# CAMBIA ESTO SI TU ELASTIC ESTÁ EN OTRA IP (Ej. la de la VM de la práctica)
ES_URL = "https://192.168.153.3:9200"
INDEX_NAME = "wallapop-items"

# Si tu Elastic tiene usuario/pass (como en la práctica SNMP), ponlos aquí:
AUTH = ('elastic', 'mlJZP3AuDE0pr4q1Rwq8') 
#AUTH = None 

# 3. Desactivamos la verificación SSL porque el certificado es autofirmado (típico en labs)
VERIFY_SSL = False

def bulk_ingest():
    # 1. Buscar el archivo JSON más reciente generado por el poller
    # Buscamos en la misma carpeta donde está este script
    list_of_files = glob.glob('wallapop_*.json') 
    
    if not list_of_files:
        print("[!] No encuentro archivos .json en la carpeta 'ingestion'.")
        print("    ¿Has ejecutado el poller.py? ¿Se guardó el archivo aquí?")
        return

    latest_file = max(list_of_files, key=os.path.getctime)
    print(f"[*] Archivo seleccionado para subir: {latest_file}")

    bulk_data = ""
    count = 0

    # 2. Leer el archivo línea a línea (formato NDJSON)
    with open(latest_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            
            try:
                doc = json.loads(line)
                
                # Preparamos el formato BULK que pide Elastic:
                # Línea 1: Metadatos (índice y ID)
                meta = {"index": {"_index": INDEX_NAME}}
                if "id" in doc:
                    meta["index"]["_id"] = doc["id"] # Usamos el ID de Wallapop
                
                # Línea 2: El dato en sí
                bulk_data += json.dumps(meta) + "\n"
                bulk_data += json.dumps(doc) + "\n"
                count += 1
                
            except json.JSONDecodeError:
                continue

    if count == 0:
        print("[!] El archivo parece vacío.")
        return

    print(f"[*] Enviando {count} documentos a {ES_URL}...")

    # 3. Enviar petición POST a Elastic
    try:
        response = requests.post(
            f"{ES_URL}/_bulk",
            headers={"Content-Type": "application/x-ndjson"},
            data=bulk_data.encode('utf-8'),
            auth=AUTH,
            timeout=30
        )

        if response.status_code == 200:
            print(f"[*] ¡ÉXITO! Datos ingestados correctamente.")
            print("    Ahora ve a Kibana -> Stack Management -> Data Views y crea uno para 'wallapop-items*'")
        else:
            print(f"[!] Error {response.status_code}: {response.text}")

    except Exception as e:
        print(f"[!] Error de conexión: {e}")
        print("    ¿Está Elasticsearch encendido y la URL es correcta?")

if __name__ == "__main__":
    bulk_ingest()