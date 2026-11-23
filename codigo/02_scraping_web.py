# Nombres y apellidos: Chinte Ponce, Joseph Alexander
# Codigo de matricula: 2024200494M
# Tema: N.86 - Estructura y sostenibilidad de la deuda publica peruana
# Fecha de extraccion: (completar con la fecha real de ejecucion)

"""
VIA 2 - SCRAPING + DESCARGA PROGRAMATICA (numeral 2.4.3).

Fuente: boletines trimestrales "Reporte Trimestral - Analisis de la Deuda Publica
Bruta" del MEF (Direccion General del Tesoro Publico), 2010T1 a 2025T4.

NOTA (ver incidencias_fuente.md): la pagina indice del MEF
https://www.mef.gob.pe/es/reporte-trimestral-de-deuda-publica responde a programas
con un desafio antibots (Incapsula) y la etiqueta noindex,nofollow. No se intenta
evadirlo. Se usan dos rutas oficiales que SI admiten acceso automatizado:

Paso 1. Revisa robots.txt de cada dominio usado.
Paso 2a. SCRAPING de la pagina oficial del MEF en la plataforma del Estado (gob.pe):
        https://www.gob.pe/institucion/mef/informes-publicaciones/tipos/2-boletin
        Selector: <a> cuyo texto contiene "Boletin de Deuda" (fecha en el titulo),
        paginacion con ?sheet=N, y dentro de cada boletin el <a> al PDF en
        cdn.www.gob.pe cuyo nombre termina en "-esp" (version en espaniol).
        Cubre los boletines desde junio de 2024.
Paso 2b. DESCARGA PROGRAMATICA de los boletines anteriores desde su URL oficial en
        https://www.mef.gob.pe/contenidos/deuda_publ/documentos/ (ruta sin desafio
        antibots). El nombre sigue un patron fijo con la fecha de corte:
        Boletin_Deuda8_DDMMAAAA.pdf (2010-2023) y Boletin_Deuda64_31032024_esp.pdf.
Paso 3. Descarga cada PDF sin modificarlo a datos_crudos/mef_pdf/ (pausa de 1 s,
        User-Agent identificable). Si el PDF ya existe, no lo vuelve a pedir.
        Registra URL, codigo HTTP, tamanio y hash en un manifiesto.
Paso 4. Parsea cada PDF con pdfplumber y extrae, de la tabla "Saldo de deuda bruta":
        vida media, duracion, reprecio medio y tasa equivalente (costo promedio);
        y de la tabla por monedas: saldos en soles, dolares, euros, yenes y otras.
        Resultado: datos_crudos/mef_extraccion_pdf_2024200494M.csv (salida directa
        del parseo, sin ediciones manuales).

En Colab, antes de correrlo:  !pip install -q pdfplumber
"""

import os
import re
import csv
import time
import hashlib
import unicodedata
from datetime import date, datetime
from urllib.parse import urljoin, urlparse
from urllib import robotparser

import requests
import pdfplumber
from bs4 import BeautifulSoup

# ----------------------------------------------------------------------
# PARAMETROS CONGELADOS (numeral 2.4.5)
# ----------------------------------------------------------------------
FECHA_INICIO = date(2010, 3, 31)    # primer boletin trimestral publicado
FECHA_CORTE = date(2025, 12, 31)    # ultimo trimestre del estudio

URL_LISTADO = "https://www.gob.pe/institucion/mef/informes-publicaciones/tipos/2-boletin"
URL_DOCUMENTOS_MEF = "https://www.mef.gob.pe/contenidos/deuda_publ/documentos/"
MAX_PAGINAS_LISTADO = 10
USER_AGENT = "UNCP-FinanzasI-055D-2024200494M/2.0 (uso academico; e_2024200494M@uncp.edu.pe)"
PAUSA_SEG = 1.0
PAUSA_MEF_SEG = 5.0      # mef.gob.pe tiene proteccion antibots: se consulta mas despacio

