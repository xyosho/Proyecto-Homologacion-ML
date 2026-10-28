"""Modelos y métricas (Sprint 2: modelo base · Sprint 3: modelos de Machine Learning).

El MODELO BASE es el "cálculo sencillo" que pide el docente para comparar: predice para cada inscrito la tasa
histórica de matrícula de su grupo (beca × canal agrupado). Si un grupo tiene pocos casos, su tasa se acerca a la del
grupo mayor (su beca); así un grupo de 3 personas no queda con una tasa extrema de 0% o 100%:

    tasa_suavizada = (matriculados + m · tasa_del_grupo_mayor) / (inscritos + m)

m (peso_previo_modelo_base = 10) equivale a "10 aspirantes imaginarios con la tasa del grupo mayor".
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (average_precision_score, brier_score_loss, f1_score, log_loss, precision_score,
                             recall_score, roc_auc_score)


class ModeloBase:
    """Tasa histórica por grupo, con suavizado jerárquico hacia el grupo mayor y hacia la tasa global."""

    def __init__(self, grupo: tuple[str, ...] = ("beca", "canal_agrupado"), m: float = 10.0):
        self.grupo, self.m = list(grupo), m

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "ModeloBase":
        y = pd.Series(np.asarray(y, dtype=float), index=X.index)
        self.global_ = float(y.mean())
        padre = y.groupby(X[self.grupo[0]]).agg(["size", "sum"])
        self.padre_ = (padre["sum"] + self.m * self.global_) / (padre["size"] + self.m)
        celda = y.groupby([X[c] for c in self.grupo]).agg(["size", "sum"])
        previo = celda.index.get_level_values(0).map(self.padre_).to_numpy()
        self.celda_ = (celda["sum"] + self.m * previo) / (celda["size"] + self.m)
        self.tabla_ = celda.rename(columns={"size": "inscritos", "sum": "matriculados"}).assign(
            tasa_cruda=lambda t: t["matriculados"] / t["inscritos"], tasa_suavizada=self.celda_)
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        claves = list(zip(*[X[c] for c in self.grupo]))
        p = pd.Series(claves).map(self.celda_.to_dict())
        p = p.fillna(X[self.grupo[0]].map(self.padre_).reset_index(drop=True)).fillna(self.global_)
        p = p.to_numpy(float)
        return np.column_stack([1 - p, p])


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
# SPRINT 3 — Modelos de Machine Learning
# =============================================================================
# Variables de entrada. Todas se conocen ANTES de la decisión que se predice (sin fuga de datos).
# No se usa colegio_promedio_saber11 (media ICFES del colegio): Admisiones no suele tener ese dato (bitácora H-43).
VARIABLES_MATRICULA = {
    "numericas": ["punt_global", "icfes_al_cuadrado", "promedio_acumulado_colegio", "edad_al_inscribirse", "estrato",
                  "log_distancia", "dias_registro_a_inscripcion", "contactos_antes_de_inscribirse",
                  "anios_desde_saber11", "puntaje_vocacional", "pct_descuento_inicial",
                  "valor_neto_primer_semestre", "probabilidad_acceso_beca", "brecha_colegio_vs_icfes"],
    "binarias": ["entrevista_realizada", "apoyo_foes", "elegible_foes", "colegio_en_convenio", "captado_en_evento",
                 "colegio_privado", "semestre_2"],
    "categoricas": ["programa", "genero", "canal", "beca", "tipo_colegio", "regimen_salud", "segmento_mercado"],
}
# Objetivo 2 (pérdida de beca): mismas variables previas a la matrícula + el promedio estimado del Sprint 2.
# NO se usa promedio_semestre_1: es lo que define si se pierde la beca (sería fuga de datos).
VARIABLES_BECA = {
    "numericas": ["punt_global", "promedio_acumulado_colegio", "promedio_matematicas_colegio",
                  "promedio_estimado_universidad", "brecha_colegio_vs_icfes", "edad_al_inscribirse", "estrato",
                  "log_distancia", "anios_desde_saber11", "puntaje_vocacional"],
    "binarias": ["colegio_privado", "semestre_2"],     # apoyo_foes se retiró: solo 12 becados con FOES (bitácora H-46)
    "categoricas": ["programa", "genero", "beca", "tipo_colegio", "segmento_mercado"],
}
OBJETIVOS = {"matricula": ("matriculado", VARIABLES_MATRICULA), "beca": ("perdio_beca_semestre_1", VARIABLES_BECA)}


def preparar_X(d: pd.DataFrame, referencias: dict, variables: dict) -> pd.DataFrame:
    """Columnas de entrada del modelo, con el tratamiento de nulos del Sprint 1 y dos derivadas simples."""
    X = d.copy()
    X["puntaje_vocacional"] = X["puntaje_vocacional"].astype("Float64").fillna(0).astype(float)   # 0 = sin entrevista
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


def ajustar_cv(tipo: str, cfg: dict, X, y, variables: dict, pliegues: int = 5) -> pd.DataFrame:
    """Para el objetivo 2 (pocos datos): validación cruzada estratificada dentro del entrenamiento."""
    from sklearn.model_selection import StratifiedKFold, cross_val_predict
    cv = StratifiedKFold(n_splits=pliegues, shuffle=True, random_state=cfg["modelado"]["semilla"])
    filas = []
    for params in grilla(f"{tipo}_beca" if f"{tipo}_beca" in cfg["modelado"]["grillas"] else tipo, cfg):
        modelo = construir_pipeline(tipo, params, variables, cfg["modelado"]["semilla"])
        p = cross_val_predict(modelo, X, y, cv=cv, method="predict_proba")[:, 1]
        m = metricas(y, p)
        filas.append({"tipo": tipo, **{f"param_{k}": v for k, v in params.items()}, "log_loss_cv": m["log_loss"],
                      "auc_cv": m["auc_roc"], "brier_cv": m["brier"], "parametros": params})
    return pd.DataFrame(filas).sort_values("log_loss_cv").reset_index(drop=True)


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


def nombres_salida(modelo) -> list[str]:
    """Nombres de las columnas que realmente ve el modelo (después del one-hot)."""
    return list(modelo.named_steps["preparacion"].get_feature_names_out())
