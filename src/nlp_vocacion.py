"""SPRINT 2 — Modelo NLP: el puntaje vocacional que se lee en las palabras del aspirante.

Entrada: dataset_entrevista, las respuestas abiertas de la entrevista de admisión unidas por sección
(Interés por el programa académico, Historia de vida e Interés por la universidad).
Objetivo: el puntaje vocacional que dio el entrevistador (1 a 5).
Modelo: TF-IDF por sección (palabras y pares de palabras, sin tildes ni palabras vacías) + regresión Ridge.

El resultado, puntaje_vocacional_nlp (1 a 5), es la vocación según las palabras del propio aspirante. No es una copia
del entrevistador: las palabras también reflejan lo que él no alcanza a ver (supuesto S-49), y eso es lo que la
regresión logística del Sprint 3 puede aprovechar.

Regla contra la FUGA DE DATOS: se ajusta SOLO con el ENTRENAMIENTO. Las filas de entrenamiento reciben predicciones
fuera de pliegue (validación cruzada de 5 pliegues): ninguna se puntúa con un modelo que ya vio su propia respuesta.

Funciones: ajustar(entrenamiento) -> dict · puntuar(nlp, tabla) -> Series · palabras_clave(nlp) · metricas(y, p)
"""
from __future__ import annotations

import re
import unicodedata
from functools import partial

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.pipeline import Pipeline

SECCIONES = {"texto_interes_programa": "Interés por el programa académico",
             "texto_historia_vida": "Historia de vida",
             "texto_interes_universidad": "Interés por la universidad"}

# Palabras vacías del español, sin tildes (el TF-IDF quita las tildes antes de compararlas). Se CONSERVAN las que
# cambian el sentido de una respuesta: "no", "nunca", "todavia", "ya", "muy", "sin" y las muletillas de duda ("pues").
STOPWORDS_ES = sorted({
    "a", "al", "algo", "algun", "alguna", "algunas", "alguno", "algunos", "ante", "antes", "asi", "aun", "cada",
    "como", "con", "contra", "cual", "cuales", "cuando", "de", "del", "desde", "donde", "durante", "e", "el", "ella",
    "ellas", "ellos", "en", "entre", "era", "eran", "es", "esa", "esas", "ese", "eso", "esos", "esta", "estaba",
    "estas", "este", "esto", "estos", "fue", "fueron", "ha", "han", "hasta", "hay", "la", "las", "le", "les", "lo",
    "los", "me", "mi", "mis", "nos", "nosotros", "o", "os", "otra", "otras", "otro", "otros", "para", "pero", "por",
    "que", "quien", "quienes", "se", "ser", "si", "sobre", "son", "su", "sus", "te", "ti", "tu", "tus", "u",
    "un", "una", "unas", "uno", "unos", "y", "yo"})


def configuracion() -> dict:
    try:
        from comun import cargar_config
        return cargar_config()
    except ImportError:
        return CONFIG_PROYECTO  # noqa: F821  (lo define una celda del cuaderno de Colab)


def analizar(texto: str, ngramas: tuple = (1, 2)) -> list[str]:
    """Cómo ve el modelo una respuesta: minúsculas y sin tildes, se parte en frases (cada respuesta termina en punto),
    se quitan las palabras vacías y se forman palabras y pares de palabras DENTRO de cada frase. Así un par nunca
    mezcla el final de una respuesta con el inicio de la siguiente."""
    t = "".join(c for c in unicodedata.normalize("NFKD", str(texto).lower()) if not unicodedata.combining(c))
    salida = []
    for frase in re.split(r"[.;:!?¡¿]+", t):
        palabras = [w for w in re.findall(r"\b\w\w+\b", frase) if w not in STOPWORDS_ES]
        for n in range(ngramas[0], ngramas[1] + 1):
            salida += [" ".join(palabras[i:i + n]) for i in range(len(palabras) - n + 1)]
    return salida


def _pipeline(cfg: dict) -> Pipeline:
    n = cfg["caracteristicas"]["nlp"]
    analizador = partial(analizar, ngramas=tuple(n["ngramas"]))
    tfidf = ColumnTransformer([(col, TfidfVectorizer(analyzer=analizador, min_df=n["min_df"], sublinear_tf=True), col)
                               for col in SECCIONES])
    return Pipeline([("tfidf", tfidf), ("ridge", RidgeCV(alphas=n["alphas"]))])


