"""Utilidades compartidas: rutas del proyecto y lectura de la configuración.

Todos los scripts leen las reglas desde config/reglas_negocio.yaml. Así, si Admisiones
corrige un valor (por ejemplo una tarifa), se cambia en un solo lugar y todo el
pipeline se vuelve a generar con la regla nueva.
"""
from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[1]
CONFIG = RAIZ / "config" / "reglas_negocio.yaml"
DATA_RAW = RAIZ / "data" / "raw"
DATA_CATALOGOS = RAIZ / "data" / "catalogos"
DATA_PROCESSED = RAIZ / "data" / "processed"
TABLAS_DIR = DATA_PROCESSED / "tablas"
SQL_DIR = RAIZ / "sql"
REPORTS = RAIZ / "reports"
FIGURAS = REPORTS / "figuras"

# La consola de Windows usa cp1252 por defecto; forzamos UTF-8 para tildes y "ñ".
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


@lru_cache(maxsize=1)
def cargar_config() -> dict:
    """Lee el YAML de reglas de negocio una sola vez por ejecución."""
    with open(CONFIG, encoding="utf-8") as f:
        return yaml.safe_load(f)


def asegurar_carpetas() -> None:
    for carpeta in (DATA_RAW, DATA_CATALOGOS, DATA_PROCESSED, TABLAS_DIR, SQL_DIR, REPORTS, FIGURAS):
        carpeta.mkdir(parents=True, exist_ok=True)
