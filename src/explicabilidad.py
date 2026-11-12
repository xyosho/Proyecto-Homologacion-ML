"""SPRINT 4 — Machine Learning explicable: ¿por qué el modelo toma sus decisiones?

SHAP (Lundberg y Lee, 2017) reparte la predicción de cada inscrito entre sus variables, como un "pago justo" en un
juego cooperativo (valores de Shapley). Para un inscrito:

    log-odds predicho = valor base (promedio) + suma de las contribuciones SHAP de sus variables

Como las contribuciones SE SUMAN, se pueden agrupar variables que miden la misma idea (por ejemplo, la beca, el
descuento y el valor neto forman "Beca y precio"). Eso hace la explicación legible para las directivas.

LIME (Ribeiro et al., 2016) es otra mirada: ajusta un modelo lineal sencillo alrededor de UN inscrito, con datos
simulados parecidos a él. Si SHAP y LIME señalan los mismos factores, la explicación es más confiable.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from caracteristicas import NOMBRE_TIPO_COLEGIO

# Variables agrupadas en conceptos de negocio (contribuciones SHAP sumadas)
GRUPOS_MATRICULA = {
    "Beca y precio": ["beca", "pct_descuento_inicial", "valor_neto_primer_semestre"],
    "Puntaje Saber 11": ["punt_global", "icfes_al_cuadrado"],
    "Distancia al campus": ["log_distancia"],
    "Canal de captación": ["canal", "captado_en_evento"],
    "Entrevista vocacional": ["entrevista_realizada", "indice_vocacional"],
    "Apoyo FOES municipal": ["apoyo_foes", "elegible_foes"],
    "Estrato y régimen de salud": ["estrato", "regimen_salud"],
    "Programa": ["programa"],
    "Ingreso a mitad de año": ["semestre_2"],
    "Colegio de procedencia": ["tipo_colegio", "colegio_privado", "colegio_en_convenio"],
    "Rendimiento en el colegio": ["promedio_acumulado_colegio", "brecha_colegio_vs_icfes"],
    "Contacto con asesores": ["contactos_antes_de_inscribirse", "dias_registro_a_inscripcion"],
    "Edad y años desde el Saber 11": ["edad_al_inscribirse", "anios_desde_saber11"],
    "Segmento de mercado": ["segmento_mercado"],
    "Género": ["genero"],
}

def _variable_de(columna: str, variables: dict) -> str:
    """Nombre original de una columna transformada (canal_REFERIDO -> canal)."""
    if columna in variables["numericas"] + variables["binarias"]:
        return columna
    return next(c for c in variables["categoricas"] if columna.startswith(c + "_"))


def contribuciones(modelo, X_fondo: pd.DataFrame, X: pd.DataFrame, variables: dict) -> tuple[pd.DataFrame, float]:
    """Valores SHAP en log-odds, ya agregados por variable ORIGINAL. Devuelve (tabla n × variables, valor base)."""
    import shap
    prep, clf = modelo.named_steps["preparacion"], modelo.named_steps["modelo"]
    nombres = list(prep.get_feature_names_out())
    T_fondo, T = prep.transform(X_fondo), prep.transform(X)
    if hasattr(clf, "coef_"):            # regresión logística: SHAP lineal (exacto)
        explicador = shap.LinearExplainer(clf, shap.maskers.Independent(T_fondo, max_samples=len(T_fondo)))
    else:                                # árboles (Random Forest, XGBoost): TreeSHAP con 100 casos de referencia
        explicador = shap.TreeExplainer(clf, data=T_fondo[:100], model_output="raw", feature_perturbation="interventional")
    exp = explicador(T)
    valores = exp.values[..., 1] if exp.values.ndim == 3 else exp.values
    base = exp.base_values[..., 1] if np.ndim(exp.base_values) == 2 else exp.base_values
    tabla = pd.DataFrame(valores, columns=nombres, index=X.index)
    tabla = tabla.T.groupby([_variable_de(c, variables) for c in nombres]).sum().T
    return tabla[[c for c in X.columns if c in tabla.columns]], float(np.mean(base))


def agrupar(contrib: pd.DataFrame, grupos: dict) -> pd.DataFrame:
    """Suma las contribuciones de las variables de cada concepto (SHAP es aditivo)."""
    return pd.DataFrame({g: contrib[[v for v in vs if v in contrib]].sum(axis=1) for g, vs in grupos.items()})


def importancia(contrib: pd.DataFrame) -> pd.Series:
    """Importancia global = promedio del valor absoluto de la contribución (cuánto mueve, en cualquier sentido)."""
    return contrib.abs().mean().sort_values(ascending=False)


def contexto(fila: pd.Series, grupo: str) -> str:
    """Dato concreto que acompaña a cada factor en la explicación en español."""
    f = fila
    textos = {
        "Beca y precio": lambda: f"beca {str(f['beca']).replace('_', ' ').title()}, descuento {float(f['pct_descuento_inicial']):.0%}",
        "Puntaje Saber 11": lambda: f"puntaje global {int(f['punt_global'])}",
        "Distancia al campus": lambda: f"vive a {float(np.exp(f['log_distancia'])):.0f} km por vía",
        "Canal de captación": lambda: f"llegó por {str(f['canal']).replace('_', ' ').lower()}",
        "Entrevista vocacional": lambda: (f"índice vocacional {float(f['indice_vocacional']):.0f} de 100" if f["entrevista_realizada"] == 1 else "sin entrevista"),
        "Apoyo FOES municipal": lambda: "con apoyo del fondo municipal" if f.get("apoyo_foes", 0) == 1 else "sin apoyo del fondo municipal",
        "Estrato y régimen de salud": lambda: f"estrato {int(f['estrato'])}",
        "Programa": lambda: f"programa {f['programa']}",
        "Ingreso a mitad de año": lambda: "ingresa en el segundo periodo del año" if f["semestre_2"] == 1 else "ingresa en el primer periodo del año",
        "Rendimiento en el colegio": lambda: f"promedio del colegio {float(f['promedio_acumulado_colegio']):.2f}",
        "Colegio de procedencia": lambda: f"colegio {NOMBRE_TIPO_COLEGIO.get(str(f['tipo_colegio']), str(f['tipo_colegio']).lower())}",
        "Contacto con asesores": lambda: f"{int(f['contactos_antes_de_inscribirse'])} contactos antes de inscribirse",
        "Edad y años desde el Saber 11": lambda: f"{int(f['edad_al_inscribirse'])} años",
        "Segmento de mercado": lambda: str(f["segmento_mercado"]),
        "Género": lambda: f"género {f['genero']}",
    }
    try:
        return textos[grupo]()
    except (KeyError, ValueError, TypeError):
        return ""


def top_factores(por_grupo: pd.DataFrame, X: pd.DataFrame, ids: pd.Series, k: int = 3, que: str = "matricularse") -> pd.DataFrame:
    """Bloque 4 del dashboard: los k conceptos que más mueven la predicción de cada inscrito, en español."""
    filas = []
    for (idx, contrib), iid in zip(por_grupo.iterrows(), ids):
        for orden, (grupo, valor) in enumerate(contrib.reindex(contrib.abs().sort_values(ascending=False).index)[:k].items(), 1):
            sube = valor > 0
            dato = contexto(X.loc[idx], grupo)
            filas.append({"inscripcion_id": int(iid), "orden": orden, "factor": grupo,
                          "direccion": "SUBE" if sube else "BAJA", "contribucion_log_odds": round(float(valor), 4),
                          "texto": f"{grupo}{f' ({dato})' if dato else ''}: {'aumenta' if sube else 'reduce'} la probabilidad de {que}."})
    return pd.DataFrame(filas)


def explicar_lime(modelo, X_ref: pd.DataFrame, fila: pd.DataFrame, variables: dict, n_variables: int = 8,
                  semilla: int = 11) -> list[tuple[str, float]]:
    """LIME: modelo lineal local alrededor de un inscrito. Las categorías se codifican como números para LIME."""
    from lime.lime_tabular import LimeTabularExplainer
    cols = list(X_ref.columns)
    cats = [cols.index(c) for c in variables["categoricas"]]
    niveles = {cols[i]: sorted(X_ref[cols[i]].unique()) for i in cats}

    def codificar(df: pd.DataFrame) -> np.ndarray:
        A = df.copy()
        for c, nv in niveles.items():
            A[c] = A[c].map({v: k for k, v in enumerate(nv)}).fillna(0)
        return A.to_numpy(float)

    def decodificar(A: np.ndarray) -> pd.DataFrame:
        df = pd.DataFrame(A, columns=cols)
        for c, nv in niveles.items():
            df[c] = [nv[int(round(min(max(v, 0), len(nv) - 1)))] for v in df[c]]
        for c in variables["numericas"] + variables["binarias"]:
            df[c] = df[c].astype(float)
        return df

    explicador = LimeTabularExplainer(codificar(X_ref), feature_names=cols, categorical_features=cats,
                                      categorical_names={i: niveles[cols[i]] for i in cats}, class_names=["no", "sí"],
                                      discretize_continuous=True, random_state=semilla, mode="classification")
    exp = explicador.explain_instance(codificar(fila)[0], lambda A: modelo.predict_proba(decodificar(A)),
                                      num_features=n_variables, num_samples=3000)
    return exp.as_list()


def importancia_permutacion(modelo, X: pd.DataFrame, y, grupos: dict, repeticiones: int = 10,
                            semilla: int = 5) -> pd.DataFrame:
    """Chequeo independiente de SHAP: se DESORDENA un concepto (todas sus columnas a la vez) y se mide cuánto cae el
    AUC. Si cae mucho, el modelo dependía de ese concepto. No usa los valores SHAP: es otra forma de verlo."""
    from sklearn.metrics import roc_auc_score
    rng = np.random.default_rng(semilla)
    auc_base = roc_auc_score(y, modelo.predict_proba(X)[:, 1])
    filas = []
    for grupo, cols in grupos.items():
        cols = [c for c in cols if c in X]
        caidas = []
        for _ in range(repeticiones):
            Xp = X.copy()
            orden = rng.permutation(len(X))
            Xp[cols] = X[cols].to_numpy()[orden]
            caidas.append(auc_base - roc_auc_score(y, modelo.predict_proba(Xp)[:, 1]))
        filas.append({"concepto": grupo, "caida_auc": float(np.mean(caidas)), "de_caida": float(np.std(caidas))})
    return pd.DataFrame(filas).sort_values("caida_auc", ascending=False).reset_index(drop=True)


def chequeos_coherencia(X: pd.DataFrame, contrib: pd.DataFrame, por_grupo: pd.DataFrame, prob: np.ndarray,
                        y_real: pd.Series | None = None) -> pd.DataFrame:
    """¿El modelo respeta las reglas de negocio? Cada fila es una afirmación verificable con los datos."""
    from scipy.stats import spearmanr
    saber = contrib[["punt_global", "icfes_al_cuadrado"]].sum(axis=1)
    banda = pd.cut(X["punt_global"], [0, 230, 290, 330, 600], labels=["< 230", "230-289", "290-329", "≥ 330"])
    por_banda = saber.groupby(banda, observed=True).mean()
    beca = contrib["beca"].groupby(X["beca"]).mean()
    imp = importancia(por_grupo)
    filas = [
        ("Más descuento → más probabilidad de matrícula",
         spearmanr(X["pct_descuento_inicial"], contrib["pct_descuento_inicial"] + contrib["valor_neto_primer_semestre"]).statistic > 0,
         "correlación entre descuento y su contribución SHAP (con el valor neto) > 0"),
        ("Las becas pesan a favor frente a no tener beca",
         bool(beca.get("SABER_11", 0) > beca.get("NINGUNA", 0) and beca.get("MI_VOCACION", 0) > beca.get("NINGUNA", 0)),
         "contribución media de la beca: " + ", ".join(f"{k} {v:+.2f}" for k, v in beca.items())),
        ("Más distancia → menos probabilidad",
         spearmanr(X["log_distancia"], contrib["log_distancia"]).statistic < 0, "correlación entre distancia y su contribución < 0"),
        ("Saber 11 en U invertida: los puntajes muy altos tienen más opciones y se matriculan menos",
         bool(por_banda.iloc[-1] < por_banda.iloc[1:3].max()),
         "contribución media por banda: " + ", ".join(f"{k} {v:+.2f}" for k, v in por_banda.items())),
        ("La entrevista vocacional pesa a favor",
         bool(contrib["entrevista_realizada"][X["entrevista_realizada"] == 1].mean() > contrib["entrevista_realizada"][X["entrevista_realizada"] == 0].mean()),
         "contribución media con entrevista > sin entrevista"),
        ("El género NO domina las decisiones",
         bool(list(imp.index).index("Género") >= len(imp) // 2 and imp["Género"] < 0.15 * imp.iloc[0]),
         f"puesto {list(imp.index).index('Género') + 1} de {len(imp)}; importancia {imp['Género']:.3f} vs. {imp.iloc[0]:.3f} del primero"),
    ]
    if y_real is not None:
        tasas = pd.DataFrame({"predicha": pd.Series(prob, index=X.index), "real": y_real.astype(float)}).groupby(X["genero"]).mean()
        brecha_pred = abs(tasas.loc["F", "predicha"] - tasas.loc["M", "predicha"])
        brecha_real = abs(tasas.loc["F", "real"] - tasas.loc["M", "real"])
        filas.append(("Paridad por género: el modelo no crea una brecha que no exista en los datos",
                      bool(brecha_pred <= brecha_real + 0.03),
                      f"brecha predicha F-M {brecha_pred:.3f} vs. brecha real {brecha_real:.3f}"))
    return pd.DataFrame(filas, columns=["regla", "cumple", "evidencia"])


def comparar_con_generador(X: pd.DataFrame, contrib: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Los datos son sintéticos: se conocen los efectos VERDADEROS (config: generador.matricula).
    ¿La explicación SHAP recupera la dirección de cada efecto real? Las variables sin efecto real deberían pesar poco."""
    from scipy.stats import spearmanr
    b = cfg["generador"]["matricula"]
    canal_shap = (contrib["canal"] + contrib["captado_en_evento"]).groupby(X["canal"]).mean()
    canal_real = pd.Series(b["beta_canal"]).reindex(canal_shap.index)
    estr_shap = contrib["estrato"].groupby(X["estrato"]).mean()
    estr_real = pd.Series({int(k): v for k, v in b["beta_estrato"].items()}).reindex(estr_shap.index)
    sentido = lambda v: "positivo" if v > 0 else "negativo"   # noqa: E731
    filas = [
        ("Descuento (beca)", f"positivo (β = {b['beta_descuento']})",
         sentido(spearmanr(X["pct_descuento_inicial"], contrib["pct_descuento_inicial"] + contrib["valor_neto_primer_semestre"] + contrib["beca"]).statistic)),
        ("Distancia al campus", f"negativo (β = {b['beta_log_distancia']})", sentido(spearmanr(X["log_distancia"], contrib["log_distancia"]).statistic)),
        ("Saber 11 (término cuadrático)", f"U invertida (β = {b['beta_icfes_cuadratico']})",
         "U invertida" if contrib["icfes_al_cuadrado"].corr(X["icfes_al_cuadrado"]) < 0 else "no recupera la U"),
        ("Entrevista vocacional", f"positivo (β = {b['beta_entrevista']})",
         sentido(contrib["entrevista_realizada"].corr(X["entrevista_realizada"]))),
        ("Apoyo FOES", f"positivo (β = {b['beta_foes']})", sentido(contrib["apoyo_foes"].corr(X["apoyo_foes"]))),
        ("Programa SSIA", f"positivo (β = {b['beta_programa_ssia']})",
         sentido(contrib["programa"][X["programa"] == "SSIA"].mean() - contrib["programa"][X["programa"] == "AD"].mean())),
        ("Ingreso a mitad de año", f"negativo (β = {b['beta_periodo_2']})", sentido(contrib["semestre_2"].corr(X["semestre_2"]))),
        ("Canal (orden de los 8 canales)", "inmersión > referido > campus day/convenio > web > redes > llamada > expo",
         f"correlación de Spearman con el orden real = {spearmanr(canal_shap, canal_real).statistic:.2f}"),
        ("Estrato (orden de los 6 estratos)", "estrato 1 el más bajo; 4 el más alto",
         f"correlación de Spearman con el orden real = {spearmanr(estr_shap, estr_real).statistic:.2f}"),
        ("Género (sin efecto real)", "ninguno (β = 0)", f"importancia {contrib['genero'].abs().mean():.3f} log-odds"),
        ("Promedio del colegio (sin efecto real en la matrícula)", "ninguno (β = 0)",
         f"importancia {contrib['promedio_acumulado_colegio'].abs().mean():.3f} log-odds"),
    ]
    tabla = pd.DataFrame(filas, columns=["efecto", "verdadero (generador)", "según SHAP"])
    tabla["coincide"] = [
        (r["según SHAP"] in r["verdadero (generador)"]) if r["según SHAP"] in ("positivo", "negativo", "U invertida")
        else (float(r["según SHAP"].split("= ")[-1]) > 0.5 if "Spearman" in r["según SHAP"]
              else float(r["según SHAP"].split()[1]) < 0.05)
        for _, r in tabla.iterrows()]
    return tabla
