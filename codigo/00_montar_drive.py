# Nombres y apellidos: Chinte Ponce, Joseph Alexander
# Codigo de matricula: 2024200494M
# Tema: N.86 - Estructura y sostenibilidad de la deuda publica peruana
# Fecha de extraccion: (completar con la fecha real de ejecucion)

"""
Celda 0 (solo para Google Colab). Monta Google Drive, crea la carpeta del
proyecto con sus subcarpetas y se ubica DENTRO de ella. Desde ese momento los
demas scripts trabajan con rutas relativas (datos_crudos/..., salidas/...), tal
como exige el numeral 2.4.4 de la consigna. Si se ejecuta fuera de Colab
(por ejemplo, el docente en su computadora), basta con abrir una terminal en la
carpeta del proyecto y correr los scripts 01 a 04 en orden: esta celda no hace falta.

Hay que volver a correr esta celda cada vez que se abre una sesion nueva de Colab.
"""

import os

try:
    from google.colab import drive
    drive.mount("/content/drive")
    BASE = "/content/drive/MyDrive/proyecto_deuda_2024200494M"
except ImportError:
    # Fuera de Colab: se usa la carpeta actual como carpeta del proyecto
    BASE = os.getcwd()

SUBCARPETAS = [
    "codigo",
    os.path.join("datos_crudos", "bcrp"),
    os.path.join("datos_crudos", "banco_mundial"),
    os.path.join("datos_crudos", "mef_pdf"),
    "datos_procesados",
    "salidas",
]

os.makedirs(BASE, exist_ok=True)
for sub in SUBCARPETAS:
    os.makedirs(os.path.join(BASE, sub), exist_ok=True)

os.chdir(BASE)
print("Carpeta del proyecto lista y activa:")
print(os.getcwd())
print("Contenido:", sorted(os.listdir(".")))
