# 🕵️‍♂️ Wallapop Fraud Radar 

![Python](https://img.shields.io/badge/Python-3.10-blue?style=for-the-badge&logo=python)
![Elastic Stack](https://img.shields.io/badge/Elastic-8.x-f48024?style=for-the-badge&logo=elasticsearch)
![Kibana](https://img.shields.io/badge/Kibana-Visualization-hotpink?style=for-the-badge&logo=kibana)
![Status](https://img.shields.io/badge/Status-Active-success?style=for-the-badge)

> **Sistema de Ciberinteligencia** diseñado para la detección en tiempo real de fraudes, estafas y anomalías de mercado en la categoría de Smartphones (iPhone) dentro de Wallapop.

---

## 📖 Descripción del Proyecto

Este proyecto implementa un pipeline completo de **Monitorización y Alerta** (basado en la Opción A.1) capaz de recolectar datos de mercado, analizarlos mediante lógica de negocio avanzada y visualizar amenazas potenciales.

El sistema no se limita a recolectar precios, sino que aplica una **Lógica de Sospecha (Suspicion Logic)** basada en:
* 📉 **Segmentación de Precios:** Detecta "chollos imposibles" comparando el precio con la media del modelo específico (ej: iPhone 15 Pro vs iPhone 11).
* 🚨 **Keywords Críticas:** Identifica intentos de pago externo (Bizum, Transferencia) y venta de réplicas/clones.
* 🤖 **Detección de Bots:** Analiza patrones de publicación masiva por usuario (Volume Anomalies).

---

## 🏗️ Arquitectura del Sistema

El flujo de datos sigue el siguiente esquema:

`Wallapop API` -> `Poller (Python)` -> `JSON Maestro` -> `Elasticsearch` -> `Kibana / Elastalert`

### Componentes Principales

| Componente | Tecnología | Función |
| :--- | :--- | :--- |
| **Collector** | Python | Extracción de datos y cálculo de `risk_score` (0-100). |
| **Storage** | Elasticsearch | Indexación de anuncios con geolocalización. |
| **Viz** | Kibana | Mapas de calor, histogramas de precio y detección de tendencias. |
| **Alerting** | Elastalert2 | Vigilancia continua y notificación de incidentes críticos. |

---

## 📂 Estructura del Repositorio

```
wallapop-fraud-lab/
├── 🐍 poller/
│   ├── poller.py            # Script principal de recolección inteligente
│   ├── requirements.txt     # Dependencias necesarias
│   └── README.md            # Documentación específica del poller
│
├── 📥 ingestion/
│   ├── bulk_ingest.py       # Script de subida a Elastic
│   ├── monitor.py           # Orquestador (Loop infinito de recolección)
│   └── wallapop_master.json # Base de datos local (formato NDJSON)
│
├── 📊 kibana/
│   ├── dashboard_export.ndjson  # Plantilla importable del Dashboard completo
│   └── screenshots/             # Evidencias visuales para el reporte
│
├── 🚨 elastalert/
│   ├── config.yaml          # Configuración de conexión a Elastic
│   └── rules/               # Reglas de detección (YAML)
│       ├── low_price.yaml   # Detecta anomalías de precio por modelo
│       ├── high_risk.yaml   # Detecta Score > 80
│       └── keywords.yaml    # Detecta Bizum, WhatsApp y Clones
│
└── 📑 report/
    └── report.pdf           # Informe final del proyecto
```



## 🚀 Instalación y Despliegue

``
### 1. Prerrequisitos
* Ubuntu / Linux (Recomendado).

* **Python 3.10+**.

* **Acceso a un clúster Elasticsearch activo (v8+)**.

### 2. Instalación de Dependencias
```bash
# Instalar librerías del poller
cd poller
pip install -r requirements.txt
```

# Instalar motor de alertas (Versión compatible con Py3.10)
```bash
pip install "elastalert2==2.15.0"
```

### 3. Ejecución del Monitor

* El script monitor.py se encarga de ejecutar el ciclo de vida completo (Descarga -> Análisis -> Ingesta) cada 5 minutos.

```bash
cd ../ingestion
python3 monitor.py
```

### 4. Activación de Alertas
* En una terminal separada, lanza el vigilante para monitorizar reglas en tiempo real:

```bash
cd ../elastalert
python3 -m elastalert.elastalert --verbose
```

---

## 📸 Capturas de Pantalla (Evidencias)

* 🗺️ Mapa de Riesgo de Fraude
Geolocalización de anuncios sospechosos en la península.

* 📉 Detección de Anomalías de Precio
Histograma que muestra la desviación de precios de estafa frente al mercado real.

* 🚨 Alerta en Tiempo Real
Elastalert detectando un intento de estafa y disparando la notificación por consola/email.

* 🛡️ Reglas de Seguridad Implementadas
El sistema vigila activamente las siguientes amenazas:

* High Risk Score: Cualquier ítem que supere los 80 puntos de riesgo (acumulación de factores).

* Price Anomaly: Detección de modelos de gama alta (ej: iPhone 15) vendidos por debajo del 40% de su valor de mercado.

## Blacklisted Keywords:

* bizum, transferencia (Evasión de pagos seguros).

* réplica, clon, 1:1 (Falsificaciones y estafas de producto).

* 6xx xxx xxx (Números de teléfono ofuscados en la descripción).

---

## 📜 Licencia

Este proyecto se distribuye bajo la Licencia MIT.

Copyright (c) 2025 Iván Ciudad Cires y Víctor Carbajo Ruiz.

Consulta el archivo `LICENSE` en la raíz del repositorio para ver