# True = no consulta ningun portal: vuelve a parsear los PDF que ya estan en
# datos_crudos/mef_pdf/ segun el manifiesto. Sirve para reproducir el parseo
# sin volver a pedir archivos. False = rastreo + descarga + parseo.
SOLO_PARSEO = False

CARPETA_PDF = os.path.join("datos_crudos", "mef_pdf")
CARPETA_HTML = os.path.join("datos_crudos", "gobpe_html")
ARCHIVO_MANIFIESTO = os.path.join("datos_crudos", "mef_manifiesto_descargas.csv")
ARCHIVO_SALIDA = os.path.join("datos_crudos", "mef_extraccion_pdf_2024200494M.csv")
ARCHIVO_DIAGNOSTICO = os.path.join("datos_crudos", "mef_diagnostico_parseo.txt")
ARCHIVO_LOG = "log_ejecucion.txt"

MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
         "julio": 7, "agosto": 8, "setiembre": 9, "septiembre": 9, "octubre": 10,
         "noviembre": 11, "diciembre": 12}
MONEDAS = {"soles": "saldo_soles", "dolares": "saldo_dolares", "euros": "saldo_euros",
           "yenes": "saldo_yenes", "otras": "saldo_otras"}
CAMPOS_SALIDA = ["fecha_corte", "trimestre", "archivo", "unidad_saldos",
                 "saldo_total_mef", "vida_media", "duracion", "reprecio_medio", "costo_promedio",
                 "saldo_soles", "saldo_dolares", "saldo_euros", "saldo_yenes", "saldo_otras",
                 "pct_soles", "pct_dolares", "pct_euros", "pct_otras_monedas",
                 "campos_encontrados"]

# Numeros: miles separados por espacio ("153 471") y decimales con coma ("13,38")
RE_DECIMAL = re.compile(r"(?<![\d,])(\d{1,2},\d{2})(?!\d)")
RE_ENTERO_COLUMNA = re.compile(r"^-?\d{1,3}(?: \d{3})*$")


def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def sin_tildes(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def normalizar_espacios(linea):
    """Convierte espacios especiales (no separables, finos) en espacios normales."""
    for ch in (" ", " ", " ", " "):
        linea = linea.replace(ch, " ")
    return linea


def a_numero(texto):
    """'153 471' -> 153471.0 ; '13,38' -> 13.38"""
    limpio = texto.replace(" ", "").replace(",", ".")
    try:
        return float(limpio)
    except ValueError:
        return None


# ----------------------------------------------------------------------
# Paso 1: robots.txt
# ----------------------------------------------------------------------
def revisar_robots(url, log):
    partes = urlparse(url)
    rp = robotparser.RobotFileParser()
    rp.set_url(f"{partes.scheme}://{partes.netloc}/robots.txt")
    try:
        rp.read()
        permitido = rp.can_fetch(USER_AGENT, url)
    except Exception as e:  # si no hay robots.txt legible se registra y se continua
        log.append(f"{ahora()} | robots.txt {partes.netloc} | no legible ({e}) | se asume permitido")
        print(f"[AVISO] robots.txt de {partes.netloc} no legible: {e}")
        return True
    log.append(f"{ahora()} | robots.txt {partes.netloc} | ruta {partes.path} | permitido={permitido}")
    print(f"[robots.txt] {partes.netloc}{partes.path[:50]} -> permitido={permitido}")
    return permitido


# ----------------------------------------------------------------------
# Paso 2: rastreo de gob.pe y URL oficiales del MEF
# ----------------------------------------------------------------------
def fecha_desde_texto(texto, href):
    """Saca la fecha de corte del texto del enlace ('Al 31 de Diciembre de 2025') o del nombre del archivo."""
    t = sin_tildes(texto).lower()
    m = re.search(r"al\s+(\d{1,2})\s+de\s+([a-z]+)\s+(?:del?\s+)?(\d{4})", t)
    if m and m.group(2) in MESES:
        return date(int(m.group(3)), MESES[m.group(2)], int(m.group(1)))
    m = re.search(r"(\d{2})(\d{2})(\d{4})\.pdf", href, re.IGNORECASE)          # ..._30062023.pdf
    if m:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    m = re.search(r"al-(\d{2})-(\d{2})-(\d{4})", href)                        # ...-al-31-12-2025-esp.pdf
    if m:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    return None


def obtener(url, log, etiqueta):
    """GET con User-Agent identificable y pausa posterior."""
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=120)
    log.append(f"{ahora()} | {etiqueta} | HTTP {resp.status_code} | {len(resp.content)} bytes | {url}")
    time.sleep(PAUSA_SEG)
    return resp


