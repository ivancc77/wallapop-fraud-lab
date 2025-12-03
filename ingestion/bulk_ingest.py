import json
import requests
import glob
import os
import urllib3 # 1. Importar esto

# 2. Desactivar las advertencias de seguridad para que no molesten en la terminal
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURACIÓN ---
ES_URL = "https://192.168.153.3:9200" # HTTPS es correcto
INDEX_NAME = "wallapop-items"
AUTH = ('elastic', 'mlJZP3AuDE0pr4q1Rwq8')

def bulk_ingest():
    # Buscar el JSON (en la carpeta actual o en ../poller)
    list_of_files = glob.glob('wallapop_*.json') 
    if not list_of_files:
        list_of_files = glob.glob('../poller/wallapop_*.json')
        if not list_of_files:
             print("[!] No encuentro archivos wallapop_*.json.")
             return

    latest_file = max(list_of_files, key=os.path.getctime)
    print(f"[*] Archivo seleccionado: {latest_file}")

    bulk_data = ""
    count = 0

    with open(latest_file, 'r', encoding='utf-8') as f:
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

    if count == 0: return

    print(f"[*] Intentando enviar {count} documentos a {ES_URL}...")

    try:
        response = requests.post(
            f"{ES_URL}/_bulk",
            headers={"Content-Type": "application/x-ndjson"},
            data=bulk_data.encode('utf-8'),
            auth=AUTH,
            timeout=30,
            verify=False  # <--- 3. ESTA ES LA CLAVE PARA ARREGLAR TU ERROR
        )

        if response.status_code == 200:
            print(f"[*] ¡ÉXITO! {count} documentos ingestados correctamente.")
        else:
            print(f"[!] Error HTTP {response.status_code}: {response.text}")

    except Exception as e:
        print(f"[!] Error de conexión: {e}")

if __name__ == "__main__":
    bulk_ingest()