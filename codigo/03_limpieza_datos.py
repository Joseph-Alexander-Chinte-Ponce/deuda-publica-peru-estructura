# Nombres y apellidos: Chinte Ponce, Joseph Alexander
# Codigo de matricula: 2024200494M
# Tema: N.86 - Estructura y sostenibilidad de la deuda publica peruana
# Fecha de extraccion: (completar con la fecha real de ejecucion)

"""
Limpia, tipifica y une las tres fuentes por la LLAVE COMUN: el trimestre (AAAA'T'q).

  - BCRP trimestral (% del PBI)                -> se usa tal cual (frecuencia nativa).
  - BCRP mensual (tipo de cambio)              -> promedio de los 3 meses de cada trimestre.
  - Banco Mundial (anual)                      -> el valor anual se asigna a los 4 trimestres
                                                  del mismo anio (armonizacion explicita).
  - MEF (boletines trimestrales parseados)     -> fecha de corte -> trimestre.

Ventana del panel: 2000T1 a 2025T4 (104 trimestres). El MEF publica boletines
desde 2010T1, por eso sus variables quedan vacias (NaN) entre 2000 y 2009: no se
imputan ni se inventan.

Salida: datos_procesados/datos_procesados_2024200494M.csv y su hash SHA-256.
"""

import os
import re
import glob
import json
import hashlib

import numpy as np
import pandas as pd

TRIMESTRE_INICIO = "2000T1"   # congelado, coherente con 01_extraccion_api.py
TRIMESTRE_CORTE = "2025T4"

CARPETA_BCRP = os.path.join("datos_crudos", "bcrp")
CARPETA_BM = os.path.join("datos_crudos", "banco_mundial")
ARCHIVO_MEF = os.path.join("datos_crudos", "mef_extraccion_pdf_2024200494M.csv")
SALIDA = os.path.join("datos_procesados", "datos_procesados_2024200494M.csv")
SALIDA_HASH = os.path.join("datos_procesados", "hash_sha256.txt")

# Mismo orden en que 01_extraccion_api.py pidio los codigos
VARIABLES_BCRP_TRIM = ["deuda_publica_pbi", "deuda_externa_pbi", "deuda_interna_pbi",
                       "deuda_interna_lp_pbi", "deuda_interna_cp_pbi", "deuda_neta_pbi",
                       "bonos_no_residentes_pbi"]
INDICADORES_BM = {
    "GC.DOD.TOTL.GD.ZS": "deuda_gob_central_pbi_bm",
    "DT.DOD.DPPG.CD": "deuda_externa_ppg_musd_bm",
    "DT.TDS.DPPG.CD": "servicio_deuda_externa_ppg_musd_bm",
    "GC.XPN.INTP.RV.ZS": "intereses_pct_ingresos_bm",
}
EN_DOLARES = {"DT.DOD.DPPG.CD", "DT.TDS.DPPG.CD"}   # se pasan a millones de US$

MESES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7,
         "ago": 8, "set": 9, "sep": 9, "oct": 10, "nov": 11, "dic": 12}


def a_flotante(valor):
    """El BCRP marca los datos faltantes como 'n.d.' u otro texto: se convierten en NaN."""
    try:
        return float(valor)
    except (TypeError, ValueError):
        return np.nan


def anio_completo(dos_o_cuatro_digitos):
    a = int(dos_o_cuatro_digitos)
    if a >= 1000:
        return a
    return 1900 + a if a > 50 else 2000 + a


def trimestre_bcrp(etiqueta):
    """'T1.00', 'T100', 'T1.2000' -> '2000T1'"""
    m = re.search(r"T\s*\.?\s*([1-4])\s*\.?\s*(\d{4}|\d{2})\b", etiqueta)
    if not m:
        raise ValueError(f"Periodo trimestral no reconocido: {etiqueta!r}")
    return f"{anio_completo(m.group(2))}T{m.group(1)}"


def trimestre_desde_mes(etiqueta):
    """'Ene.2000' o 'Ene.00' -> '2000T1'"""
    m = re.match(r"([A-Za-z]{3})\w*\.?\s*(\d{4}|\d{2})", etiqueta)
    if not m:
        raise ValueError(f"Periodo mensual no reconocido: {etiqueta!r}")
    mes = MESES[m.group(1).lower()]
    return f"{anio_completo(m.group(2))}T{(mes - 1) // 3 + 1}"