def listar_boletines_gobpe(log):
    """Paso 2a: recorre el listado de gob.pe (?sheet=1, 2, ...) y entra a cada boletin de deuda."""
    os.makedirs(CARPETA_HTML, exist_ok=True)
    fichas = {}
    for n in range(1, MAX_PAGINAS_LISTADO + 1):
        url = URL_LISTADO if n == 1 else f"{URL_LISTADO}?sheet={n}"
        resp = obtener(url, log, f"gob.pe listado pagina {n}")
        if resp.status_code != 200:
            break
        with open(os.path.join(CARPETA_HTML, f"listado_pagina_{n}.html"), "wb") as f:
            f.write(resp.content)                     # evidencia: la pagina tal como se rastreo
        sopa = BeautifulSoup(resp.text, "html.parser")
        nuevos = 0
        for a in sopa.select("a[href*='/informes-publicaciones/']"):
            titulo = a.get_text(" ", strip=True)
            if "boletin de deuda" not in sin_tildes(titulo).lower():
                continue
            fecha = fecha_desde_texto(titulo, a["href"])
            if fecha and fecha not in fichas:
                fichas[fecha] = urljoin(URL_LISTADO, a["href"])
                nuevos += 1
        print(f"   pagina {n}: {nuevos} boletines nuevos")
        if nuevos == 0:                               # no hay mas paginas con boletines
            break

    boletines = {}
    for fecha, url_ficha in sorted(fichas.items()):
        if not (FECHA_INICIO <= fecha <= FECHA_CORTE):
            continue
        resp = obtener(url_ficha, log, f"gob.pe ficha {fecha}")
        sopa = BeautifulSoup(resp.text, "html.parser")
        pdfs = [a["href"] for a in sopa.select("a[href*='cdn.www.gob.pe']") if ".pdf" in a["href"].lower()]
        espanol = [h for h in pdfs if "-esp" in h.lower()] or [h for h in pdfs if "eng" not in h.lower()]
        if espanol:
            boletines[fecha] = [espanol[0]]
        else:
            print(f"[AVISO] {fecha}: la ficha no tiene PDF en espaniol")
    print(f"[OK] gob.pe: {len(boletines)} boletines dentro de {FECHA_INICIO} a {FECHA_CORTE}")
    return boletines


def fines_de_trimestre(inicio, fin):
    """Fechas de corte trimestrales: 31-03, 30-06, 30-09 y 31-12 de cada anio."""
    fechas = []
    for anio in range(inicio.year, fin.year + 1):
        for mes, dia in ((3, 31), (6, 30), (9, 30), (12, 31)):
            d = date(anio, mes, dia)
            if inicio <= d <= fin:
                fechas.append(d)
    return fechas


def urls_documentos_mef(fecha):
    """Paso 2b: URL oficial de un boletin antiguo segun el patron fijo de nombres del MEF."""
    ddmmaaaa = fecha.strftime("%d%m%Y")
    if fecha == date(2024, 3, 31):
        return [URL_DOCUMENTOS_MEF + "Boletin_Deuda64_31032024_esp.pdf"]
    return [URL_DOCUMENTOS_MEF + f"Boletin_Deuda8_{ddmmaaaa}.pdf",
            URL_DOCUMENTOS_MEF + f"Boletin_Deuda8_{ddmmaaaa}.PDF"]   # 31-12-2023 usa extension en mayusculas


