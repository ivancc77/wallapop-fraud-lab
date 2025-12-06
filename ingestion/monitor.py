import time
import os
import datetime

INTERVALO = 1800 

print(f"[*] --- MONITOR DE ESTAFAS WALLAPOP ---")
print(f"[*] Ciclo: {INTERVALO}s | Archivo: wallapop_master.json")
print("[*] Ctrl+C para salir.\n")

try:
    while True:
        ahora = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"┌── [ {ahora} ] Iniciando ciclo...")
        
        # 1. EJECUTAR POLLER
        # Usa python3 para Linux
        print("│ >> 1. Buscando nuevos anuncios sospechosos...")
        if os.system("python3 ../poller/poller.py") != 0:
            print("│ [!] Alerta: El poller falló o no encontró el archivo.")
        
        else:
            # 2. EJECUTAR INGESTIÓN
            print("│ >> 2. Sincronizando Elastic...")
            os.system("python3 bulk_ingest.py")
            
        print(f"└── Ciclo finalizado. Esperando {INTERVALO}s...\n")
        time.sleep(INTERVALO)

except KeyboardInterrupt:
    print("\n[!] Monitor detenido.")