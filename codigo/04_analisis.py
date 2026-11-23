# Nombres y apellidos: Chinte Ponce, Joseph Alexander
# Codigo de matricula: 2024200494M
# Tema: N.86 - Estructura y sostenibilidad de la deuda publica peruana
# Fecha de extraccion: (completar con la fecha real de ejecucion)

"""
Genera, SOLO a partir de datos_procesados_2024200494M.csv, las tablas, la
estimacion y las figuras del articulo. Todo se guarda en salidas/.

  Tabla 1  promedios por subperiodo (2000-2009, 2010-2019, 2020-2025)
  Tabla 2  correlaciones de Pearson, 2010T1-2025T4 (periodo con datos del MEF)
  Tabla 3  regresion MCO: costo promedio de la deuda ~ % en moneda extranjera + vida media + tipo de cambio
  Figura 1 deuda publica interna y externa (% del PBI), 2000-2025          [BCRP]
  Figura 2 composicion de la deuda por moneda (%), 2010-2025               [MEF]
  Figura 3 vida media (anios) y costo promedio (%), 2010-2025              [MEF]
  Figura 4 pago de intereses como % de los ingresos del gobierno            [Banco Mundial]

Cada fuente aparece en al menos un resultado (numeral 2.4.1).
"""

import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

ENTRADA = os.path.join("datos_procesados", "datos_procesados_2024200494M.csv")
CARPETA_SALIDAS = "salidas"

# Paleta y tinta (fondo claro). Colores categoricos en orden fijo, nunca ciclados.
AZUL, NARANJA, AGUAMARINA, AMARILLO = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
FONDO, TINTA, TINTA_2, TENUE = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRILLA, EJE = "#e1e0d9", "#c3c2b7"

plt.rcParams.update({
    "figure.facecolor": FONDO, "axes.facecolor": FONDO, "savefig.facecolor": FONDO,
    "axes.edgecolor": EJE, "axes.labelcolor": TINTA_2, "axes.titlecolor": TINTA,
    "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "axes.labelsize": 10, "axes.grid": True, "axes.axisbelow": True,
    "grid.color": GRILLA, "grid.linewidth": 0.6, "xtick.color": TENUE, "ytick.color": TENUE,
    "xtick.labelsize": 9, "ytick.labelsize": 9, "legend.frameon": False, "legend.fontsize": 9,
    "font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False,
})


def fecha_trimestre(panel):
    """Fecha de fin de trimestre para el eje X."""
    return pd.PeriodIndex(panel["trimestre"].str.replace("T", "Q"), freq="Q").to_timestamp(how="end")


def formatear_eje_fecha(ax):
    """Etiquetas de fecha compactas (anio y, si cabe, mes) en lugar de '2024-07'."""
    localizador = mdates.AutoDateLocator(minticks=4, maxticks=9)
    ax.xaxis.set_major_locator(localizador)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(localizador))


def rango_anios(sub):
    a0, a1 = int(sub["anio"].min()), int(sub["anio"].max())
    return str(a0) if a0 == a1 else f"{a0}-{a1}"


def eje_y_con_rango_minimo(ax, serie, rango_minimo):
    """Evita que el eje se 'acerque' tanto que variaciones pequenias parezcan enormes."""
    s = serie.dropna()
    if s.empty:
        return
    centro, amplitud = (s.max() + s.min()) / 2, max(s.max() - s.min(), rango_minimo)
    ax.set_ylim(centro - amplitud * 0.6, centro + amplitud * 0.6)


def guardar(fig, nombre):
    ruta = os.path.join(CARPETA_SALIDAS, nombre)
    fig.savefig(ruta, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"[Figura] {ruta}")


def nota_fuente(fig, texto):
    fig.text(0.01, -0.02, texto, fontsize=8, color=TENUE, ha="left", va="top")


# ----------------------------------------------------------------------
# Tablas
# ----------------------------------------------------------------------
MIN_OBS_SUBPERIODO = 4   # al menos un anio de trimestres para promediar un subperiodo