def armar_lista_boletines(log):
    boletines = listar_boletines_gobpe(log)
    faltantes = [f for f in fines_de_trimestre(FECHA_INICIO, FECHA_CORTE) if f not in boletines]
    for fecha in faltantes:
        boletines[fecha] = urls_documentos_mef(fecha)
    print(f"[OK] Total a descargar: {len(boletines)} boletines "
          f"({len(boletines) - len(faltantes)} desde gob.pe y {len(faltantes)} desde mef.gob.pe/contenidos)")
    return dict(sorted(boletines.items()))


# ----------------------------------------------------------------------
# Paso 3: descarga programatica
# ----------------------------------------------------------------------
def es_desafio_antibots(contenido):
    """La respuesta de Incapsula es una pagina HTML pequenia con un script '_Incapsula_Resource'."""
    return b"_Incapsula_Resource" in contenido[:2000]


def descargar_boletines(boletines, log):
    os.makedirs(CARPETA_PDF, exist_ok=True)
    filas_manifiesto = []
    bloqueado = False          # si el MEF responde con el desafio antibots, no se insiste en esta ejecucion
    for fecha, candidatas in boletines.items():
        ruta = os.path.join(CARPETA_PDF, f"boletin_deuda_{fecha.isoformat()}.pdf")
        url_usada, codigo = candidatas[0], ""
        es_mef = "mef.gob.pe" in candidatas[0]
        if os.path.exists(ruta) and os.path.getsize(ruta) > 0:
            estado = "ya_descargado"
        elif es_mef and bloqueado:
            estado = "no_intentado: desafio antibots activo (ver incidencias_fuente.md)"
        else:
            estado = "error: ninguna URL devolvio un PDF"
            pausa = PAUSA_MEF_SEG if es_mef else PAUSA_SEG
            for url in candidatas:                       # se prueba cada URL candidata en orden
                try:
                    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=120)
                    codigo = resp.status_code
                    time.sleep(pausa)
                    if resp.status_code == 200 and resp.content.startswith(b"%PDF"):
                        with open(ruta, "wb") as f:
                            f.write(resp.content)
                        url_usada, estado = url, "descargado"
                        break
                    if es_desafio_antibots(resp.content):
                        bloqueado = True
                        estado = "bloqueado: desafio antibots (Incapsula)"
                        print(f"[BLOQUEO] {fecha}: el MEF respondio con su desafio antibots. "
                              "No se insiste: se registra y se omiten los demas PDF de mef.gob.pe en esta ejecucion.")
                        break
                except requests.exceptions.RequestException as e:
                    estado = f"error: {e}"
                    time.sleep(pausa)
            if estado not in ("descargado",) and not estado.startswith("bloqueado"):
                print(f"[ERROR] {fecha}: {estado} (ultimo HTTP {codigo})")
        tamano = os.path.getsize(ruta) if os.path.exists(ruta) else 0
        sha = ""
        if tamano:
            with open(ruta, "rb") as fpdf:
                sha = hashlib.sha256(fpdf.read()).hexdigest()
        filas_manifiesto.append({"fecha_corte": fecha.isoformat(), "url": url_usada, "archivo": os.path.basename(ruta),
                                 "http": codigo, "estado": estado, "bytes": tamano, "sha256": sha})
        log.append(f"{ahora()} | MEF PDF {fecha} | HTTP {codigo} | {estado} | {tamano} bytes | {url_usada}")
    with open(ARCHIVO_MANIFIESTO, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=list(filas_manifiesto[0].keys()))
        escritor.writeheader()
        escritor.writerows(filas_manifiesto)
    ok = sum(1 for r in filas_manifiesto if r["bytes"] > 0)
    print(f"[OK] PDFs disponibles en {CARPETA_PDF}: {ok} de {len(filas_manifiesto)}")
    if bloqueado:
        pendientes = [r["fecha_corte"] for r in filas_manifiesto if not r["bytes"]]
        print(f"[PENDIENTE] {len(pendientes)} boletines sin descargar por el desafio antibots "
              f"({pendientes[0]} a {pendientes[-1]}). Vuelve a correr este script mas tarde: "
              "los PDF ya descargados no se piden de nuevo.")
    return filas_manifiesto


