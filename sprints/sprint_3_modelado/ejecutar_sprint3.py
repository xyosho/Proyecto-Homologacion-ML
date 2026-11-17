"""SPRINT 3 — Modelado: la regresión logística mejorada con el puntaje vocacional NLP, frente a la regresión de Poisson,
la binomial negativa, Random Forest y XGBoost.

¿Se matricula el inscrito?  (inscritos con resultado: 2024-1 a 2026-2)
  1. Ajuste de hiperparámetros: regresión logística (C y penalización L1/L2), Poisson y binomial negativa (penalización
     L2; son modelos de conteo y su probabilidad es p = mín(μ, 1)), Random Forest y XGBoost, todos con el
     puntaje vocacional NLP del Sprint 2 (lo que dicen las palabras del aspirante en la entrevista), se entrenan con
     2024-1 a 2025-2 y se miden en VALIDACION (2026-1), por log-loss. Control: la misma logística ajustada SIN el NLP,
     para medir cuánto aporta el texto.
  2. Comparación final: cada modelo, y también la logística del Sprint 2 (sin ajuste), se reentrena con entrenamiento +
     validación y se evalúa UNA vez en PRUEBA (2026-2). Tabla "la logística de la Semana 2 tenía un error del X%,
     este modelo del Y%".
  3. Modelo para usar: el elegido se reentrena con TODO el histórico (2024-1 a 2026-2). Es el que predice la
     campaña 2027-1 (Sprint 5) y el que usa el script del Sprint 6.

Salidas: resultados/ (tablas, métricas, figuras, predicciones) y modelos/ (joblib + metadatos).
Uso:  python sprints/sprint_3_modelado/ejecutar_sprint3.py [--local]
"""
from __future__ import annotations

import json
import sys
import warnings
from datetime import date
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
sys.path.insert(0, str(RAIZ / "src"))
warnings.filterwarnings("ignore", category=UserWarning)

import joblib  # noqa: E402
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.calibration import calibration_curve  # noqa: E402
from sklearn.metrics import confusion_matrix, roc_auc_score, roc_curve  # noqa: E402

import caracteristicas as ca  # noqa: E402
import flujo  # noqa: E402
import modelado as mo  # noqa: E402

RES, FIG, MOD = AQUI / "resultados", AQUI / "resultados" / "figuras", AQUI / "modelos"
AZUL, NARANJA, GRIS = "#1B365D", "#E07B39", "#9AA5B1"
# De más simple a más compleja. Los tres lineales van primero; si empatan (a menos de 0,002 de log-loss), se queda la
# logística, que es la que ya se usa: otro modelo solo la reemplaza si es mejor de verdad.
COMPLEJIDAD = ["logistica", "poisson", "binomial_negativa", "random_forest", "xgboost"]
NOMBRE = {"logistica_sprint2": "Regresión logística (Sprint 2)",
          "logistica_sin_nlp": "Regresión logística ajustada sin NLP (control)",
          "logistica": "Regresión logística ajustada con NLP", "poisson": "Regresión de Poisson con NLP",
          "binomial_negativa": "Regresión binomial negativa con NLP", "random_forest": "Random Forest", "xgboost": "XGBoost"}
VERSION = "s3-" + date.today().isoformat()


def elegir(mejores: dict[str, pd.Series], columna: str, tolerancia: float = 0.002) -> str:
    """El de menor log-loss; si uno más simple está a menos de 0,002, se prefiere el simple (navaja de Occam)."""
    mejor = min(mejores.values(), key=lambda f: f[columna])[columna]
    return next(t for t in COMPLEJIDAD if mejores[t][columna] <= mejor + tolerancia)


