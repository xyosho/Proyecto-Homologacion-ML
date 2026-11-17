"""Carga de las tablas planas para los sprints 2 a 6.

Fuente preferida: Supabase con la API de solo lectura (credenciales en .env o en los Secretos de Colab, ver
conexion_supabase.py). Si no hay credenciales, se usan los CSV que exporta el pipeline (data/processed), que son
idénticos (las pruebas lo comprueban): en el computador, los del repositorio; en Colab, donde no está el repositorio,
la copia que está en GitHub (data/processed de la rama del sprint), así que no hay que subir ningún archivo.
La función siempre dice de dónde salieron los datos.
"""
from __future__ import annotations

import io
import os
import urllib.request
from pathlib import Path

import pandas as pd

TABLAS = ("dataset_matricula", "dataset_entrevista", "resultado_campana_2027_1")   # el último solo en el Sprint 5
ENTEROS_CON_VACIOS = ("matriculado", "puntaje_vocacional", "matriculado_real")


def preparar_tipos(df: pd.DataFrame) -> pd.DataFrame:
    """La API devuelve JSON: se fijan los tipos para que local y Colab den exactamente lo mismo."""
    if df.empty:                                   # tabla sin filas: no hay tipos que fijar
        return df
    df = df.copy()
    for c in ENTEROS_CON_VACIOS:
        if c in df:
            df[c] = pd.to_numeric(df[c]).astype("Int64")
    for c in ("distancia_campus_km", "distancia_vial_km", "colegio_promedio_saber11", "pct_descuento_inicial"):
        if c in df:
            df[c] = pd.to_numeric(df[c]).astype(float)
    if "asesor_id" in df:
        df["asesor_id"] = df["asesor_id"].astype(int)
    return df.sort_values("inscripcion_id").reset_index(drop=True)


def _csv_local(tabla: str) -> Path:
    from comun import DATA_PROCESSED
    if tabla == "resultado_campana_2027_1":       # "sobre sellado" desde la Semana 1 (data/processed/oculto)
        return DATA_PROCESSED / "oculto" / "resultado_2027_1_sellado.parquet"
    return DATA_PROCESSED / f"{tabla}.csv"


def url_github(tabla: str) -> tuple[str, str]:
    """Dirección de la copia de la tabla en GitHub y la rama de donde sale (config/reglas_negocio.yaml -> repositorio;
    en Colab, cada cuaderno fija la rama de su sprint en la variable de entorno RAMA_DATOS_GITHUB)."""
    from comun import cargar_config
    repo = cargar_config()["repositorio"]
    rama = os.environ.get("RAMA_DATOS_GITHUB") or repo["rama_datos"]
    ruta = "data/processed/" + ("oculto/resultado_2027_1_sellado.parquet" if tabla == "resultado_campana_2027_1"
                                else f"{tabla}.csv")
    return f"https://raw.githubusercontent.com/{repo['github']}/{rama}/{ruta}", rama


def _leer_github(tabla: str) -> tuple[pd.DataFrame, str]:
    url, rama = url_github(tabla)
    with urllib.request.urlopen(url, timeout=120) as respuesta:
        contenido = io.BytesIO(respuesta.read())
    return (pd.read_parquet(contenido) if url.endswith(".parquet") else pd.read_csv(contenido)), rama


def cargar(tabla: str, fuente: str = "auto") -> tuple[pd.DataFrame, str]:
    """Devuelve (datos, origen). fuente: 'supabase', 'local', 'github' o 'auto' (Supabase si hay credenciales; si no,
    el CSV del repositorio si está en el computador, o su copia en GitHub, como en Colab)."""
    if tabla not in TABLAS:
        raise ValueError(f"Tabla desconocida: {tabla}")
    if fuente not in ("auto", "supabase", "local", "github"):
        raise ValueError(f"Fuente desconocida: {fuente}")
    aviso = ""
    if fuente in ("auto", "supabase"):
        try:
            from conexion_supabase import crear_cliente, leer_dataset_matricula
            df = leer_dataset_matricula(crear_cliente(), tabla=tabla)
            if df.empty:                       # la tabla existe pero no tiene filas (o la API no deja leerlas)
                raise RuntimeError(f"La tabla {tabla} está vacía en Supabase: cárguela con python src/s05_cargar_supabase.py.")
            return preparar_tipos(df), "Supabase (API de solo lectura)"
        except Exception as error:
            if fuente == "supabase":
                raise
            aviso = type(error).__name__
    sin_conexion = f" (sin conexión a Supabase: {aviso})" if fuente == "auto" else ""
    ruta = _csv_local(tabla)
    if fuente == "github" or (fuente == "auto" and not ruta.exists()):
        df, rama = _leer_github(tabla)
        return preparar_tipos(df), f"GitHub: copia de data/processed en la rama {rama} del repositorio{sin_conexion}"
    df = pd.read_parquet(ruta) if ruta.suffix == ".parquet" else pd.read_csv(ruta)
    return preparar_tipos(df), "CSV local exportado por el pipeline" + sin_conexion


def cargar_inscritos(fuente: str = "auto") -> tuple[pd.DataFrame, str]:
    """dataset_matricula con las respuestas de la entrevista (dataset_entrevista, texto por sección) unidas por inscripcion_id."""
    inscritos, origen = cargar("dataset_matricula", fuente)
    entrevista, _ = cargar("dataset_entrevista", fuente)
    if len(entrevista) != len(inscritos):     # p. ej. la tabla existe en Supabase pero aún no se cargó (src/s05)
        if fuente == "supabase":
            raise RuntimeError(f"dataset_entrevista tiene {len(entrevista)} filas y dataset_matricula {len(inscritos)}: "
                               "falta cargar la entrevista en Supabase (python src/s05_cargar_supabase.py).")
        entrevista, _ = cargar("dataset_entrevista", "local" if _csv_local("dataset_entrevista").exists() else "github")
    return inscritos.merge(entrevista, on="inscripcion_id", how="left", validate="one_to_one"), origen