# ----------------------------------------------------------------------
# Paso 4: parseo de cada PDF
# ----------------------------------------------------------------------
def lineas_del_pdf(ruta):
    """
    Reconstruye cada fila de las tablas usando la POSICION de cada palabra en la pagina.
    En estos boletines los miles se separan con un espacio ("265 827"), igual que las
    columnas en el texto plano, asi que el texto plano es ambiguo. Con las coordenadas:
    si la distancia entre dos palabras es pequenia (un espacio) son parte del mismo dato;
    si es grande, son columnas distintas. Las columnas se unen con 2 espacios.
    """
    lineas = []
    with pdfplumber.open(ruta) as pdf:
        for pagina in pdf.pages:
            palabras = pagina.extract_words(x_tolerance=1.5, y_tolerance=2, keep_blank_chars=False)
            palabras.sort(key=lambda w: (round(w["top"], 1), w["x0"]))
            filas, actual, tope = [], [], None
            for w in palabras:                       # agrupar palabras de la misma altura
                if actual and abs(w["top"] - tope) > 2.5:
                    filas.append(actual)
                    actual = []
                if not actual:
                    tope = w["top"]
                actual.append(w)
            if actual:
                filas.append(actual)
            for fila in filas:
                fila.sort(key=lambda w: w["x0"])
                piezas, previa = [fila[0]["text"]], fila[0]
                for w in fila[1:]:
                    separacion = w["x0"] - previa["x1"]
                    alto = max(previa["bottom"] - previa["top"], 1)
                    if separacion <= 0.45 * alto:     # del tamanio de un espacio: mismo dato
                        piezas[-1] += " " + w["text"]
                    else:                             # hueco grande: nueva columna
                        piezas.append(w["text"])
                    previa = w
                lineas.append(normalizar_espacios("  ".join(piezas)))
    return lineas


def buscar_indicadores_total(lineas):
    """
    Fila 'Total' de la tabla 'Saldo de deuda bruta'. Sus decimales van en este orden:
    vida media (anios), duracion (anios), reprecio medio (anios), tasa equivalente (%).
    La fila TOTAL de la tabla por monedas no tiene decimales, asi que no se confunde.
    """
    for linea in lineas:
        if not re.match(r"^\s*total\b", sin_tildes(linea).lower()):
            continue
        decimales = [a_numero(d) for d in RE_DECIMAL.findall(linea)]
        if len(decimales) < 4:
            continue
        vida, dur, rep, tasa = decimales[:4]
        if 2 <= vida <= 30 and 0.5 <= tasa <= 15:        # control de coherencia
            columnas = [c.strip() for c in re.split(r"\s{2,}", linea.strip()) if c.strip()]
            saldo = next((a_numero(c) for c in columnas[1:] if RE_ENTERO_COLUMNA.match(c)), None)
            return {"saldo_total_mef": saldo, "vida_media": vida, "duracion": dur,
                    "reprecio_medio": rep, "costo_promedio": tasa}
    return {}


