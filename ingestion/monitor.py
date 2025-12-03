import time
import os
import datetime

# Intervalo en segundos (300s = 5 minutos)
INTERVALO = 300 

print(f"[*] --- INICIANDO MONITOR AUTOMÁTICO ---")
print(f"[*] Frecuencia: Cada {INTERVALO} segundos")
print("[*] Pulsa Ctrl+C para detenerlo en cualquier momento.\n")

try:
    while True:
        ahora = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"┌── [ {ahora} ] Iniciando nuevo ciclo...")
        
        # 1. EJECUTAR POLLER
        # Buscamos el script en la carpeta hermana '../poller/'
        print("│ >> 1. Descargando datos (ejecutando ../poller/poller.py)...")
        
        # --- CAMBIO CLAVE AQUÍ ABAJO ---
        codigo_salida = os.system("python ../poller/poller.py")
        
        if codigo_salida != 0:
            print("│ [!] Error: No se pudo ejecutar el poller. ¿La ruta es correcta?")
            print("│     Esperando al siguiente ciclo...")
        
        else:
            # 2. EJECUTAR INGESTIÓN
            # Como bulk_ingest.py está en la MISMA carpeta que este monitor, no hace falta ruta
            print("│ >> 2. Subiendo datos a Elastic (bulk_ingest.py)...")
            os.system("python bulk_ingest.py")
            
        print(f"└── Ciclo terminado. Durmiendo {INTERVALO}s...\n")
        
        # Esperar hasta la siguiente vuelta
        time.sleep(INTERVALO)

except KeyboardInterrupt:
    print("\n[!] Monitor detenido por el usuario.")