def leer_json(ruta):
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def cargar_bcrp_trimestral():
    datos = leer_json(os.path.join(CARPETA_BCRP, "bcrp_deuda_trimestral.json"))
    nombres = [s["name"] for s in datos["config"]["series"]]
    if len(nombres) != len(VARIABLES_BCRP_TRIM):
        raise ValueError(f"Se esperaban {len(VARIABLES_BCRP_TRIM)} series y llegaron {len(nombres)}")
    filas = []
    for p in datos["periods"]:
        fila = {"trimestre": trimestre_bcrp(p["name"])}
        for var, valor in zip(VARIABLES_BCRP_TRIM, p["values"]):
            fila[var] = a_flotante(valor)
        filas.append(fila)
    print("BCRP trimestral: series recibidas (revisa que coincidan con las variables):")
    for var, nombre in zip(VARIABLES_BCRP_TRIM, nombres):
        print(f"   {var:<26} <- {nombre}")
    return pd.DataFrame(filas)


def cargar_bcrp_tipo_cambio():
    datos = leer_json(os.path.join(CARPETA_BCRP, "bcrp_tipo_cambio_mensual.json"))
    filas = [{"trimestre": trimestre_desde_mes(p["name"]), "tc": a_flotante(p["values"][0])}
             for p in datos["periods"]]
    mensual = pd.DataFrame(filas)
    trimestral = (mensual.groupby("trimestre", as_index=False)
                  .agg(tc_promedio=("tc", "mean"), meses_tc=("tc", "count")))
    incompletos = trimestral[trimestral["meses_tc"] < 3]
    if len(incompletos):
        print(f"AVISO tipo de cambio: {len(incompletos)} trimestres con menos de 3 meses")
    return trimestral.drop(columns="meses_tc")


def cargar_banco_mundial():
    anual = None
    for indicador, variable in INDICADORES_BM.items():
        ruta = os.path.join(CARPETA_BM, f"{indicador}.json")
        if not os.path.exists(ruta):
            print(f"AVISO: falta {ruta}, la variable {variable} quedara vacia")
            continue
        datos = leer_json(ruta)
        registros = datos[1] if isinstance(datos, list) and len(datos) > 1 and datos[1] else []
        df = pd.DataFrame([{"anio": int(r["date"]), variable: a_flotante(r["value"])} for r in registros])
        if df.empty:
            continue
        if indicador in EN_DOLARES:
            df[variable] = df[variable] / 1e6
        anual = df if anual is None else anual.merge(df, on="anio", how="outer")
    if anual is None:
        return pd.DataFrame(columns=["trimestre"])
    # armonizacion anual -> trimestral: el mismo valor para T1, T2, T3 y T4
    trimestral = anual.loc[anual.index.repeat(4)].copy()
    trimestral["q"] = np.tile([1, 2, 3, 4], len(anual))
    trimestral["trimestre"] = trimestral["anio"].astype(str) + "T" + trimestral["q"].astype(str)
    return trimestral.drop(columns=["anio", "q"])


def cargar_mef(tipo_cambio):
    """
    Los boletines antiguos reportan saldos en millones de US$ y los recientes en millones
    de S/ (columna unidad_saldos de 02_scraping_web.py). Para que el saldo sea comparable
    se pasa todo a soles con el tipo de cambio promedio del trimestre (BCRP). Los
    porcentajes por moneda, la vida media y el costo no dependen de la unidad.
    """
    if not os.path.exists(ARCHIVO_MEF):
        raise FileNotFoundError("Falta la salida del parseo del MEF: corre 02_scraping_web.py")
    mef = pd.read_csv(ARCHIVO_MEF)
    if "unidad_saldos" not in mef.columns:
        raise ValueError("La salida del MEF no tiene la columna unidad_saldos: vuelve a correr 02_scraping_web.py")
    columnas = ["trimestre", "unidad_saldos", "saldo_total_mef", "vida_media", "duracion", "reprecio_medio",
                "costo_promedio", "pct_soles", "pct_dolares", "pct_euros", "pct_otras_monedas"]
    mef = mef[columnas].drop_duplicates(subset="trimestre", keep="last")
    for c in columnas[2:]:
        mef[c] = pd.to_numeric(mef[c], errors="coerce")
    mef = mef.merge(tipo_cambio, on="trimestre", how="left")
    en_usd = mef["unidad_saldos"].eq("USD")
    mef.loc[en_usd, "saldo_total_mef"] = mef.loc[en_usd, "saldo_total_mef"] * mef.loc[en_usd, "tc_promedio"]
    sin_unidad = mef["unidad_saldos"].isna() | mef["unidad_saldos"].eq("")
    mef.loc[sin_unidad, "saldo_total_mef"] = np.nan      # unidad desconocida: no se adivina
    print(f"MEF: {en_usd.sum()} boletines en US$ convertidos a S/; {sin_unidad.sum()} sin unidad detectada (saldo vacio)")
    mef["saldo_total_mef"] = mef["saldo_total_mef"] / 1000   # millones -> miles de millones de S/
    mef = mef.rename(columns={"saldo_total_mef": "saldo_deuda_mef_mmsoles"})
    return mef.drop(columns=["unidad_saldos", "tc_promedio"])