def tabla1_subperiodos(panel):
    variables = {
        "deuda_publica_pbi": "Deuda pública (% PBI)",
        "deuda_externa_pbi": "Deuda externa (% PBI)",
        "deuda_interna_pbi": "Deuda interna (% PBI)",
        "participacion_externa_pct": "Deuda externa (% del total)",
        "tc_promedio": "Tipo de cambio (S/ por US$)",
        "pct_soles": "Deuda en soles (%)",
        "vida_media": "Vida media (años)",
        "costo_promedio": "Costo promedio (%)",
        "intereses_pct_ingresos_bm": "Intereses (% ingresos)",
    }
    cortes = pd.cut(panel["anio"], bins=[1999, 2009, 2019, 2025], labels=["2000-2009", "2010-2019", "2020-2025"])
    grupos = panel.groupby(cortes, observed=True)[list(variables)]
    tabla = grupos.mean().T.round(2)
    n_obs = grupos.count().T
    # Un promedio de subperiodo con muy pocos trimestres no representa al subperiodo:
    # se deja vacio y el dato puntual se reporta aparte en el texto.
    tabla = tabla.where(n_obs >= MIN_OBS_SUBPERIODO)
    tabla.index = [variables[v] for v in tabla.index]
    n_obs.index = tabla.index
    n_obs.to_csv(os.path.join(CARPETA_SALIDAS, "tabla1b_observaciones_subperiodo.csv"), encoding="utf-8")
    ruta = os.path.join(CARPETA_SALIDAS, "tabla1_promedios_subperiodo.csv")
    tabla.to_csv(ruta, encoding="utf-8")
    print(f"[Tabla 1] {ruta}\n{tabla.to_string()}\n")
    print(f"[Tabla 1b] trimestres con dato por subperiodo:\n{n_obs.to_string()}\n")


MIN_OBS_CORRELACION = 12   # menos observaciones dan correlaciones poco confiables


def tabla2_correlaciones(panel):
    """
    Correlaciones de Pearson por pares (cada par usa los trimestres en que ambas
    variables tienen dato), porque las fuentes cubren periodos distintos. Los pares
    con menos de MIN_OBS_CORRELACION observaciones quedan vacios.
    """
    columnas = ["deuda_publica_pbi", "participacion_externa_pct", "participacion_cp_interna_pct",
                "bonos_no_residentes_pbi", "tc_promedio", "intereses_pct_ingresos_bm",
                "pct_moneda_extranjera", "vida_media", "costo_promedio"]
    datos = panel[columnas]
    corr = datos.corr(method="pearson", min_periods=MIN_OBS_CORRELACION).round(3)
    presentes = datos.notna().astype(int)
    n_pares = presentes.T @ presentes                 # trimestres con ambos datos, por par
    ruta = os.path.join(CARPETA_SALIDAS, "tabla2_correlaciones.csv")
    corr.to_csv(ruta, encoding="utf-8")
    n_pares.to_csv(os.path.join(CARPETA_SALIDAS, "tabla2b_observaciones_por_par.csv"), encoding="utf-8")
    print(f"[Tabla 2] {ruta}\n{corr.to_string()}\n")
    print(f"[Tabla 2b] observaciones por par:\n{n_pares.to_string()}\n")


def mco(y, X, nombres):
    """Minimos cuadrados ordinarios con errores estandar clasicos (sin librerias extra)."""
    X = np.column_stack([np.ones(len(X)), X])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    residuos = y - X @ beta
    n, k = X.shape
    sigma2 = residuos @ residuos / (n - k)
    varianzas = np.diag(sigma2 * np.linalg.pinv(X.T @ X))
    if np.linalg.cond(X.T @ X) > 1e10:
        print("AVISO: regresores casi colineales; interpreta los coeficientes con cuidado.")
    ee = np.sqrt(np.clip(varianzas, 0, None))
    r2 = 1 - (residuos @ residuos) / ((y - y.mean()) @ (y - y.mean()))
    return pd.DataFrame({"variable": ["constante"] + nombres, "coeficiente": beta,
                         "error_estandar": ee, "t": beta / ee}), r2, n


def tabla3_regresion(panel):
    columnas = ["costo_promedio", "pct_moneda_extranjera", "vida_media", "tc_promedio"]
    sub = panel.loc[panel["anio"] >= 2010, columnas].dropna()
    if len(sub) < 10:
        print("[Tabla 3] Muy pocas observaciones con datos del MEF; se omite la regresion.")
        return
    resultado, r2, n = mco(sub["costo_promedio"].to_numpy(), sub[columnas[1:]].to_numpy(), columnas[1:])
    resultado = resultado.round(4)
    resultado.loc[len(resultado)] = ["R2", round(r2, 4), np.nan, np.nan]
    resultado.loc[len(resultado)] = ["n", n, np.nan, np.nan]
    ruta = os.path.join(CARPETA_SALIDAS, "tabla3_regresion_costo.csv")
    resultado.to_csv(ruta, index=False, encoding="utf-8")
    print(f"[Tabla 3] {ruta}\n{resultado.to_string(index=False)}\n")


