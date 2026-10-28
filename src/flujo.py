"""Paso común de los sprints 3 a 6: cargar las tablas planas y construir las características del Sprint 2.

Así todos los sprints usan exactamente las mismas columnas, aprendidas solo con el entrenamiento.
"""
from __future__ import annotations

import pandas as pd

import caracteristicas as ca
import datos


def cargar_y_construir(fuente: str = "auto") -> dict:
    """Devuelve inscritos y permanencia con características, las referencias del Sprint 2 y el origen de los datos."""
    inscritos, origen = datos.cargar("dataset_matricula", fuente)
    permanencia, _ = datos.cargar("dataset_permanencia", fuente)
    ref = ca.ajustar_referencias(inscritos, permanencia)
    d = ca.construir_caracteristicas(inscritos, ref)
    p = ca.construir_caracteristicas(permanencia, ref)
    return {"inscritos": d, "permanencia": p, "referencias": ref, "origen": origen}


def conjunto(d: pd.DataFrame, *nombres: str) -> pd.DataFrame:
    """Filtra por partición temporal: conjunto(d, 'ENTRENAMIENTO', 'VALIDACION')."""
    return d[d["particion"].isin(nombres)]


def modelos_finales(f: dict, parametros: dict) -> dict:
    """Reentrena los modelos finales del Sprint 3 con los hiperparámetros ya elegidos (los guarda modelos/*.json).

    Sirve en Google Colab, donde no están los archivos .joblib: con la misma semilla el resultado es idéntico.
    parametros = {"matricula": {"tipo", "parametros"}, "xgboost": {"parametros"}, "beca": {"tipo", "parametros"}}
    """
    import modelado as mo
    cfg = ca.configuracion()
    semilla, m = cfg["modelado"]["semilla"], cfg["caracteristicas"]["peso_previo_modelo_base"]
    d, p, ref = f["inscritos"], f["permanencia"], f["referencias"]
    hist = conjunto(d, "ENTRENAMIENTO", "VALIDACION", "PRUEBA")
    Xh, yh = mo.preparar_X(hist, ref, mo.VARIABLES_MATRICULA), hist["matriculado"].astype(int)
    bec = p[p["becado"] == 1]
    Xb, yb = mo.preparar_X(bec, ref, mo.VARIABLES_BECA), bec["perdio_beca_semestre_1"].astype(int)
    pm, pb = parametros["matricula"], parametros["beca"]
    return {
        "referencias": ref,
        "modelo_matricula": mo.construir_pipeline(pm["tipo"], pm["parametros"], mo.VARIABLES_MATRICULA, semilla).fit(Xh, yh),
        "modelo_matricula_xgboost": mo.construir_pipeline("xgboost", parametros["xgboost"]["parametros"],
                                                          mo.VARIABLES_MATRICULA, semilla).fit(Xh, yh),
        "modelo_base": mo.ModeloBase(m=m).fit(hist, hist["matriculado"]),
        "modelo_beca": mo.construir_pipeline(pb["tipo"], pb["parametros"], mo.VARIABLES_BECA, semilla).fit(Xb, yb),
        "fondo_matricula": Xh.sample(300, random_state=1), "fondo_beca": Xb.sample(200, random_state=1),
    }
