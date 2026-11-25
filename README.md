# Estructura y sostenibilidad de la deuda pública peruana

**Nombres y apellidos:** Chinte Ponce, Joseph Alexander
**Código de matrícula:** 2024200494M
**Tema:** N.º 86 del Temario (S13, Apalancamiento y estructura de capital)
**Curso:** Finanzas I (055D), UNCP, 2026-II, Unidad II
**Fecha de corte de los datos:** 2025T4 (extracción: 21/11/2026 BCRP y Banco Mundial; 21 y 22/11/2026 MEF)

## Objetivo

Analizar la composición por moneda y plazo de la deuda pública peruana y su costo promedio, 2000T1 a 2025T4, con datos extraídos de forma automatizada de fuentes oficiales.

## Fuentes y vías de extracción

Vía 1, API (`codigo/01_extraccion_api.py`):

- **BCRPData** (Banco Central de Reserva del Perú), API REST pública sin clave. Series trimestrales de deuda pública en % del PBI (PN03432FQ, PN03433FQ, PN03442FQ, PN03443FQ, PN03469FQ, PN03481FQ, PN03484FQ) y tipo de cambio interbancario promedio mensual (PN01207PM).
  `https://estadisticas.bcrp.gob.pe/estadisticas/series/api/{códigos}/json/{inicio}/{fin}/esp`
- **Banco Mundial**, API v2 pública sin clave. Indicadores GC.DOD.TOTL.GD.ZS, DT.DOD.DPPG.CD, DT.TDS.DPPG.CD y GC.XPN.INTP.RV.ZS para el Perú.
  `https://api.worldbank.org/v2/country/PER/indicator/{indicador}?format=json&date=2000:2025`

Vía 2, scraping y descarga programática (`codigo/02_scraping_web.py`):

- **MEF**, boletines trimestrales "Análisis de la Deuda Pública Bruta", 2010T1 a 2025T4 (64 PDF). La página índice del MEF tiene un desafío antibots (Incapsula); no se evade y se usan dos rutas oficiales (ver `incidencias_fuente.md`):
  - Scraping con BeautifulSoup del listado del MEF en gob.pe (enlaces cuyo texto contiene "Boletín de Deuda", paginación `?sheet=N`, y en cada ficha el PDF en español de `cdn.www.gob.pe`): boletines desde junio de 2024.
    `https://www.gob.pe/institucion/mef/informes-publicaciones/tipos/2-boletin`
  - Descarga programática de los boletines de 2010 a marzo de 2024 desde su URL oficial, que sigue un patrón fijo con la fecha de corte.
    `https://www.mef.gob.pe/contenidos/deuda_publ/documentos/Boletin_Deuda8_DDMMAAAA.pdf`

  El script revisa el robots.txt de cada dominio, hace una pausa de 1 s entre solicitudes y usa un User-Agent identificable. Los PDF quedan intactos en `datos_crudos/mef_pdf/`, las páginas rastreadas en `datos_crudos/gobpe_html/` y el manifiesto con URL, código HTTP y hash de cada PDF en `datos_crudos/mef_manifiesto_descargas.csv`. Luego los parsea con pdfplumber. Por el bloqueo antibots solo se obtuvieron 8 boletines (2010T1 y 2024T2 a 2025T4). La constante `SOLO_PARSEO = True` permite volver a parsear los PDF ya descargados sin consultar ningún portal.

Llave común: el trimestre. El tipo de cambio mensual se promedia por trimestre y los indicadores anuales del Banco Mundial se asignan a los 4 trimestres de su año (ver `03_limpieza_datos.py`). Cada fuente aparece en al menos una tabla o figura del artículo.

## Orden de ejecución

Desde la carpeta del proyecto (en Google Colab, primero `codigo/00_montar_drive.py`, que monta Drive y se ubica en la carpeta):

```
pip install -r requirements.txt
python codigo/01_extraccion_api.py
python codigo/02_scraping_web.py
python codigo/03_limpieza_datos.py
python codigo/04_analisis.py
```

1. `01_extraccion_api.py`: descarga BCRP y Banco Mundial a `datos_crudos/` (JSON originales, sin editar).
2. `02_scraping_web.py`: rastrea la página del MEF, descarga los PDF y genera `datos_crudos/mef_extraccion_pdf_2024200494M.csv` (salida directa del parseo).
3. `03_limpieza_datos.py`: une las fuentes por trimestre y genera `datos_procesados/datos_procesados_2024200494M.csv` y su hash.
4. `04_analisis.py`: genera las tablas (promedios por subperiodo, correlaciones, regresión si hay datos suficientes y comparación del primer y último boletín del MEF) y las figuras en `salidas/`.

## Parámetros congelados

`FECHA_INICIO = "2000-1"` y `FECHA_CORTE = "2025-4"` (trimestral), `2000-1` a `2025-12` (mensual), 2000 a 2025 (Banco Mundial) y boletines del MEF del 31-03-2010 al 31-12-2025. Todos están declarados como constantes al inicio de cada script, sin fechas dinámicas.

## Versión del lenguaje y de las librerías

Ejecutado en Google Colab. Python 3.13.18. Versiones exactas en `requirements.txt`: requests 2.32.4, beautifulsoup4 4.13.5, pdfplumber 0.11.11, pandas 2.2.3, numpy 2.4.6 y matplotlib 3.10.0.

## Hash SHA-256 del archivo procesado

```
aa0c3514719a61b4f6cd4b1dc22e926c375b3fe748b31fdf0f301697d76e7e6d
```

Corresponde a `datos_procesados/datos_procesados_2024200494M.csv` generado el 22/11/2026. Si una nueva ejecución da otro hash (por revisiones de las fuentes), se actualiza aquí con su fecha.

## Estructura de la carpeta

```
codigo/                    scripts 00 a 04 y generar_requirements.py
datos_crudos/              respuestas originales: bcrp/, banco_mundial/, gobpe_html/, mef_pdf/ y CSV del parseo del MEF
datos_procesados/          panel final y su hash
salidas/                   tablas (.csv) y figuras (.png) del artículo
evidencias_incidencias/    capturas y respuesta del portal del MEF (ver incidencias_fuente.md)
```

## Clave de API

Ninguna fuente requiere clave (ver `.env.example`).

## Repositorio

Enlace de GitHub: (https://github.com/Joseph-Alexander-Chinte-Ponce/deuda-publica-peru-estructura)