def objetivo_matricula(d: pd.DataFrame, ref: dict, cfg: dict) -> dict:
    V2, V = mo.VARIABLES_MATRICULA, mo.VARIABLES_MATRICULA_NLP      # Sprint 2 (sin NLP) · Sprint 3 (con NLP)
    e, v, t = (flujo.conjunto(d, x) for x in ["ENTRENAMIENTO", "VALIDACION", "PRUEBA"])
    ev = flujo.conjunto(d, "ENTRENAMIENTO", "VALIDACION")
    hist = flujo.conjunto(d, "ENTRENAMIENTO", "VALIDACION", "PRUEBA")
    y = lambda x: x["matriculado"].astype(int)          # noqa: E731
    X = lambda x: mo.preparar_X(x, ref, V)              # noqa: E731
    X2 = lambda x: mo.preparar_X(x, ref, V2)            # noqa: E731

    busquedas = {tipo: mo.ajustar_temporal(tipo, cfg, X(e), y(e), X(v), y(v), V) for tipo in COMPLEJIDAD}
    # Control: la misma búsqueda de la logística, sin el puntaje NLP (aísla lo que aporta el texto de la entrevista)
    sin_nlp = mo.ajustar_temporal("logistica", cfg, X2(e), y(e), X2(v), y(v), V2).assign(tipo="logistica_sin_nlp")
    pd.concat([*busquedas.values(), sin_nlp]).drop(columns="parametros").to_csv(
        RES / "matricula_busqueda_hiperparametros.csv", index=False)
    mejores = {tipo: b.iloc[0] for tipo, b in busquedas.items()}
    elegido = elegir(mejores, "log_loss_validacion")

    semilla, c2 = cfg["modelado"]["semilla"], cfg["modelado"]["sprint2_logistica"]
    # La logística del Sprint 2 se reentrena con entrenamiento + validación, igual que los demás (comparación justa)
    modelos = {"logistica_sprint2": mo.construir_pipeline("logistica", c2, V2, semilla).fit(X2(ev), y(ev)),
               "logistica_sin_nlp": mo.construir_pipeline("logistica", sin_nlp.iloc[0]["parametros"], V2, semilla).fit(X2(ev), y(ev))}
    for tipo in COMPLEJIDAD:
        modelos[tipo] = mo.construir_pipeline(tipo, mejores[tipo]["parametros"], V, semilla).fit(X(ev), y(ev))
    prob = {n: m.predict_proba((X2 if n in ("logistica_sprint2", "logistica_sin_nlp") else X)(t))[:, 1]
            for n, m in modelos.items()}
    prueba = {n: mo.metricas(y(t), p, cfg["modelado"]["umbral_clasificacion"]) for n, p in prob.items()}
    for n in prueba:
        prueba[n]["ic95_auc"] = mo.intervalo_bootstrap(y(t), prob[n], lambda a, b, u: roc_auc_score(a, b))
    tabla = mo.tabla_metricas({NOMBRE[n]: prueba[n] for n in ["logistica_sprint2", "logistica_sin_nlp", *COMPLEJIDAD]})
    tabla["log_loss"] = [prueba[n]["log_loss"] for n in ["logistica_sprint2", "logistica_sin_nlp", *COMPLEJIDAD]]
    tabla.to_csv(RES / "matricula_comparacion_prueba.csv", encoding="utf-8-sig")

    # Modelos para usar: reentrenados con TODO el histórico
    final = mo.construir_pipeline(elegido, mejores[elegido]["parametros"], V, semilla).fit(X(hist), y(hist))
    xgb = mo.construir_pipeline("xgboost", mejores["xgboost"]["parametros"], V, semilla).fit(X(hist), y(hist))
    log2 = mo.construir_pipeline("logistica", c2, V2, semilla).fit(X2(hist), y(hist))
    meta = {"objetivo": "matriculado", "tipo": elegido, "parametros": mejores[elegido]["parametros"],
            "variables": V, "entrenado_con": sorted(hist["periodo"].unique()), "n": int(len(hist)),
            "metricas_prueba_2026_2": prueba[elegido], "version": VERSION, "semilla": semilla}
    joblib.dump({"modelo": final, "meta": meta}, MOD / "modelo_matricula.joblib")
    joblib.dump({"modelo": xgb, "meta": meta | {"tipo": "xgboost", "parametros": mejores["xgboost"]["parametros"]}},
                MOD / "modelo_matricula_xgboost.joblib")
    joblib.dump({"modelo": log2, "meta": meta | {"tipo": "logistica", "parametros": c2, "modelo": "Sprint 2 (sin ajuste)",
                                                  "variables": V2, "metricas_prueba_2026_2": prueba["logistica_sprint2"]}},
                MOD / "logistica_sprint2_matricula.joblib")
    (MOD / "modelo_matricula.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    # Conteos: los modelos de Poisson y binomial negativa nacieron para contar. Se compara cuántos matriculados predice
    # cada modelo (suma de probabilidades) frente a los reales, por estrato y por canal, en la prueba 2026-2.
    conteos = []
    for grupo in ("estrato", "canal"):
        real = t.groupby(grupo)["matriculado"].sum()
        for n in ["logistica_sprint2", *COMPLEJIDAD]:
            pred = pd.Series(prob[n], index=t.index).groupby(t[grupo]).sum()
            conteos.append({"agrupacion": grupo, "modelo": NOMBRE[n], "grupos": int(len(real)),
                            "matriculados_reales": int(real.sum()), "matriculados_predichos": float(pred.sum()),
                            "error_absoluto_medio_por_grupo": float((pred - real).abs().mean())})
    conteos = pd.DataFrame(conteos)
    conteos.round(2).to_csv(RES / "conteos_por_grupo_prueba.csv", index=False, encoding="utf-8-sig")
    dispersion = float(modelos["binomial_negativa"].named_steps["modelo"].dispersion_)
    return {"busquedas": busquedas, "sin_nlp": sin_nlp, "mejores": mejores, "elegido": elegido, "prueba": prueba,
            "prob": prob, "y_prueba": y(t), "tabla": tabla, "final": final, "conteos": conteos, "dispersion_nb": dispersion}


def tabla_prediccion(d: pd.DataFrame, ref: dict, cfg: dict, final_m, elegido_m: str) -> pd.DataFrame:
    """Bloque 3 del dashboard: una predicción por inscrito (histórico: dentro del entrenamiento; 2027-1: a futuro)."""
    pm = final_m.predict_proba(mo.preparar_X(d, ref, mo.VARIABLES_MATRICULA_NLP))[:, 1]
    s = cfg["modelado"]["segmentos_propension"]
    pm = np.round(pm, 4)              # el segmento se calcula con la misma probabilidad que se publica (4 decimales)
    return pd.DataFrame({
        "inscripcion_id": d["inscripcion_id"].to_numpy(), "periodo": d["periodo"].to_numpy(),
        "tipo_prediccion": np.where(d["particion"] == "CAMPANA", "CAMPANA_A_FUTURO", "HISTORICO_ENTRENAMIENTO"),
        "modelo_matricula": elegido_m, "prob_matricula": pm,
        "decil_propension": pd.qcut(pd.Series(pm).rank(method="first"), 10, labels=False).to_numpy() + 1,
        "segmento_propension": np.select([pm >= s["ALTA"], pm < s["BAJA"]], ["ALTA", "BAJA"], "MEDIA"),
        "version": VERSION, "fecha_generacion": date.today().isoformat()})


def figuras(r1: dict) -> None:
    t = r1["tabla"]
    fig, ejes = plt.subplots(1, 2, figsize=(13, 4.5))
    colores = [NARANJA, GRIS] + [AZUL] * (len(t) - 2)
    for ax, col, titulo in [(ejes[0], "error_pct", "Error en prueba 2026-2 (% mal clasificados)"),
                            (ejes[1], "auc_roc", "AUC-ROC en prueba 2026-2 (0,5 = azar)")]:
        ax.barh(t.index, t[col], color=colores)
        ax.set_title(titulo)
        for i, v in enumerate(t[col]):
            ax.text(v, i, f" {v:.1f}%" if col == "error_pct" else f" {v:.3f}", va="center", fontsize=9)
        ax.invert_yaxis()
    ejes[1].axvline(0.5, color=GRIS, ls=":")
    plt.tight_layout()
    fig.savefig(FIG / "matricula_comparacion.png", dpi=120)
    plt.close(fig)

    fig, ejes = plt.subplots(1, 2, figsize=(12, 5))
    for n, p in r1["prob"].items():
        fpr, tpr, _ = roc_curve(r1["y_prueba"], p)
        ejes[0].plot(fpr, tpr, label=f"{NOMBRE[n]} (AUC {r1['prueba'][n]['auc_roc']:.3f})")
        frac, media = calibration_curve(r1["y_prueba"], p, n_bins=8, strategy="quantile")
        ejes[1].plot(media, frac, "o-", label=NOMBRE[n])
    ejes[0].plot([0, 1], [0, 1], color=GRIS, ls=":")
    ejes[0].set(title="Curva ROC (prueba 2026-2)", xlabel="falsos positivos", ylabel="verdaderos positivos")
    ejes[1].plot([0, 1], [0, 1], color=GRIS, ls=":", label="calibración perfecta")
    ejes[1].set(title="Calibración: probabilidad predicha vs. tasa real", xlabel="probabilidad predicha", ylabel="tasa real")
    for ax in ejes:
        ax.legend(fontsize=8)
    plt.tight_layout()
    fig.savefig(FIG / "matricula_roc_calibracion.png", dpi=120)
    plt.close(fig)

    cm = confusion_matrix(r1["y_prueba"], r1["prob"][r1["elegido"]] >= 0.5)
    fig, ax = plt.subplots(figsize=(4.8, 4.2))
    ax.imshow(cm, cmap="Blues")
    for (i, j), v in np.ndenumerate(cm):
        ax.text(j, i, f"{v}", ha="center", va="center", fontsize=13, color="white" if v > cm.max() / 2 else "black")
    ax.set_xticks([0, 1], ["predice NO", "predice SÍ"])
    ax.set_yticks([0, 1], ["no se matriculó", "se matriculó"])
    ax.set_title(f"Matriz de confusión · {NOMBRE[r1['elegido']]}")
    plt.tight_layout()
    fig.savefig(FIG / "matricula_matriz_confusion.png", dpi=120)
    plt.close(fig)



def main() -> None:
    for c in (RES, FIG, MOD):
        c.mkdir(parents=True, exist_ok=True)
    f = flujo.cargar_y_construir("local" if "--local" in sys.argv else "auto")
    cfg = ca.configuracion()
    print(f"Datos: {f['origen']}")
    r1 = objetivo_matricula(f["inscritos"], f["referencias"], cfg)
    pred = tabla_prediccion(f["inscritos"], f["referencias"], cfg, r1["final"], r1["elegido"])
    pred.to_csv(RES / "prediccion.csv", index=False, encoding="utf-8-sig")
    base, elegido = r1["prueba"]["logistica_sprint2"], r1["prueba"][r1["elegido"]]
    ic = mo.diferencia_error(r1["y_prueba"], r1["prob"]["logistica_sprint2"], r1["prob"][r1["elegido"]])
    frase = mo.frase_docente(base["error_pct"], elegido["error_pct"], NOMBRE[r1["elegido"]], ic, int(base["n"]))
    # Cuánto aporta el texto: la misma logística ajustada con y sin el puntaje NLP, en los mismos inscritos de la prueba
    ic_nlp = mo.diferencia_error(r1["y_prueba"], r1["prob"]["logistica_sin_nlp"], r1["prob"]["logistica"])
    aporte = {"error_pct_sin_nlp": r1["prueba"]["logistica_sin_nlp"]["error_pct"], "error_pct_con_nlp": r1["prueba"]["logistica"]["error_pct"],
              "auc_sin_nlp": r1["prueba"]["logistica_sin_nlp"]["auc_roc"], "auc_con_nlp": r1["prueba"]["logistica"]["auc_roc"],
              "ic95_diferencia_error_puntos": ic_nlp,
              "parametros_sin_nlp": r1["sin_nlp"].iloc[0]["parametros"]}
    resumen = {"frase_docente": frase, "ic95_diferencia_error_puntos": ic, "aporte_nlp": aporte, "origen_datos": f["origen"],
               "binomial_negativa_dispersion_alpha": r1["dispersion_nb"],
               "conteos_por_grupo_prueba": r1["conteos"].round(3).to_dict(orient="records"),
               "matricula": {"elegido": r1["elegido"], "prueba_2026_2": r1["prueba"],
                             "mejores_validacion": {k: v.drop("parametros").to_dict() | {"parametros": v["parametros"]} for k, v in r1["mejores"].items()}}}
    (RES / "metricas_sprint3.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    figuras(r1)
    print("\nMatrícula (prueba 2026-2):")
    print(r1["tabla"][["n", "error_pct", "auc_roc", "brier", "log_loss"]])
    print(f"Binomial negativa: α estimado = {r1['dispersion_nb']:.2e} (sin sobredispersión: se reduce a Poisson)")
    print(r1["conteos"].round(2).to_string(index=False))
    print(f"Elegido por validación: {NOMBRE[r1['elegido']]} {r1['mejores'][r1['elegido']]['parametros']}")
    print(f"Aporte del NLP (misma logística ajustada): error {aporte['error_pct_sin_nlp']:.1f}% → {aporte['error_pct_con_nlp']:.1f}% · "
          f"AUC {aporte['auc_sin_nlp']:.3f} → {aporte['auc_con_nlp']:.3f} · IC 95% de la diferencia de error: {ic_nlp}")
    print("\n" + frase)


if __name__ == "__main__":
    main()