def buscar_saldos_por_moneda(lineas):
    """
    Tabla por monedas: 'Soles  153 471  0  15 046  15 046'. Se toma la primera cifra tras la etiqueta.
    Se descarta cuando a la etiqueta le siguen decimales (es otra tabla, p. ej. 'Otras 8 217 ... 4,49').
    """
    saldos = {}
    for linea in lineas:
        columnas = [c.strip() for c in re.split(r"\s{2,}", linea.strip()) if c.strip()]
        for i, col in enumerate(columnas):
            m = re.match(r"^(?:nuevos\s+)?(soles|dolares|euros|yenes|otras)(?:\s+(-?\d{1,3}(?: \d{3})*))?$",
                         sin_tildes(col).lower())
            if not m:
                continue
            clave = MONEDAS[m.group(1)]
            if clave in saldos:
                continue
            siguientes = columnas[i + 1:i + 4]
            if any("," in s for s in siguientes):
                continue
            if m.group(2):                                   # cifra pegada a la etiqueta
                valor = a_numero(m.group(2))
            elif siguientes and RE_ENTERO_COLUMNA.match(siguientes[0]):
                valor = a_numero(siguientes[0])
            else:
                continue
            if valor is not None and valor >= 0:
                saldos[clave] = valor
    return saldos


def detectar_unidad_saldos(lineas):
    """
    Los boletines antiguos expresan los saldos en millones de US$ ("US$ Mill.") y los
    recientes en millones de soles ("S/ Mill."). Se lee la unidad del encabezado de la
    tabla "Descomposicion de la variacion del saldo adeudado". Los porcentajes por
    moneda no cambian con la unidad; el saldo total si (se convierte en 03_limpieza).
    """
    for linea in lineas:
        t = sin_tildes(linea).lower().replace(" ", "")
        if "saldoadeudado" in t:
            if "us$" in t:
                return "USD"
            if "s/" in t:
                return "PEN"
    for linea in lineas:                      # respaldo: cualquier rotulo de unidad
        t = sin_tildes(linea).lower().replace(" ", "")
        if "us$mill" in t or "us$millones" in t:
            return "USD"
        if "s/mill" in t or "millonesdes/" in t:
            return "PEN"
    return ""


def parsear_boletin(ruta, fecha):
    lineas = lineas_del_pdf(ruta)
    fila = {"fecha_corte": fecha.isoformat(),
            "trimestre": f"{fecha.year}T{(fecha.month - 1) // 3 + 1}",
            "archivo": os.path.basename(ruta)}
    fila["unidad_saldos"] = detectar_unidad_saldos(lineas)
    fila.update(buscar_indicadores_total(lineas))
    fila.update(buscar_saldos_por_moneda(lineas))

    if "saldo_soles" in fila and "saldo_dolares" in fila:
        total = sum(fila.get(k, 0) or 0 for k in MONEDAS.values())
        fila["pct_soles"] = round(100 * fila["saldo_soles"] / total, 2)
        fila["pct_dolares"] = round(100 * fila["saldo_dolares"] / total, 2)
        # Algunos boletines antiguos (p. ej. 2010) no tienen fila "Euros": la deuda en euros
        # va dentro de "Otras". En ese caso pct_euros queda vacio (no 0), porque no se reporto.
        fila["pct_euros"] = round(100 * fila["saldo_euros"] / total, 2) if "saldo_euros" in fila else ""
        otras = (fila.get("saldo_yenes") or 0) + (fila.get("saldo_otras") or 0)
        fila["pct_otras_monedas"] = round(100 * otras / total, 2)

    claves = ["vida_media", "costo_promedio", "saldo_soles", "saldo_dolares"]
    fila["campos_encontrados"] = f"{sum(k in fila for k in claves)}/4"
    return fila, lineas


def escribir_diagnostico(muestras):
    """Guarda las lineas clave de los PDFs donde el parseo fallo, para revisarlas."""
    palabras = ("total", "soles", "dolares", "euros", "yenes", "otras", "vida", "media",
                "tasa", "equivalente", "saldo de deuda")
    with open(ARCHIVO_DIAGNOSTICO, "w", encoding="utf-8") as f:
        for fecha, lineas in muestras:
            f.write(f"\n===== {fecha} =====\n")
            for linea in lineas:
                if any(p in sin_tildes(linea).lower() for p in palabras):
                    f.write(repr(linea[:220]) + "\n")
    print(f"[DIAGNOSTICO] Lineas clave guardadas en {ARCHIVO_DIAGNOSTICO}")


