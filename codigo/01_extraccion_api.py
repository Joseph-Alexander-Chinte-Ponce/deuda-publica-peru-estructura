# Nombres y apellidos: Chinte Ponce, Joseph Alexander
# Codigo de matricula: 2024200494M
# Tema: N.86 - Estructura y sostenibilidad de la deuda publica peruana
# Fecha de extraccion: (completar con la fecha real de ejecucion)

"""
VIA 1 - API. Descarga, sin editar, tres grupos de series:

  A) BCRPData (API REST publica, sin clave), frecuencia TRIMESTRAL.
     Cuadro "Saldo de la deuda del sector publico no financiero (% del PBI)".
     https://estadisticas.bcrp.gob.pe/estadisticas/series/trimestrales/saldo-de-deuda-publica-porcentaje-del-pbi
  B) BCRPData, frecuencia MENSUAL: tipo de cambio interbancario promedio.
     (La API no permite mezclar frecuencias en una misma consulta.)
  C) Banco Mundial, API v2 (publica, sin clave), frecuencia ANUAL:
     indicadores de deuda del Peru.

Formato BCRP: https://estadisticas.bcrp.gob.pe/estadisticas/series/api/[codigos]/json/[inicio]/[fin]/esp
Formato Banco Mundial: https://api.worldbank.org/v2/country/PER/indicator/[id]?format=json&date=[ini]:[fin]

Cada respuesta se guarda tal como llega (bytes originales) en datos_crudos/.
Se ejecuta desde la carpeta del proyecto (en Colab, despues de 00_montar_drive.py).
"""

import os
import time
import json
from datetime import datetime

import requests

# ----------------------------------------------------------------------
# PARAMETROS CONGELADOS (numeral 2.4.5): constantes fijas, nunca "hoy"
# ----------------------------------------------------------------------
FECHA_INICIO = "2000-1"        # trimestre inicial (anio-trimestre)
FECHA_CORTE = "2025-4"         # trimestre final
FECHA_INICIO_MES = "2000-1"    # para el tipo de cambio mensual (anio-mes)
FECHA_CORTE_MES = "2025-12"
ANIO_INICIO_BM = 2000          # Banco Mundial (anual)
ANIO_CORTE_BM = 2025

# Codigos BCRP trimestrales (todos en % del PBI). El orden importa:
# el BCRP devuelve las series en el mismo orden en que se piden.
SERIES_BCRP_TRIM = {
    "deuda_publica_pbi": "PN03432FQ",        # Deuda publica total
    "deuda_externa_pbi": "PN03433FQ",        # Deuda publica externa
    "deuda_interna_pbi": "PN03442FQ",        # Deuda publica interna
    "deuda_interna_lp_pbi": "PN03443FQ",     # Interna de largo plazo
    "deuda_interna_cp_pbi": "PN03469FQ",     # Interna de corto plazo
    "deuda_neta_pbi": "PN03481FQ",           # Deuda neta del SPNF
    "bonos_no_residentes_pbi": "PN03484FQ",  # Bonos globales y soberanos en manos de no residentes
}

# Codigo BCRP mensual
SERIES_BCRP_MES = {
    "tc_interbancario_promedio": "PN01207PM",  # S/ por US$, promedio del periodo
}

# Indicadores del Banco Mundial (WDI / International Debt Statistics)
INDICADORES_BM = {
    "GC.DOD.TOTL.GD.ZS": "deuda_gob_central_pbi_bm",      # Deuda del gobierno central (% PBI)
    "DT.DOD.DPPG.CD": "deuda_externa_ppg_usd_bm",         # Stock de deuda externa publica y con garantia publica (US$)
    "DT.TDS.DPPG.CD": "servicio_deuda_externa_ppg_usd_bm",  # Servicio de esa deuda (US$)
    "GC.XPN.INTP.RV.ZS": "intereses_pct_ingresos_bm",     # Pago de intereses (% de los ingresos)
}

URL_BCRP = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api"
URL_BM = "https://api.worldbank.org/v2/country/PER/indicator"
USER_AGENT = "UNCP-FinanzasI-055D-2024200494M/2.0 (uso academico; e_2024200494M@uncp.edu.pe)"

CARPETA_BCRP = os.path.join("datos_crudos", "bcrp")
CARPETA_BM = os.path.join("datos_crudos", "banco_mundial")
ARCHIVO_LOG = "log_ejecucion.txt"
PAUSA_SEG = 1.0      # pausa minima entre solicitudes (numeral 2.4.8)
REINTENTOS = 3


