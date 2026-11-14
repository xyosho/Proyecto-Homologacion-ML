"""Paso común de los sprints 3 a 6: cargar las tablas planas y construir las características del Sprint 2.

Así todos los sprints usan exactamente las mismas columnas, aprendidas solo con el entrenamiento.
"""
from __future__ import annotations

import pandas as pd

import caracteristicas as ca
import datos


def cargar_y_construir(fuente: str = "auto") -> dict:
    """Devuelve los inscritos con características, las referencias del Sprint 2, el origen de los datos y las
    respuestas de la entrevista por sección (la entrada del modelo NLP; no son columnas del modelo de matrícula)."""
    import nlp_vocacion as nv
    inscritos, origen = datos.cargar_inscritos(fuente)
    ref = ca.ajustar_referencias(inscritos)
    return {"inscritos": ca.construir_caracteristicas(inscritos, ref), "referencias": ref, "origen": origen,
            "entrevista": inscritos[["inscripcion_id", *nv.SECCIONES]]}


def conjunto(d: pd.DataFrame, *nombres: str) -> pd.DataFrame:
    """Filtra por partición temporal: conjunto(d, 'ENTRENAMIENTO', 'VALIDACION')."""
    return d[d["particion"].isin(nombres)]


def modelos_finales(f: dict, parametros: dict) -> dict:
    """Reentrena los modelos finales del Sprint 3 con los hiperparámetros ya elegidos (los guarda modelos/*.json).

    Sirve en Google Colab, donde no están los archivos .joblib: con la misma semilla el resultado es idéntico.
    parametros = {"matricula": {"tipo", "parametros"}, "xgboost": {"parametros"}}
    """
    import modelado as mo
    cfg = ca.configuracion()
    semilla = cfg["modelado"]["semilla"]
    d, ref = f["inscritos"], f["referencias"]
    hist = conjunto(d, "ENTRENAMIENTO", "VALIDACION", "PRUEBA")
    V, V2 = mo.VARIABLES_MATRICULA_NLP, mo.VARIABLES_MATRICULA          # Sprint 3 (con NLP) · Sprint 2 (sin NLP)
    Xh, yh = mo.preparar_X(hist, ref, V), hist["matriculado"].astype(int)
    pm = parametros["matricula"]
    return {
        "referencias": ref,
        "modelo_matricula": mo.construir_pipeline(pm["tipo"], pm["parametros"], V, semilla).fit(Xh, yh),
        "modelo_matricula_xgboost": mo.construir_pipeline("xgboost", parametros["xgboost"]["parametros"], V, semilla).fit(Xh, yh),
        # La regresión logística del Sprint 2 (sin ajuste de hiperparámetros ni NLP), para compararla en igualdad de condiciones
        "logistica_sprint2": mo.construir_pipeline("logistica", cfg["modelado"]["sprint2_logistica"], V2, semilla).fit(
            mo.preparar_X(hist, ref, V2), yh),
        "fondo_matricula": Xh.sample(300, random_state=1),
    }