def parsear_todos(manifiesto, log):
    filas, fallidos = [], []
    for reg in manifiesto:
        if not reg["bytes"]:
            continue
        fecha = date.fromisoformat(reg["fecha_corte"])
        ruta = os.path.join(CARPETA_PDF, reg["archivo"])
        try:
            fila, lineas = parsear_boletin(ruta, fecha)
        except Exception as e:
            print(f"[ERROR] parseo {reg['archivo']}: {e}")
            log.append(f"{ahora()} | parseo {reg['archivo']} | error {e}")
            continue
        filas.append(fila)
        if fila["campos_encontrados"] != "4/4":
            fallidos.append((fila["fecha_corte"], lineas))
        print(f"  {fila['trimestre']}  unidad={fila['unidad_saldos'] or '?'}  vida={fila.get('vida_media')}  costo={fila.get('costo_promedio')}"
              f"  soles={fila.get('saldo_soles')}  dolares={fila.get('saldo_dolares')}  [{fila['campos_encontrados']}]")

    with open(ARCHIVO_SALIDA, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=CAMPOS_SALIDA)
        escritor.writeheader()
        for fila in filas:
            escritor.writerow({k: fila.get(k, "") for k in CAMPOS_SALIDA})

    completos = sum(1 for r in filas if r["campos_encontrados"] == "4/4")
    log.append(f"{ahora()} | parseo MEF | {len(filas)} boletines | {completos} completos | {ARCHIVO_SALIDA}")
    print(f"\n[OK] Parseo: {completos} de {len(filas)} boletines con los 4 campos clave -> {ARCHIVO_SALIDA}")
    if fallidos:
        # se guardan hasta 4 casos repartidos en el tiempo
        paso = max(1, len(fallidos) // 4)
        escribir_diagnostico(fallidos[::paso][:4])


def main():
    if not os.path.isdir("datos_crudos"):
        raise SystemExit("No estoy en la carpeta del proyecto: corre primero 00_montar_drive.py")
    log = [f"=== 02_scraping_web iniciada: {ahora()} ===",
           f"Parametros: boletines desde {FECHA_INICIO} hasta {FECHA_CORTE}"]
    print(log[0])

    if SOLO_PARSEO:
        print("Modo SOLO_PARSEO: no se consulta ningun portal; se parsean los PDF ya descargados.")
        with open(ARCHIVO_MANIFIESTO, newline="", encoding="utf-8") as f:
            manifiesto = [dict(r, bytes=int(r["bytes"] or 0)) for r in csv.DictReader(f)]
        parsear_todos(manifiesto, log)
        log.append(f"=== 02_scraping_web (solo parseo) finalizada: {ahora()} ===")
        with open(ARCHIVO_LOG, "a", encoding="utf-8") as f:
            f.write("\n".join(log) + "\n\n")
        print("\nListo. Siguiente paso: 03_limpieza_datos.py")
        return

    for url in (URL_LISTADO, URL_DOCUMENTOS_MEF, "https://cdn.www.gob.pe/uploads/document/file/"):
        if not revisar_robots(url, log):
            raise SystemExit("robots.txt prohibe esta ruta: aplicar el procedimiento de sustitucion (numeral 2.4.3) "
                             "y registrarlo en incidencias_fuente.md")

    print("\n--- Rastreo del listado en gob.pe ---")
    boletines = armar_lista_boletines(log)
    print("\n--- Descarga de los PDF ---")
    manifiesto = descargar_boletines(boletines, log)
    parsear_todos(manifiesto, log)

    log.append(f"=== 02_scraping_web finalizada: {ahora()} ===")
    with open(ARCHIVO_LOG, "a", encoding="utf-8") as f:
        f.write("\n".join(log) + "\n\n")
    print("\nListo. Siguiente paso: 03_limpieza_datos.py")


if __name__ == "__main__":
    main()