def tabla4_comparacion_mef(panel):
    """Primer vs. ultimo boletin del MEF disponible (los subperiodos con 1 dato no se promedian)."""
    variables = {"saldo_deuda_mef_mmsoles": "Saldo de deuda (miles de millones de S/)",
                 "pct_soles": "Deuda en soles (%)", "pct_moneda_extranjera": "Deuda en moneda extranjera (%)",
                 "pct_dolares": "Deuda en dólares (%)",
                 "pct_euros": "Deuda en euros (%)", "vida_media": "Vida media (años)",
                 "duracion": "Duración (años)", "costo_promedio": "Costo promedio (%)"}
    con_dato = panel[panel["pct_soles"].notna()]
    if len(con_dato) < 2:
        print("[Tabla 4] Menos de dos boletines del MEF; se omite.")
        return
    extremos = con_dato.iloc[[0, -1]].set_index("trimestre")[list(variables)].T
    extremos["cambio"] = extremos.iloc[:, 1] - extremos.iloc[:, 0]
    extremos.index = [variables[v] for v in extremos.index]
    extremos = extremos.round(2)
    ruta = os.path.join(CARPETA_SALIDAS, "tabla4_comparacion_mef.csv")
    extremos.to_csv(ruta, encoding="utf-8")
    print(f"[Tabla 4] {ruta}\n{extremos.to_string()}\n")


# ----------------------------------------------------------------------
# Figuras
# ----------------------------------------------------------------------
def figura1_interna_externa(panel):
    x = fecha_trimestre(panel)
    fig, ax = plt.subplots(figsize=(9, 4.6))
    capas = ax.stackplot(x, panel["deuda_interna_pbi"], panel["deuda_externa_pbi"],
                         colors=[AZUL, NARANJA], labels=["Deuda interna", "Deuda externa"],
                         edgecolor=FONDO, linewidth=2)
    ax.set_title("Deuda pública del Perú por origen (% del PBI), 2000-2025")
    ax.set_ylabel("% del PBI")
    ax.set_xlim(x.min(), x.max())
    ax.set_ylim(0, None)
    ax.legend(loc="upper right", ncol=2)
    ult = panel.dropna(subset=["deuda_publica_pbi"]).iloc[-1]
    x_ult = x[panel.index.get_loc(ult.name)]
    ax.plot([x_ult], [ult["deuda_publica_pbi"]], marker="o", markersize=6, color=TINTA,
            markeredgecolor=FONDO, markeredgewidth=2, zorder=5, clip_on=False)
    ax.text(0.99, 0.84, f"Total {ult['trimestre']}: {ult['deuda_publica_pbi']:.1f}% del PBI",
            transform=ax.transAxes, ha="right", va="top", fontsize=9, color=TINTA)
    formatear_eje_fecha(ax)
    nota_fuente(fig, "Fuente: BCRPData, series PN03442FQ y PN03433FQ. Elaboración propia.")
    guardar(fig, "figura1_deuda_interna_externa.png")


def figura2_monedas(panel):
    """
    Barras apiladas al 100 % solo para los trimestres con boletin disponible.
    Se usan barras (no un area continua) porque la serie del MEF tiene huecos:
    un area uniria con una linea recta trimestres separados por varios anios.
    """
    sub = panel[panel["pct_soles"].notna()].reset_index(drop=True)
    if sub.empty:
        print("[Figura 2] Sin datos del MEF; se omite.")
        return
    series = [("pct_soles", "Soles", AZUL), ("pct_dolares", "Dólares", NARANJA),
              ("pct_euros", "Euros", AGUAMARINA), ("pct_otras_monedas", "Otras", AMARILLO)]
    pos = np.arange(len(sub))
    fig, ax = plt.subplots(figsize=(9, 4.6))
    base = np.zeros(len(sub))
    for col, etiqueta, color in series:
        valores = sub[col].fillna(0).to_numpy()
        ax.bar(pos, valores, bottom=base, color=color, label=etiqueta, width=0.7,
               edgecolor=FONDO, linewidth=1.5)
        base += valores
    for i, v in enumerate(sub["pct_soles"]):
        ax.text(i, v / 2, f"{v:.0f}%", ha="center", va="center", fontsize=8, color=FONDO)
    ax.set_xticks(pos, sub["trimestre"])
    ax.set_title(f"Composición de la deuda pública por moneda (%), trimestres con boletín disponible")
    ax.set_ylabel("% del saldo de deuda")
    ax.set_ylim(0, 100)
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1), ncol=1)
    nota_fuente(fig, "Fuente: MEF, boletines trimestrales de deuda pública (parseo programático). "
                     "Solo trimestres cuyo boletín pudo descargarse (ver incidencias_fuente.md). Elaboración propia.")
    guardar(fig, "figura2_composicion_moneda.png")


