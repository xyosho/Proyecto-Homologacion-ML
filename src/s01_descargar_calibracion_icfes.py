"""PASO 1 — Descargar la muestra REAL de calibración del ICFES (datos abiertos).

¿Por qué? Los datos sintéticos de puntajes, estratos y colegios no deben inventarse "a ojo":
se calibran con los microdatos públicos y anonimizados del ICFES ("Resultados únicos
Saber 11", datos.gov.co, licencia CC BY-SA 4.0). Así la distribución y las correlaciones
de los puntajes sintéticos se pueden comparar contra datos reales (paso 3).

Filtro de la muestra:
  - Periodos 2019-4 y 2022-4 (los más recientes de calendario A disponibles en el dataset).
  - Residentes en Bogotá y en los 11 municipios de Sabana Centro (zona de influencia del campus).
  - Calendario A y estudiantes regulares (no "individuales").

Hallazgo de auditoría (H-10): en 2019-4 y 2022-4 cada estudiante aparece exactamente
2 veces (filas idénticas). Se eliminan duplicados por `estu_consecutivo`.

Uso:  python src/s01_descargar_calibracion_icfes.py   (usa caché si ya existe)
"""
from __future__ import annotations

import json
from datetime import datetime

import pandas as pd
import requests

from comun import DATA_RAW, asegurar_carpetas

URL = "https://www.datos.gov.co/resource/kgxf-xxbe.csv"
SALIDA = DATA_RAW / "icfes_saber11_calibracion.parquet"
METADATOS = DATA_RAW / "icfes_saber11_calibracion_metadatos.json"

# Bogotá + Sabana Centro (códigos DIVIPOLA del DANE)
MUNICIPIOS = {
    "11001": "BOGOTÁ D.C.", "25175": "CHÍA", "25126": "CAJICÁ", "25214": "COTA",
    "25899": "ZIPAQUIRÁ", "25758": "SOPÓ", "25817": "TOCANCIPÁ", "25799": "TENJO",
    "25785": "TABIO", "25200": "COGUA", "25295": "GACHANCIPÁ", "25486": "NEMOCÓN",
}
PERIODOS = ("20194", "20224")
COLUMNAS = [
    "periodo", "estu_consecutivo", "estu_fechanacimiento", "estu_genero", "estu_nacionalidad",
    "estu_cod_reside_mcpio", "estu_mcpio_reside",
    "cole_cod_dane_establecimiento", "cole_nombre_establecimiento", "cole_naturaleza",
    "cole_calendario", "cole_caracter", "cole_jornada", "cole_bilingue", "cole_area_ubicacion", "cole_mcpio_ubicacion",
    "fami_estratovivienda",
    "punt_lectura_critica", "punt_matematicas", "punt_sociales_ciudadanas",
    "punt_c_naturales", "punt_ingles", "punt_global",
]


def construir_where() -> str:
    mpios = ",".join(f"'{c}'" for c in MUNICIPIOS)
    pers = ",".join(f"'{p}'" for p in PERIODOS)
    return (f"periodo in({pers}) AND estu_cod_reside_mcpio in({mpios}) "
            f"AND cole_calendario='A' AND estu_estudiante='ESTUDIANTE'")


def descargar(tam_pagina: int = 50000) -> pd.DataFrame:
    """Descarga paginada (la API Socrata entrega máximo `tam_pagina` filas por solicitud)."""
    partes, offset = [], 0
    while True:
        params = {"$select": ",".join(COLUMNAS), "$where": construir_where(),
                  "$order": ":id", "$limit": tam_pagina, "$offset": offset}
        r = requests.get(URL, params=params, timeout=300)
        r.raise_for_status()
        from io import StringIO
        parte = pd.read_csv(StringIO(r.content.decode("utf-8")), dtype=str)
        partes.append(parte)
        print(f"  offset={offset:>7,}  filas={len(parte):,}")
        if len(parte) < tam_pagina:
            break
        offset += tam_pagina
    return pd.concat(partes, ignore_index=True)


def main() -> None:
    asegurar_carpetas()
    if SALIDA.exists():
        print(f"Ya existe {SALIDA.name}; se usa la caché (borre el archivo para volver a descargar).")
        return
    print("Descargando muestra de calibración ICFES desde datos.gov.co ...")
    crudo = descargar()
    filas_crudas = len(crudo)
    # H-10: los registros vienen duplicados; nos quedamos con uno por estudiante.
    datos = crudo.drop_duplicates(subset=["estu_consecutivo"]).reset_index(drop=True)
    for c in [c for c in COLUMNAS if c.startswith("punt_")]:
        datos[c] = pd.to_numeric(datos[c], errors="coerce").astype("Int64")
    datos.to_parquet(SALIDA, index=False)

    meta = {
        "fuente": "ICFES. Resultados únicos Saber 11 [conjunto de datos]. datos.gov.co, id kgxf-xxbe",
        "licencia": "Creative Commons Atribución-CompartirIgual 4.0 (CC BY-SA 4.0)",
        "url_api": URL, "where": construir_where(), "columnas": COLUMNAS,
        "fecha_descarga": datetime.now().isoformat(timespec="seconds"),
        "filas_descargadas": filas_crudas, "filas_tras_deduplicar": len(datos),
        "duplicados_eliminados": filas_crudas - len(datos),
        "por_periodo": datos["periodo"].value_counts().sort_index().to_dict(),
    }
    METADATOS.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
