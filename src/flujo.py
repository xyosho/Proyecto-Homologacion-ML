"""Paso común de los sprints 3 a 6: cargar las tablas planas y construir las características del Sprint 2.

Así todos los sprints usan exactamente las mismas columnas, aprendidas solo con el entrenamiento.
"""
from __future__ import annotations

import pandas as pd

import caracteristicas as ca
import datos


def cargar_y_construir(fuente: str = "auto") -> dict:
    """Devuelve los inscritos con características, las referencias del Sprint 2 y el origen de los datos."""
    inscritos, origen = datos.cargar_inscritos(fuente)
    ref = ca.ajustar_referencias(inscritos)
    return {"inscritos": ca.construir_caracteristicas(inscritos, ref), "referencias": ref, "origen": origen}


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
    Xh, yh = mo.preparar_X(hist, ref, mo.VARIABLES_MATRICULA), hist["matriculado"].astype(int)
    pm = parametros["matricula"]
    return {
        "referencias": ref,
        "modelo_matricula": mo.construir_pipeline(pm["tipo"], pm["parametros"], mo.VARIABLES_MATRICULA, semilla).fit(Xh, yh),
        "modelo_matricula_xgboost": mo.construir_pipeline("xgboost", parametros["xgboost"]["parametros"],
                                                          mo.VARIABLES_MATRICULA, semilla).fit(Xh, yh),
        # La regresión logística del Sprint 2 (sin ajuste de hiperparámetros), para compararla en igualdad de condiciones
        "logistica_sprint2": mo.construir_pipeline("logistica", cfg["modelado"]["sprint2_logistica"],
                                                   mo.VARIABLES_MATRICULA, semilla).fit(Xh, yh),
        "fondo_matricula": Xh.sample(300, random_state=1),
    }
