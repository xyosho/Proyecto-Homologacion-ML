"""Modelos y métricas de la matrícula (Sprint 2: regresión logística · Sprint 3: comparación con Random Forest y XGBoost).

El primer modelo del proyecto (Sprint 2) es una REGRESIÓN LOGÍSTICA sin ajuste de hiperparámetros
(config/reglas_negocio.yaml -> modelado.sprint2_logistica). Se compara con la referencia mínima de decir siempre
"no se matricula" (ClaseMayoritaria). En el Sprint 3 se ajustan los hiperparámetros con la validación y se compara con
Random Forest y XGBoost.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (average_precision_score, brier_score_loss, f1_score, log_loss, precision_score,
                             recall_score, roc_auc_score)


class ClaseMayoritaria:
    """Referencia mínima: siempre predice la tasa global (todos iguales). Cualquier modelo útil debe superarla."""

    def fit(self, X, y):
        self.tasa_ = float(np.mean(np.asarray(y, dtype=float)))
        return self

    def predict_proba(self, X):
        return np.column_stack([np.full(len(X), 1 - self.tasa_), np.full(len(X), self.tasa_)])


def metricas(y, p, umbral: float = 0.5) -> dict:
    """Métricas de clasificación. 'error_pct' es el lenguaje del docente: % de inscritos mal clasificados."""
    y = np.asarray(y, dtype=int)
    p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    pred = (p >= umbral).astype(int)
    unica = len(np.unique(y)) > 1
    return {
        "n": int(len(y)), "umbral": float(umbral),
        "error_pct": float(100 * (pred != y).mean()),
        "exactitud": float((pred == y).mean()),
        "auc_roc": float(roc_auc_score(y, p)) if unica else float("nan"),
        "auc_pr": float(average_precision_score(y, p)) if unica else float("nan"),
        "brier": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, p, labels=[0, 1])),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "tasa_real": float(y.mean()), "tasa_predicha_media": float(p.mean()),
    }


def tabla_metricas(resultados: dict[str, dict]) -> pd.DataFrame:
    """{nombre_modelo: metricas} -> tabla ordenada para mostrar."""
    cols = ["n", "error_pct", "exactitud", "auc_roc", "auc_pr", "brier", "precision", "recall", "f1"]
    return pd.DataFrame(resultados).T[cols].astype(float).round(4)


# =============================================================================
# Modelos de Machine Learning (regresión logística desde el Sprint 2; Random Forest y XGBoost en el Sprint 3)
# =============================================================================
# Variables de entrada. Todas se conocen ANTES de la decisión que se predice (sin fuga de datos).
# No se usa colegio_promedio_saber11 (media ICFES del colegio): Admisiones no suele tener ese dato (bitácora H-43).
VARIABLES_MATRICULA = {
    "numericas": ["punt_global", "icfes_al_cuadrado", "promedio_acumulado_colegio", "edad_al_inscribirse", "estrato",
                  "log_distancia", "dias_registro_a_inscripcion", "contactos_antes_de_inscribirse",
                  "anios_desde_saber11", "indice_vocacional", "pct_descuento_inicial",
                  "valor_neto_primer_semestre", "brecha_colegio_vs_icfes"],
    "binarias": ["entrevista_realizada", "apoyo_foes", "elegible_foes", "colegio_en_convenio", "captado_en_evento",
                 "colegio_privado", "semestre_2"],
    "categoricas": ["programa", "genero", "canal", "beca", "tipo_colegio", "regimen_salud", "segmento_mercado"],
}


def preparar_X(d: pd.DataFrame, referencias: dict, variables: dict) -> pd.DataFrame:
    """Columnas de entrada del modelo, con el tratamiento de nulos del Sprint 1 y dos derivadas simples."""
    X = d.copy()
    X["indice_vocacional"] = X["indice_vocacional"].astype("Float64").fillna(0).astype(float)   # 0 = sin entrevista
    # (entrevista_realizada distingue "sin entrevista" de un índice de 0)
    media, desv = referencias["estandarizacion"]["punt_global"]
    X["icfes_al_cuadrado"] = ((X["punt_global"] - media) / desv) ** 2       # captura la "U invertida" del ICFES
    X["semestre_2"] = X["periodo"].str.endswith("-2").astype(int)          # ingreso a mitad de año
    columnas = variables["numericas"] + variables["binarias"] + variables["categoricas"]
    X = X[columnas].copy()
    for c in variables["categoricas"]:
        X[c] = X[c].astype(str)
    for c in variables["numericas"] + variables["binarias"]:
        X[c] = X[c].astype(float)
    return X


def construir_pipeline(tipo: str, parametros: dict, variables: dict, semilla: int = 20261105):
    """Preprocesamiento + modelo en un solo objeto: se ajusta y se aplica igual en todos los conjuntos."""
    from sklearn.compose import ColumnTransformer
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    from xgboost import XGBClassifier

    categ = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    if tipo == "logistica":
        prep = ColumnTransformer([("num", StandardScaler(), variables["numericas"] + variables["binarias"]),
                                  ("cat", categ, variables["categoricas"])], verbose_feature_names_out=False)
        modelo = LogisticRegression(max_iter=5000, **parametros)
    else:
        prep = ColumnTransformer([("num", "passthrough", variables["numericas"] + variables["binarias"]),
                                  ("cat", categ, variables["categoricas"])], verbose_feature_names_out=False)
        if tipo == "random_forest":
            modelo = RandomForestClassifier(n_estimators=500, random_state=semilla, n_jobs=-1, **parametros)
        elif tipo == "xgboost":
            modelo = XGBClassifier(random_state=semilla, n_jobs=1, eval_metric="logloss", tree_method="hist",
                                   subsample=0.8, colsample_bytree=0.8, **parametros)
        else:
            raise ValueError(tipo)
    return Pipeline([("preparacion", prep), ("modelo", modelo)])


def grilla(tipo: str, cfg: dict) -> list[dict]:
    """Combinaciones de hiperparámetros a probar (config/reglas_negocio.yaml -> modelado.grillas)."""
    from itertools import product
    g = cfg["modelado"]["grillas"][tipo]
    return [dict(zip(g, valores)) for valores in product(*g.values())]


def ajustar_temporal(tipo: str, cfg: dict, Xe, ye, Xv, yv, variables: dict) -> pd.DataFrame:
    """Prueba cada combinación entrenando con ENTRENAMIENTO y midiendo en VALIDACION (2026-1)."""
    filas = []
    for params in grilla(tipo, cfg):
        modelo = construir_pipeline(tipo, params, variables, cfg["modelado"]["semilla"]).fit(Xe, ye)
        m = metricas(yv, modelo.predict_proba(Xv)[:, 1])
        filas.append({"tipo": tipo, **{f"param_{k}": v for k, v in params.items()},
                      "log_loss_validacion": m["log_loss"], "auc_validacion": m["auc_roc"],
                      "brier_validacion": m["brier"], "error_pct_validacion": m["error_pct"], "parametros": params})
    return pd.DataFrame(filas).sort_values("log_loss_validacion").reset_index(drop=True)


def intervalo_bootstrap(y, p, funcion, n: int = 1000, semilla: int = 7, umbral: float = 0.5) -> tuple[float, float]:
    """IC 95% por remuestreo: se repite la medición en 1.000 muestras con reemplazo del conjunto de prueba."""
    y, p = np.asarray(y, dtype=int), np.asarray(p, dtype=float)
    rng = np.random.default_rng(semilla)
    valores = []
    for _ in range(n):
        i = rng.integers(0, len(y), len(y))
        if len(np.unique(y[i])) < 2:
            continue
        valores.append(funcion(y[i], p[i], umbral))
    return float(np.percentile(valores, 2.5)), float(np.percentile(valores, 97.5))


def diferencia_error(y, p_antes, p_despues, n: int = 1000, semilla: int = 7, umbral: float = 0.5) -> tuple[float, float]:
    """IC 95% de (error del modelo nuevo − error del anterior), en puntos, remuestreando los MISMOS inscritos.
    Si el intervalo incluye el 0, la diferencia puede ser azar: los dos modelos rinden igual."""
    y = np.asarray(y, dtype=int)
    falla_a = (np.asarray(p_antes) >= umbral) != y
    falla_b = (np.asarray(p_despues) >= umbral) != y
    rng = np.random.default_rng(semilla)
    dif = [100 * (falla_b[i].mean() - falla_a[i].mean()) for i in (rng.integers(0, len(y), len(y)) for _ in range(n))]
    return float(np.percentile(dif, 2.5)), float(np.percentile(dif, 97.5))


def frase_docente(error_antes: float, error_despues: float, nombre: str, ic: tuple[float, float], n: int,
                  antes: str = "La regresión logística de la Semana 2", cuando: str = "inscritos de 2026-2") -> str:
    """La frase que pide el docente ("tenía un error del X%, este modelo del Y%"), sin afirmar una mejora que no hay."""
    num = lambda v: f"{v:.1f}".replace(".", ",")   # noqa: E731
    frase = (f"{antes} tenía un error del {num(error_antes)}%, mientras que el modelo de la Semana 3 ({nombre}) tiene "
             f"un error del {num(error_despues)}% en {n:,} {cuando}, que ningún modelo vio al entrenar.".replace(f"{n:,}", f"{n:,}".replace(",", ".")))
    dif = error_despues - error_antes
    if ic[1] < 0:
        return frase + f" Mejora {num(-dif)} puntos (IC 95% de la diferencia: {num(ic[0])} a {num(ic[1])})."
    if ic[0] > 0:
        return frase + f" Es {num(dif)} puntos peor (IC 95% de la diferencia: {num(ic[0])} a {num(ic[1])})."
    return (frase + f" La diferencia ({num(dif)} puntos) está dentro del margen del azar (IC 95%: {num(ic[0])} a "
            f"{num(ic[1])}): los dos modelos rinden igual.")


def nombres_salida(modelo) -> list[str]:
    """Nombres de las columnas que realmente ve el modelo (después del one-hot)."""
    return list(modelo.named_steps["preparacion"].get_feature_names_out())
