# Diccionario de variables

**Tema N.º 86:** Estructura y sostenibilidad de la deuda pública peruana
**Estudiante:** Chinte Ponce, Joseph Alexander. Código 2024200494M
**Archivo descrito:** `datos_procesados/datos_procesados_2024200494M.csv`
**Llave común:** `trimestre` (formato AAAATq, por ejemplo 2025T4). Ventana: 2000T1 a 2025T4 (104 trimestres).

## Identificadores

| Variable | Definición | Unidad | Fuente |
|---|---|---|---|
| `trimestre` | Trimestre calendario (llave de unión) | AAAATq | Construida |
| `anio` | Año del trimestre | Año | Construida |
| `q` | Número de trimestre (1 a 4) | Entero | Construida |

## Vía 1: API del BCRP (frecuencia trimestral nativa salvo el tipo de cambio)

Endpoint: `https://estadisticas.bcrp.gob.pe/estadisticas/series/api/{códigos}/json/2000-1/2025-4/esp`

| Variable | Definición | Unidad | Frecuencia | Serie |
|---|---|---|---|---|
| `deuda_publica_pbi` | Saldo de la deuda pública del sector público no financiero | % del PBI | Trimestral | PN03432FQ |
| `deuda_externa_pbi` | Deuda pública externa | % del PBI | Trimestral | PN03433FQ |
| `deuda_interna_pbi` | Deuda pública interna | % del PBI | Trimestral | PN03442FQ |
| `deuda_interna_lp_pbi` | Deuda interna de largo plazo | % del PBI | Trimestral | PN03443FQ |
| `deuda_interna_cp_pbi` | Deuda interna de corto plazo | % del PBI | Trimestral | PN03469FQ |
| `deuda_neta_pbi` | Deuda neta del sector público no financiero | % del PBI | Trimestral | PN03481FQ |
| `bonos_no_residentes_pbi` | Bonos globales y soberanos en poder de no residentes | % del PBI | Trimestral | PN03484FQ |
| `tc_promedio` | Tipo de cambio interbancario, promedio de los 3 meses del trimestre | S/ por US$ | Mensual, promediado a trimestral | PN01207PM |

## Vía 1: API del Banco Mundial (frecuencia anual, asignada a los 4 trimestres del año)

Endpoint: `https://api.worldbank.org/v2/country/PER/indicator/{indicador}?format=json&date=2000:2025`

| Variable | Definición | Unidad | Indicador |
|---|---|---|---|
| `deuda_gob_central_pbi_bm` | Deuda total del gobierno central | % del PIB | GC.DOD.TOTL.GD.ZS |
| `deuda_externa_ppg_musd_bm` | Stock de deuda externa pública y con garantía pública | Millones de US$ | DT.DOD.DPPG.CD |
| `servicio_deuda_externa_ppg_musd_bm` | Servicio de la deuda externa pública y con garantía pública | Millones de US$ | DT.TDS.DPPG.CD |
| `intereses_pct_ingresos_bm` | Pago de intereses | % de los ingresos del gobierno | GC.XPN.INTP.RV.ZS |

## Vía 2: scraping y descarga programática del MEF (boletines trimestrales, 2010T1 a 2025T4)

Página rastreada: `https://www.mef.gob.pe/es/reporte-trimestral-de-deuda-publica`. Cada boletín se descarga en PDF y se parsea con pdfplumber. Entre 2000T1 y 2009T4 estas variables quedan vacías porque el MEF no publicó boletines en ese periodo. Por el bloqueo antibots del portal (ver `incidencias_fuente.md`) solo se obtuvieron 8 boletines: 2010T1 y 2024T2 a 2025T4; los demás trimestres quedan vacíos y no se imputan.

| Variable | Definición | Unidad | Tabla del boletín |
|---|---|---|---|
| `saldo_deuda_mef_mmsoles` | Saldo de la deuda pública bruta. Los boletines antiguos lo reportan en millones de US$; se convierte a soles con `tc_promedio` del mismo trimestre | Miles de millones de S/ | Saldo de deuda bruta, fila Total |
| `vida_media` | Plazo promedio que falta para pagar el principal | Años | Saldo de deuda bruta, fila Total |
| `duracion` | Duración (plazo promedio ponderado de los flujos) | Años | Saldo de deuda bruta, fila Total |
| `reprecio_medio` | Plazo promedio en que se fijan nuevas tasas | Años | Saldo de deuda bruta, fila Total |
| `costo_promedio` | Tasa equivalente en soles del portafolio de deuda | % anual | Saldo de deuda bruta, fila Total |
| `pct_soles` | Deuda en soles sobre el saldo total | % | Saldo por moneda |
| `pct_dolares` | Deuda en dólares sobre el saldo total | % | Saldo por moneda |
| `pct_euros` | Deuda en euros sobre el saldo total. Vacía cuando el boletín no separa los euros (p. ej. 2010T1, donde van dentro de "Otras") | % | Saldo por moneda |
| `pct_otras_monedas` | Deuda en yenes y otras monedas sobre el saldo total | % | Saldo por moneda |

## Variables derivadas (calculadas en 03_limpieza_datos.py)

| Variable | Cálculo | Unidad |
|---|---|---|
| `participacion_externa_pct` | 100 × deuda_externa_pbi / deuda_publica_pbi | % del total |
| `participacion_cp_interna_pct` | 100 × deuda_interna_cp_pbi / deuda_interna_pbi | % de la deuda interna |
| `pct_moneda_extranjera` | 100 − pct_soles | % |