def figura3_vida_costo(panel):
    con_dato = panel.index[panel["vida_media"].notna() | panel["costo_promedio"].notna()]
    if len(con_dato) == 0:
        print("[Figura 3] Sin datos del MEF; se omite.")
        return
    # Se toma toda la rejilla trimestral entre el primer y el ultimo dato: los trimestres
    # sin boletin quedan como NaN y la linea se corta ahi (no se inventa la trayectoria).
    sub = panel.loc[con_dato.min():con_dato.max()]
    x = fecha_trimestre(sub)
    # Dos medidas de distinta escala -> dos paneles con su propio eje (nunca doble eje Y)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 6), sharex=True)
    ax1.plot(x, sub["vida_media"], color=AZUL, linewidth=2, marker="o", markersize=4)
    ax1.set_title(f"Vida media de la deuda pública (años), {rango_anios(sub)}")
    eje_y_con_rango_minimo(ax1, sub["vida_media"], rango_minimo=4)
    ax1.set_ylabel("Años")
    ax2.plot(x, sub["costo_promedio"], color=NARANJA, linewidth=2, marker="o", markersize=4)
    ax2.set_title(f"Costo promedio de la deuda pública (tasa equivalente en soles, %), {rango_anios(sub)}")
    eje_y_con_rango_minimo(ax2, sub["costo_promedio"], rango_minimo=2)
    formatear_eje_fecha(ax2)
    ax2.set_ylabel("%")
    for ax, col in ((ax1, "vida_media"), (ax2, "costo_promedio")):
        s = sub[col].dropna()
        if not s.empty:
            primero, ultimo = s.index[0], s.index[-1]
            ax.annotate(f"{sub.loc[primero, 'trimestre']}: {s[primero]:.2f}",
                        xy=(x[sub.index.get_loc(primero)], s[primero]),
                        xytext=(0, 9), textcoords="offset points", ha="left", fontsize=8, color=TINTA)
            if ultimo != primero:
                ax.annotate(f"{sub.loc[ultimo, 'trimestre']}: {s[ultimo]:.2f}",
                            xy=(x[sub.index.get_loc(ultimo)], s[ultimo]),
                            xytext=(0, -14), textcoords="offset points", ha="right", fontsize=8, color=TINTA)
    fig.tight_layout()
    nota_fuente(fig, "Fuente: MEF, boletines trimestrales de deuda pública (parseo programático). "
                     "Los tramos sin línea son trimestres sin boletín descargado. Elaboración propia.")
    guardar(fig, "figura3_vida_media_costo.png")


def figura4_intereses(panel):
    anual = panel.groupby("anio", as_index=False)["intereses_pct_ingresos_bm"].first().dropna()
    if anual.empty:
        print("[Figura 4] Sin datos del Banco Mundial; se omite.")
        return
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.bar(anual["anio"], anual["intereses_pct_ingresos_bm"], color=AZUL, width=0.7, edgecolor=FONDO, linewidth=1)
    ax.set_title(f"Pago de intereses de la deuda (% de los ingresos del gobierno), {rango_anios(anual)}")
    ax.set_ylabel("% de los ingresos")
    ax.grid(axis="x", visible=False)
    ult = anual.iloc[-1]
    ax.annotate(f"{ult['intereses_pct_ingresos_bm']:.1f}%", xy=(ult["anio"], ult["intereses_pct_ingresos_bm"]),
                xytext=(0, 4), textcoords="offset points", ha="center", fontsize=9, color=TINTA)
    nota_fuente(fig, "Fuente: Banco Mundial, indicador GC.XPN.INTP.RV.ZS. Elaboración propia.")
    guardar(fig, "figura4_intereses_ingresos.png")


def main():
    if not os.path.exists(ENTRADA):
        raise SystemExit("Falta el archivo procesado: corre 03_limpieza_datos.py")
    os.makedirs(CARPETA_SALIDAS, exist_ok=True)
    panel = pd.read_csv(ENTRADA)
    print(f"Panel: {len(panel)} trimestres, {panel['trimestre'].iloc[0]} a {panel['trimestre'].iloc[-1]}\n")

    tabla1_subperiodos(panel)
    tabla2_correlaciones(panel)
    tabla3_regresion(panel)
    tabla4_comparacion_mef(panel)
    figura1_interna_externa(panel)
    figura2_monedas(panel)
    figura3_vida_costo(panel)
    figura4_intereses(panel)
    print("\nListo. Revisa la carpeta salidas/ (tablas .csv y 4 figuras .png)")


if __name__ == "__main__":
    main()