def rejilla_trimestral():
    """Lista completa de trimestres de la ventana, para que ninguno se pierda en la union."""
    periodos = pd.period_range(TRIMESTRE_INICIO.replace("T", "Q"), TRIMESTRE_CORTE.replace("T", "Q"), freq="Q")
    return pd.DataFrame({"trimestre": [f"{p.year}T{p.quarter}" for p in periodos]})


def reportar_atipicos(panel, columnas):
    """Regla de Tukey (1.5 x RIQ). Solo se reportan: en series de deuda los saltos suelen ser reales."""
    print("\nValores atipicos (regla 1.5 x RIQ, solo informativo):")
    for c in columnas:
        s = panel[c].dropna()
        if s.empty:
            continue
        q1, q3 = s.quantile([0.25, 0.75])
        riq = q3 - q1
        fuera = panel.loc[(panel[c] < q1 - 1.5 * riq) | (panel[c] > q3 + 1.5 * riq), "trimestre"].tolist()
        if fuera:
            print(f"   {c}: {len(fuera)} ({', '.join(fuera[:6])}{'...' if len(fuera) > 6 else ''})")


def main():
    if not os.path.isdir("datos_crudos"):
        raise SystemExit("No estoy en la carpeta del proyecto: corre primero 00_montar_drive.py")
    os.makedirs("datos_procesados", exist_ok=True)

    panel = rejilla_trimestral()
    panel = panel.merge(cargar_bcrp_trimestral(), on="trimestre", how="left")
    tipo_cambio = cargar_bcrp_tipo_cambio()
    panel = panel.merge(tipo_cambio, on="trimestre", how="left")
    panel = panel.merge(cargar_banco_mundial(), on="trimestre", how="left")
    panel = panel.merge(cargar_mef(tipo_cambio), on="trimestre", how="left")

    # Variables derivadas
    panel["participacion_externa_pct"] = 100 * panel["deuda_externa_pbi"] / panel["deuda_publica_pbi"]
    panel["participacion_cp_interna_pct"] = 100 * panel["deuda_interna_cp_pbi"] / panel["deuda_interna_pbi"]
    panel["pct_moneda_extranjera"] = 100 - panel["pct_soles"]

    # Columnas de identificacion
    panel.insert(1, "anio", panel["trimestre"].str[:4].astype(int))
    panel.insert(2, "q", panel["trimestre"].str[-1].astype(int))

    # Control: externa + interna debe ser igual (o casi) a la deuda total
    dif = (panel["deuda_externa_pbi"] + panel["deuda_interna_pbi"] - panel["deuda_publica_pbi"]).abs()
    print(f"\nControl externa + interna = total: diferencia maxima {dif.max():.2f} puntos del PBI")

    print("\nDatos faltantes por variable (trimestres sin dato):")
    for c, n in panel.isna().sum().items():
        if n:
            print(f"   {c}: {n}")
    reportar_atipicos(panel, ["deuda_publica_pbi", "tc_promedio", "vida_media", "costo_promedio", "pct_soles"])

    panel = panel.round(4)
    panel.to_csv(SALIDA, index=False, encoding="utf-8")
    with open(SALIDA, "rb") as f:
        hash_sha256 = hashlib.sha256(f.read()).hexdigest()
    with open(SALIDA_HASH, "w", encoding="utf-8") as f:
        f.write(f"{hash_sha256}  {os.path.basename(SALIDA)}\n")

    print(f"\nPanel guardado en {SALIDA}")
    print(f"Filas: {len(panel)} | Columnas: {panel.shape[1]}")
    print(f"Columnas: {list(panel.columns)}")
    print("\nUltimos 4 trimestres (variables principales):")
    print(panel[["trimestre", "deuda_publica_pbi", "deuda_externa_pbi", "deuda_interna_pbi",
                 "tc_promedio", "vida_media", "costo_promedio", "pct_soles"]].tail(4).to_string(index=False))
    print(f"\nHash SHA-256 (copialo al README.md):\n{hash_sha256}")


if __name__ == "__main__":
    main()
