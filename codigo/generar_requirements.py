# Nombres y apellidos: Chinte Ponce, Joseph Alexander
# Codigo de matricula: 2024200494M
# Tema: N.86 - Estructura y sostenibilidad de la deuda publica peruana
# Fecha de extraccion: (completar con la fecha real de ejecucion)

"""Genera requirements.txt con las versiones EXACTAS instaladas (numeral 2.4.2)."""

import sys
from importlib.metadata import version, PackageNotFoundError

PAQUETES = ["requests", "beautifulsoup4", "pdfplumber", "pandas", "numpy", "matplotlib"]

lineas = []
for paquete in PAQUETES:
    try:
        lineas.append(f"{paquete}=={version(paquete)}")
    except PackageNotFoundError:
        print(f"AVISO: {paquete} no esta instalado")

with open("requirements.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lineas) + "\n")

print("requirements.txt:")
print("\n".join(lineas))
print("\nVersion de Python:", sys.version.split()[0])
