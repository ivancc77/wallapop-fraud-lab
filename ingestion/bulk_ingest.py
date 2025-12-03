import json
import requests
import glob
import os

# --- CONFIGURACIÓN ---
# Apuntamos a la máquina remota donde está Elastic
ES_URL = "http://192.168.153.3:9200"
INDEX_NAME = "wallapop-items"

# Usuario y contraseña que me facilitaste
AUTH = ('elastic', 'mlJZP3AuDE0pr4q1Rwq8')

def bulk_ingest():
    # Buscar el archivo JSON más reciente en la carpeta actual
    list_of_files = glob.glob('wallapop_*.json') 
    
    if not list_of_files:
        print("[!] No encuentro archivos wallapop_*.json en esta carpeta.")
        print("    Primero ejecuta: python3 poller.py")
        return

    latest_file = max(list_of_files, key=os.path.getctime)
    print(f"[*] Archivo seleccionado: {latest_file}")

    bulk_data = ""
    count = 0

    # Leer el archivo línea a línea (formato NDJSON)
    with open(latest_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            
            try:
                doc = json.loads(line)
                
                # [cite_start]Preparamos el formato BULK [cite: 994]
                # Línea 1: Metadatos (índice y ID)
                meta = {"index": {"_index": INDEX_NAME}}
                if "id" in doc:
                    meta["index"]["_id"] = doc["id"]
                
                # Línea 2: El documento
                bulk_data += json.dumps(meta) + "\n"
                bulk_data += json.dumps(doc) + "\n"
                count += 1
                
            except json.JSONDecodeError:
                continue

    if count == 0:
        print("[!] El archivo parece vacío.")
        return

    print(f"[*] Intentando enviar {count} documentos a {ES_URL}...")

    # Enviar petición POST a Elastic
    try:
        response = requests.post(
            f"{ES_URL}/_bulk",
            headers={"Content-Type": "application/x-ndjson"},
            data=bulk_data.encode('utf-8'),
            auth=AUTH,
            timeout=30
        )

        if response.status_code == 200:
            resp_json = response.json()
            if resp_json.get("errors"):
                print("[!] Ojo, hubo algunos errores en la inserción (revisa los logs).")
                # Imprimir el primer error para depurar si hace falta
                print(resp_json['items'][0]) 
            else:
                print(f"[*] ¡ÉXITO! {count} documentos ingestados correctamente.")
        else:
            print(f"[!] Error HTTP {response.status_code}: {response.text}")

    except Exception as e:
        print(f"[!] Error de conexión: {e}")
        print("    Asegúrate de que la VM 192.168.153.3 está encendida y Elastic corriendo.")

if __name__ == "__main__":
    bulk_ingest()