def con_texto(d: pd.DataFrame) -> pd.Series:
    """True si el inscrito presentó la entrevista (tiene respuestas)."""
    if not set(SECCIONES) <= set(d.columns):
        return pd.Series(False, index=d.index)
    return d[list(SECCIONES)].notna().all(axis=1)


def ajustar(entrenamiento: pd.DataFrame, cfg: dict | None = None) -> dict:
    """Aprende, solo con las entrevistas del ENTRENAMIENTO, a leer el puntaje vocacional en las palabras."""
    cfg = cfg or configuracion()
    n = cfg["caracteristicas"]["nlp"]
    e = entrenamiento[con_texto(entrenamiento)]
    X, y = e[list(SECCIONES)], e["puntaje_vocacional"].astype(float).to_numpy()
    modelo = _pipeline(cfg).fit(X, y)
    pliegues = KFold(n["pliegues"], shuffle=True, random_state=n["semilla"])
    fuera = np.clip(cross_val_predict(_pipeline(cfg), X, y, cv=pliegues), 1, 5)
    return {"modelo": modelo, "fuera_de_pliegue": pd.Series(fuera, index=e["inscripcion_id"].to_numpy()),
            "alpha": float(modelo.named_steps["ridge"].alpha_), "n_entrevistas": int(len(e)),
            "n_terminos": int(len(modelo.named_steps["tfidf"].get_feature_names_out())), "media_entrenamiento": float(y.mean())}


def puntuar(nlp: dict, d: pd.DataFrame) -> pd.Series:
    """puntaje_vocacional_nlp (1 a 5) de cada fila; vacío si no hubo entrevista. Las filas del entrenamiento usan su
    predicción fuera de pliegue; las demás (validación, prueba, campaña y aspirantes nuevos), el modelo completo."""
    s = pd.Series(np.nan, index=d.index, dtype=float)
    m = con_texto(d)
    if m.any():
        s[m] = np.clip(nlp["modelo"].predict(d.loc[m, list(SECCIONES)]), 1, 5)
        fuera = d["inscripcion_id"].map(nlp["fuera_de_pliegue"])
        s = fuera.where(fuera.notna() & m, s)
    return s.round(3)


def terminos(texto: str, cfg: dict | None = None) -> list[str]:
    """Los términos que el modelo extrae de un texto (para mostrar el preprocesamiento)."""
    return analizar(texto, tuple((cfg or configuracion())["caracteristicas"]["nlp"]["ngramas"]))


def palabras_clave(nlp: dict, k: int = 8) -> pd.DataFrame:
    """Los términos que más suben y más bajan el puntaje en cada sección: las palabras que determinan la vocación."""
    nombres = nlp["modelo"].named_steps["tfidf"].get_feature_names_out()
    pesos = pd.DataFrame({"columna": [x.split("__", 1)[0] for x in nombres], "termino": [x.split("__", 1)[1] for x in nombres],
                          "peso": nlp["modelo"].named_steps["ridge"].coef_})
    filas = []
    for col, nombre in SECCIONES.items():
        p = pesos[pesos["columna"] == col]
        for sentido, parte in (("sube", p.nlargest(k, "peso")), ("baja", p.nsmallest(k, "peso"))):
            filas += [{"seccion": nombre, "sentido": sentido, "termino": t, "peso": round(float(w), 4)}
                      for t, w in zip(parte["termino"], parte["peso"])]
    return pd.DataFrame(filas)


def metricas(y, p, media_entrenamiento: float | None = None) -> dict:
    """Qué tan bien lee el modelo el puntaje del entrevistador (y frente a predecir siempre el promedio)."""
    y, p = np.asarray(y, dtype=float), np.asarray(p, dtype=float)
    base = float(np.mean(y) if media_entrenamiento is None else media_entrenamiento)
    return {"n": int(len(y)), "mae": float(np.mean(np.abs(y - p))), "mae_promedio": float(np.mean(np.abs(y - base))),
            "spearman": float(spearmanr(y, p).statistic), "pct_a_un_punto": float(100 * np.mean(np.abs(y - p) <= 1))}