def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def descargar(url, log, etiqueta):
    """GET con reintentos. Devuelve (bytes, codigo_http) o (None, codigo) si falla."""
    codigo = None
    for intento in range(1, REINTENTOS + 1):
        try:
            resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=60)
            codigo = resp.status_code
            resp.raise_for_status()
            return resp.content, codigo
        except requests.exceptions.RequestException as e:
            print(f"   [intento {intento}/{REINTENTOS}] {etiqueta}: {e}")
            log.append(f"{ahora()} | {etiqueta} | intento {intento} fallido | HTTP {codigo} | {e}")
            time.sleep(PAUSA_SEG * 3 * intento)
    return None, codigo


def guardar_bytes(contenido, ruta):
    with open(ruta, "wb") as f:
        f.write(contenido)


def extraer_bcrp(series, inicio, fin, nombre_archivo, log):
    """Una sola consulta (max. 10 codigos, misma frecuencia). Guarda el JSON crudo."""
    codigos = list(series.values())
    url = f"{URL_BCRP}/{'-'.join(codigos)}/json/{inicio}/{fin}/esp"
    contenido, codigo = descargar(url, log, f"BCRP {nombre_archivo}")
    if contenido is None:
        print(f"[ERROR] BCRP {nombre_archivo}: sin respuesta valida")
        return
    ruta = os.path.join(CARPETA_BCRP, nombre_archivo)
    guardar_bytes(contenido, ruta)
    datos = json.loads(contenido.decode("utf-8"))
    n_periodos = len(datos.get("periods", []))
    nombres = [s.get("name", "") for s in datos.get("config", {}).get("series", [])]
    log.append(f"{ahora()} | BCRP {nombre_archivo} | HTTP {codigo} | {n_periodos} periodos | {len(nombres)} series | {url}")
    print(f"[OK] BCRP {nombre_archivo}: HTTP {codigo}, {n_periodos} periodos, {len(nombres)} series")
    for codigo_serie, nombre in zip(codigos, nombres):
        print(f"     {codigo_serie} -> {nombre}")
    time.sleep(PAUSA_SEG)


def extraer_banco_mundial(log):
    """Una consulta por indicador. Guarda el JSON crudo de cada uno."""
    for indicador, variable in INDICADORES_BM.items():
        url = f"{URL_BM}/{indicador}?format=json&date={ANIO_INICIO_BM}:{ANIO_CORTE_BM}&per_page=500"
        contenido, codigo = descargar(url, log, f"BM {indicador}")
        if contenido is None:
            print(f"[ERROR] Banco Mundial {indicador}: sin respuesta valida")
            continue
        ruta = os.path.join(CARPETA_BM, f"{indicador}.json")
        guardar_bytes(contenido, ruta)
        datos = json.loads(contenido.decode("utf-8"))
        registros = datos[1] if isinstance(datos, list) and len(datos) > 1 and datos[1] else []
        con_valor = [r for r in registros if r.get("value") is not None]
        anios = sorted(r["date"] for r in con_valor)
        rango = f"{anios[0]}-{anios[-1]}" if anios else "sin datos"
        log.append(f"{ahora()} | BM {indicador} ({variable}) | HTTP {codigo} | {len(registros)} filas | {len(con_valor)} con valor | {rango} | {url}")
        print(f"[OK] Banco Mundial {indicador}: HTTP {codigo}, {len(con_valor)} anios con dato ({rango})")
        time.sleep(PAUSA_SEG)


def main():
    if not os.path.isdir("datos_crudos"):
        raise SystemExit("No estoy en la carpeta del proyecto: corre primero 00_montar_drive.py")
    os.makedirs(CARPETA_BCRP, exist_ok=True)
    os.makedirs(CARPETA_BM, exist_ok=True)

    log = [f"=== 01_extraccion_api iniciada: {ahora()} ===",
           f"Parametros: trimestral {FECHA_INICIO} a {FECHA_CORTE} | mensual {FECHA_INICIO_MES} a {FECHA_CORTE_MES} | BM {ANIO_INICIO_BM}-{ANIO_CORTE_BM}"]
    print(log[0]); print(log[1])

    print("\n--- BCRP trimestral (deuda publica, % del PBI) ---")
    extraer_bcrp(SERIES_BCRP_TRIM, FECHA_INICIO, FECHA_CORTE, "bcrp_deuda_trimestral.json", log)

    print("\n--- BCRP mensual (tipo de cambio) ---")
    extraer_bcrp(SERIES_BCRP_MES, FECHA_INICIO_MES, FECHA_CORTE_MES, "bcrp_tipo_cambio_mensual.json", log)

    print("\n--- Banco Mundial (anual) ---")
    extraer_banco_mundial(log)

    log.append(f"=== 01_extraccion_api finalizada: {ahora()} ===")
    with open(ARCHIVO_LOG, "a", encoding="utf-8") as f:
        f.write("\n".join(log) + "\n\n")
    print("\nListo. Siguiente paso: 02_scraping_web.py")


if __name__ == "__main__":
    main()
