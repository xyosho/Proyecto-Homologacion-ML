"""Carga de las tablas planas para los sprints 2 a 6.

Fuente preferida: Supabase con la API de solo lectura (credenciales en .env o en los Secretos de Colab, ver
conexion_supabase.py). Si no hay credenciales, se usan los CSV que exporta el pipeline (data/processed), que son
idénticos (las pruebas lo comprueban). La función siempre dice de dónde salieron los datos.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

TABLAS = ("dataset_matricula", "dataset_permanencia", "resultado_campana_2027_1")   # el último solo en el Sprint 5
ENTEROS_CON_VACIOS = ("matriculado", "puntaje_vocacional", "perdio_beca_semestre_1", "matriculado_real")


def preparar_tipos(df: pd.DataFrame) -> pd.DataFrame:
    """La API devuelve JSON: se fijan los tipos para que local y Colab den exactamente lo mismo."""
    df = df.copy()
    for c in ENTEROS_CON_VACIOS:
        if c in df:
            df[c] = pd.to_numeric(df[c]).astype("Int64")
    for c in ("distancia_campus_km", "distancia_vial_km", "colegio_promedio_saber11", "promedio_acumulado_colegio",
              "promedio_matematicas_colegio", "pct_descuento_inicial", "promedio_semestre_1"):
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


def cargar(tabla: str, fuente: str = "auto") -> tuple[pd.DataFrame, str]:
    """Devuelve (datos, origen). fuente: 'supabase', 'local' o 'auto' (Supabase si hay credenciales)."""
    if tabla not in TABLAS:
        raise ValueError(f"Tabla desconocida: {tabla}")
    if fuente in ("auto", "supabase"):
        try:
            from conexion_supabase import crear_cliente, leer_dataset_matricula
            df = leer_dataset_matricula(crear_cliente(), tabla=tabla)
            return preparar_tipos(df), "Supabase (API de solo lectura)"
        except Exception as error:
            if fuente == "supabase":
                raise
            aviso = type(error).__name__
    ruta = _csv_local(tabla)
    df = pd.read_parquet(ruta) if ruta.suffix == ".parquet" else pd.read_csv(ruta)
    origen = "CSV local exportado por el pipeline" + (f" (sin conexión a Supabase: {aviso})" if fuente == "auto" else "")
    return preparar_tipos(df), origen
