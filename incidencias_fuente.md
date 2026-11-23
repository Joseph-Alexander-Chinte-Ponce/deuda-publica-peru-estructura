# Registro de incidencias de la fuente (numeral 2.4.3)

**Estudiante:** Chinte Ponce, Joseph Alexander. Código 2024200494M
**Tema:** N.º 86, Estructura y sostenibilidad de la deuda pública peruana (Unidad II)
**Vía afectada:** Vía 2, scraping y descarga programática (MEF, boletines trimestrales de deuda pública)

## Incidencia 1: desafío antibots en la página índice del MEF

| Campo | Detalle |
|---|---|
| URL | https://www.mef.gob.pe/es/reporte-trimestral-de-deuda-publica |
| Fecha y hora | 21/11/2026, 20:32 (hora de Lima), 01:32 UTC del 22/11/2026, según log_ejecucion.txt |
| Código de respuesta HTTP | 200, pero con un cuerpo de 212 bytes sin contenido |
| Respuesta del portal | Página con `<META NAME="robots" CONTENT="noindex,nofollow">` y un script `/_Incapsula_Resource?...`: desafío antibots de Imperva Incapsula, que exige ejecutar JavaScript en un navegador |
| robots.txt | Permite la ruta, pero la etiqueta meta de la propia página pide a los robots no indexar ni seguir enlaces |
| Resultado | El script no encontró enlaces (0 boletines); ver `datos_crudos/mef_pagina_listado.html` de esa ejecución |
| Evidencia | `evidencias_incidencias/incidencia1_respuesta_incapsula_mef_21-11-2026.html` (respuesta de 212 bytes guardada por el script; también en `datos_crudos/mef_pagina_listado.html`) |

**Decisión:** no se intenta evadir el desafío (ni con navegador automatizado ni copiando cookies), porque el numeral 2.4.8 prohíbe vulnerar accesos restringidos y exige respetar los términos de uso del portal.

## Vía sustituta propuesta (misma fuente, otra ruta oficial de acceso)

La fuente sigue siendo la misma: los boletines "Reporte Trimestral - Análisis de la Deuda Pública Bruta" de la Dirección General del Tesoro Público del MEF. Solo cambia la página desde la que se obtienen sus enlaces:

1. **Scraping** de la página oficial del MEF en la plataforma del Estado, https://www.gob.pe/institucion/mef/informes-publicaciones/tipos/2-boletin (robots.txt de gob.pe: permitido). Cubre los boletines desde el 30/06/2024.
2. **Descarga programática** de los boletines anteriores (31/03/2010 a 31/03/2024) desde su URL oficial en https://www.mef.gob.pe/contenidos/deuda_publ/documentos/ (ruta sin desafío antibots; prueba del 21/11/2026: HTTP 200, `application/pdf`). El nombre de cada archivo sigue un patrón fijo con la fecha de corte.

Las dos rutas se probaron el 21/11/2026 desde Google Colab: respondieron HTTP 200 con PDF válidos y sin desafío antibots.

## Incidencia 2: el desafío antibots se extiende a los PDF de mef.gob.pe/contenidos

| Campo | Detalle |
|---|---|
| URL de ejemplo | https://www.mef.gob.pe/contenidos/deuda_publ/documentos/Boletin_Deuda8_30062023.pdf |
| Fecha y hora | 21/11/2026, 20:40 a 20:45 (hora de Lima), según log_ejecucion.txt |
| Código de respuesta HTTP | 200, `text/html`, 212 bytes (en lugar del PDF) |
| Respuesta del portal | La misma página de desafío de Incapsula (`/_Incapsula_Resource?...`, `noindex,nofollow`) |
| Contexto | La misma URL respondió con el PDF (`application/pdf`, 117 350 bytes) en una consulta aislada a las 20:35; al descargar los boletines en secuencia, el portal empezó a responder con el desafío |
| Resultado | 57 boletines (31/03/2010 a 31/03/2024) sin descargar; los 7 de gob.pe (30/06/2024 a 31/12/2025) sí se descargaron y parsearon (4 de 4 campos en cada uno) |
| Evidencia | `evidencias_incidencias/incidencia2_bloqueo_pdf_mef_21-11-2026.png` (salida del script); `datos_crudos/mef_manifiesto_descargas.csv` y `log_ejecucion.txt` registran el estado de cada boletín |

**Medidas tomadas (sin evadir el bloqueo):** el script detecta la página de desafío, deja de consultar mef.gob.pe en esa ejecución, sube la pausa entre solicitudes a ese dominio a 5 s y conserva los PDF ya descargados para no volver a pedirlos. Se hizo un único reintento en otra fecha (tabla siguiente). Como el bloqueo persistió, no se insiste más: las variables del MEF se analizan solo con los 8 boletines disponibles (2010T1 y 2024T2 a 2025T4) y la limitación se declara en el artículo.

| Reintento | Fecha y hora | Resultado |
|---|---|---|
| 1 | 22/11/2026, 20:29 (hora de Lima), 01:29 UTC del 23/11/2026 | Se descargó 1 PDF (31/03/2010); en el segundo (30/06/2010) el portal volvió a responder con el desafío antibots. El script se detuvo y no insistió. Evidencia: `evidencias_incidencias/incidencia2_reintento_22-11-2026.png` |

## Autorización del docente

| Campo | Detalle |
|---|---|
| Fecha de la solicitud | Antes del 17/11/2026 (dentro del plazo: hasta 5 días antes del EXANTE del 07/12/2026) |
| Canal | Grupo de WhatsApp del curso |
| Respuesta del docente | Martes 17/11/2026: autoriza el uso de la fuente |
| Nota | La incidencia se consultó al docente antes del 17/11/2026 y se re-verificó y documentó con evidencia el 21/11/2026 |
