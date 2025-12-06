import pygame
import json
import os
import requests
import io
import sys

# --- CONFIGURACIÓN DEL VISOR ---
ANCHO_VENTANA = 1000
ALTO_VENTANA = 700
ARCHIVO_DATOS = "../ingestion/wallapop_master.json" 

# Colores
BLANCO = (255, 255, 255)
NEGRO = (0, 0, 0)
GRIS = (200, 200, 200)
GRIS_OSCURO = (50, 50, 50)
ROJO_ALERTA = (220, 20, 60)
VERDE_OK = (34, 139, 34)
AZUL_LINK = (30, 144, 255)

class VisorWallapop:
    def __init__(self):
        pygame.init()
        self.pantalla = pygame.display.set_mode((ANCHO_VENTANA, ALTO_VENTANA))
        pygame.display.set_caption("Visor de Fraude Wallapop")
        self.reloj = pygame.time.Clock()
        self.fuente_titulo = pygame.font.SysFont("Arial", 28, bold=True)
        self.fuente_texto = pygame.font.SysFont("Arial", 20)
        self.fuente_mini = pygame.font.SysFont("Arial", 16)
        
        self.items = []
        self.indice_actual = 0
        self.cache_imagenes = {}
        self.orden_actual = "Defecto"
        
        self.cargar_datos()

    def cargar_datos(self):
        print("[*] Cargando datos del JSON...")
        self.items = []
        if os.path.exists(ARCHIVO_DATOS):
            with open(ARCHIVO_DATOS, 'r', encoding='utf-8') as f:
                for linea in f:
                    if linea.strip():
                        try:
                            self.items.append(json.loads(linea))
                        except: pass
        else:
            print(f"[!] No se encuentra {ARCHIVO_DATOS}")
        
        print(f"[*] {len(self.items)} items cargados.")

    def descargar_imagen(self, url):
        if not url: return None
        if url in self.cache_imagenes:
            return self.cache_imagenes[url]
        
        try:
            print(f"Descargando imagen: {url}")
            r = requests.get(url, timeout=5)
            img_bytes = io.BytesIO(r.content)
            img = pygame.image.load(img_bytes)
            # Escalar imagen para que quepa en la mitad izquierda
            img = pygame.transform.scale(img, (400, 400))
            self.cache_imagenes[url] = img
            return img
        except Exception as e:
            print(f"Error imagen: {e}")
            return None

    def ordenar(self, criterio):
        if not self.items: return
        
        if criterio == "riesgo":
            self.items.sort(key=lambda x: x['enrichment']['risk_score'], reverse=True)
            self.orden_actual = "Mayor Riesgo"
        elif criterio == "precio":
            self.items.sort(key=lambda x: x.get('price', 999999))
            self.orden_actual = "Menor Precio"
        elif criterio == "fecha":
            self.items.sort(key=lambda x: x['timestamps']['crawled_at'], reverse=True)
            self.orden_actual = "Más Recientes"
            
        self.indice_actual = 0
        self.cache_imagenes.clear() # Limpiar cache al reordenar para no consumir mucha RAM

    def dibujar_texto_multilinea(self, texto, x, y, ancho_max, color=NEGRO, fuente=None):
        if fuente is None: fuente = self.fuente_texto
        palabras = texto.split(' ')
        lineas = []
        linea_actual = ""
        
        for palabra in palabras:
            test_linea = linea_actual + palabra + " "
            if fuente.size(test_linea)[0] < ancho_max:
                linea_actual = test_linea
            else:
                lineas.append(linea_actual)
                linea_actual = palabra + " "
        lineas.append(linea_actual)
        
        for i, linea in enumerate(lineas):
            sup = fuente.render(linea, True, color)
            self.pantalla.blit(sup, (x, y + i * 25))

    def ejecutar(self):
        corriendo = True
        while corriendo:
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    corriendo = False
                
                if evento.type == pygame.KEYDOWN:
                    if evento.key == pygame.K_ESCAPE: corriendo = False
                    
                    # Navegación
                    if evento.key == pygame.K_RIGHT:
                        if self.indice_actual < len(self.items) - 1:
                            self.indice_actual += 1
                    if evento.key == pygame.K_LEFT:
                        if self.indice_actual > 0:
                            self.indice_actual -= 1
                            
                    # Ordenación
                    if evento.key == pygame.K_r: self.ordenar("riesgo")
                    if evento.key == pygame.K_p: self.ordenar("precio")
                    if evento.key == pygame.K_f: self.ordenar("fecha")

            # --- DIBUJAR ---
            self.pantalla.fill(BLANCO)
            
            if not self.items:
                texto = self.fuente_titulo.render("No hay datos. Ejecuta el poller primero.", True, NEGRO)
                self.pantalla.blit(texto, (50, 50))
                pygame.display.flip()
                continue

            item = self.items[self.indice_actual]
            riesgo = item['enrichment']['risk_score']
            
            # Panel izquierdo (Imagen)
            pygame.draw.rect(self.pantalla, GRIS, (20, 80, 420, 420))
            img_url = item.get("image_url")
            
            if img_url:
                img = self.descargar_imagen(img_url)
                if img:
                    self.pantalla.blit(img, (30, 90))
                else:
                    txt = self.fuente_texto.render("Sin Imagen / Error", True, NEGRO)
                    self.pantalla.blit(txt, (150, 250))
            else:
                txt = self.fuente_texto.render("Anuncio sin imagen", True, NEGRO)
                self.pantalla.blit(txt, (150, 250))

            # Panel derecho (Info)
            x_info = 470
            y_info = 80
            
            # Título
            self.dibujar_texto_multilinea(item.get("title", "Sin título"), x_info, y_info, 500, NEGRO, self.fuente_titulo)
            y_info += 80
            
            # Precio
            precio = f"{item.get('price')} {item.get('currency')}"
            txt_precio = self.fuente_titulo.render(precio, True, VERDE_OK)
            self.pantalla.blit(txt_precio, (x_info, y_info))
            y_info += 50
            
            # Riesgo (Con fondo de color)
            color_riesgo = ROJO_ALERTA if riesgo > 50 else VERDE_OK
            pygame.draw.rect(self.pantalla, color_riesgo, (x_info, y_info, 250, 40), border_radius=5)
            txt_riesgo = self.fuente_titulo.render(f"RIESGO: {riesgo}/100", True, BLANCO)
            self.pantalla.blit(txt_riesgo, (x_info + 10, y_info + 5))
            y_info += 60
            
            # Factores de riesgo
            factores = item['enrichment']['risk_factors']
            if factores:
                self.pantalla.blit(self.fuente_texto.render("Motivos de sospecha:", True, NEGRO), (x_info, y_info))
                y_info += 30
                for f in factores:
                    self.pantalla.blit(self.fuente_mini.render(f"• {f}", True, ROJO_ALERTA), (x_info, y_info))
                    y_info += 20
            
            y_info += 20
            
            # Descripción (Truncada)
            desc = item.get("description", "")[:400] + "..."
            self.pantalla.blit(self.fuente_texto.render("Descripción:", True, NEGRO), (x_info, y_info))
            y_info += 25
            self.dibujar_texto_multilinea(desc, x_info, y_info, 500, GRIS_OSCURO, self.fuente_mini)

            # Barra Inferior (Controles)
            pygame.draw.rect(self.pantalla, GRIS_OSCURO, (0, ALTO_VENTANA - 60, ANCHO_VENTANA, 60))
            info_nav = f"Item {self.indice_actual + 1} de {len(self.items)} | Orden: {self.orden_actual}"
            ayuda = "[Flechas] Navegar | [R] Ordenar Riesgo | [P] Ordenar Precio | [F] Ordenar Fecha"
            
            self.pantalla.blit(self.fuente_texto.render(info_nav, True, BLANCO), (20, ALTO_VENTANA - 50))
            self.pantalla.blit(self.fuente_mini.render(ayuda, True, GRIS), (20, ALTO_VENTANA - 25))

            pygame.display.flip()
            self.reloj.tick(30)

        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    VisorWallapop().ejecutar()