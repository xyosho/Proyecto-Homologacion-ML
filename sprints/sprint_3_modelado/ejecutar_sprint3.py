"""SPRINT 3 — Modelado: modelo base vs. modelos de Machine Learning para los dos objetivos.

OBJETIVO 1 · ¿Se matricula el inscrito?  (inscritos con resultado: 2024-1 a 2026-2)
  1. Ajuste de hiperparámetros: se entrena con 2024-1 a 2025-2 y se mide en VALIDACION (2026-1), por log-loss.
  2. Comparación final: cada modelo se reentrena con entrenamiento + validación y se evalúa UNA vez en PRUEBA (2026-2).
     Tabla "el modelo base tenía un error del X%, este modelo del Y%".
  3. Modelo para usar: el elegido se reentrena con TODO el histórico (2024-1 a 2026-2). Es el que predice la
     campaña 2027-1 (Sprint 5) y el que usa el script del Sprint 6.

OBJETIVO 2 · ¿Pierde la beca al cerrar el primer semestre?  (557 becados matriculados con el semestre cerrado)
  Pocos datos: ajuste con validación cruzada de 5 pliegues dentro del entrenamiento (2024-1 a 2025-2) y prueba con
  2026-1 (la cohorte 2026-2 aún no cierra semestre). Intervalos de confianza por bootstrap.

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
from sklearn.metrics import confusion_matrix, precision_score, recall_score, roc_auc_score, roc_curve  # noqa: E402

import caracteristicas as ca  # noqa: E402
import flujo  # noqa: E402
import modelado as mo  # noqa: E402

RES, FIG, MOD = AQUI / "resultados", AQUI / "resultados" / "figuras", AQUI / "modelos"
AZUL, NARANJA, GRIS, VERDE = "#1B365D", "#E07B39", "#9AA5B1", "#2E7D5B"
COMPLEJIDAD = ["logistica", "random_forest", "xgboost"]          # de más simple a más compleja
NOMBRE = {"modelo_base": "Modelo base (Sprint 2)", "logistica": "Regresión logística",
          "random_forest": "Random Forest", "xgboost": "XGBoost", "clase_mayoritaria": "Referencia: clase mayoritaria"}
VERSION = "s3-" + date.today().isoformat()


def elegir(mejores: dict[str, pd.Series], columna: str, tolerancia: float = 0.002) -> str:
    """El de menor log-loss; si uno más simple está a menos de 0,002, se prefiere el simple (navaja de Occam)."""
    mejor = min(mejores.values(), key=lambda f: f[columna])[columna]
    return next(t for t in COMPLEJIDAD if mejores[t][columna] <= mejor + tolerancia)


def objetivo_matricula(d: pd.DataFrame, ref: dict, cfg: dict) -> dict:
    V = mo.VARIABLES_MATRICULA
    e, v, t = (flujo.conjunto(d, x) for x in ["ENTRENAMIENTO", "VALIDACION", "PRUEBA"])
    ev = flujo.conjunto(d, "ENTRENAMIENTO", "VALIDACION")
    hist = flujo.conjunto(d, "ENTRENAMIENTO", "VALIDACION", "PRUEBA")
    y = lambda x: x["matriculado"].astype(int)          # noqa: E731
    X = lambda x: mo.preparar_X(x, ref, V)              # noqa: E731

    busquedas = {tipo: mo.ajustar_temporal(tipo, cfg, X(e), y(e), X(v), y(v), V) for tipo in COMPLEJIDAD}
    pd.concat(busquedas.values()).drop(columns="parametros").to_csv(RES / "matricula_busqueda_hiperparametros.csv", index=False)
    mejores = {tipo: b.iloc[0] for tipo, b in busquedas.items()}
    elegido = elegir(mejores, "log_loss_validacion")

    m_base = cfg["caracteristicas"]["peso_previo_modelo_base"]
    modelos = {"modelo_base": mo.ModeloBase(m=m_base).fit(ev, ev["matriculado"]),
               "clase_mayoritaria": mo.ClaseMayoritaria().fit(ev, ev["matriculado"])}
    for tipo in COMPLEJIDAD:
        modelos[tipo] = mo.construir_pipeline(tipo, mejores[tipo]["parametros"], V, cfg["modelado"]["semilla"]).fit(X(ev), y(ev))
    prob = {n: (m.predict_proba(t)[:, 1] if n in ("modelo_base", "clase_mayoritaria") else m.predict_proba(X(t))[:, 1])
            for n, m in modelos.items()}
    prueba = {n: mo.metricas(y(t), p, cfg["modelado"]["umbral_clasificacion"]) for n, p in prob.items()}
    for n in prueba:
        prueba[n]["ic95_auc"] = mo.intervalo_bootstrap(y(t), prob[n], lambda a, b, u: roc_auc_score(a, b))
    tabla = mo.tabla_metricas({NOMBRE[n]: prueba[n] for n in ["clase_mayoritaria", "modelo_base", *COMPLEJIDAD]})
    tabla.to_csv(RES / "matricula_comparacion_prueba.csv", encoding="utf-8-sig")

    # Modelos para usar: reentrenados con TODO el histórico
    final = mo.construir_pipeline(elegido, mejores[elegido]["parametros"], V, cfg["modelado"]["semilla"]).fit(X(hist), y(hist))
    xgb = mo.construir_pipeline("xgboost", mejores["xgboost"]["parametros"], V, cfg["modelado"]["semilla"]).fit(X(hist), y(hist))
    base_final = mo.ModeloBase(m=m_base).fit(hist, hist["matriculado"])
    meta = {"objetivo": "matriculado", "tipo": elegido, "parametros": mejores[elegido]["parametros"],
            "variables": V, "entrenado_con": sorted(hist["periodo"].unique()), "n": int(len(hist)),
            "metricas_prueba_2026_2": prueba[elegido], "version": VERSION, "semilla": cfg["modelado"]["semilla"]}
    joblib.dump({"modelo": final, "meta": meta}, MOD / "modelo_matricula.joblib")
    joblib.dump({"modelo": xgb, "meta": meta | {"tipo": "xgboost", "parametros": mejores["xgboost"]["parametros"]}},
                MOD / "modelo_matricula_xgboost.joblib")
    joblib.dump({"modelo": base_final, "meta": {"tipo": "modelo_base", "entrenado_con": meta["entrenado_con"]}},
                MOD / "modelo_base_matricula.joblib")
    (MOD / "modelo_matricula.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return {"busquedas": busquedas, "mejores": mejores, "elegido": elegido, "prueba": prueba, "prob": prob,
            "y_prueba": y(t), "tabla": tabla, "final": final}


def objetivo_beca(p: pd.DataFrame, ref: dict, cfg: dict) -> dict:
    V = mo.VARIABLES_BECA
    b = p[p["becado"] == 1]
    e, t = flujo.conjunto(b, "ENTRENAMIENTO"), flujo.conjunto(b, "VALIDACION")
    y = lambda x: x["perdio_beca_semestre_1"].astype(int)   # noqa: E731
    X = lambda x: mo.preparar_X(x, ref, V)                  # noqa: E731
    busquedas = {tipo: mo.ajustar_cv(tipo, cfg, X(e), y(e), V) for tipo in COMPLEJIDAD}
    pd.concat(busquedas.values()).drop(columns="parametros").to_csv(RES / "beca_busqueda_hiperparametros.csv", index=False)
    mejores = {tipo: r.iloc[0] for tipo, r in busquedas.items()}
    elegido = elegir(mejores, "log_loss_cv")
    m_base = cfg["caracteristicas"]["peso_previo_modelo_base"]
    modelos = {"modelo_base": mo.ModeloBase(grupo=("beca", "segmento_rendimiento_icfes"), m=m_base).fit(e, e["perdio_beca_semestre_1"]),
               "clase_mayoritaria": mo.ClaseMayoritaria().fit(e, e["perdio_beca_semestre_1"])}
    for tipo in COMPLEJIDAD:
        modelos[tipo] = mo.construir_pipeline(tipo, mejores[tipo]["parametros"], V, cfg["modelado"]["semilla"]).fit(X(e), y(e))
    prob = {n: (m.predict_proba(t)[:, 1] if n in ("modelo_base", "clase_mayoritaria") else m.predict_proba(X(t))[:, 1])
            for n, m in modelos.items()}
    prueba = {n: mo.metricas(y(t), q) for n, q in prob.items()}
    for n in prueba:
        prueba[n]["ic95_auc"] = mo.intervalo_bootstrap(y(t), prob[n], lambda a, q, u: roc_auc_score(a, q))
        prueba[n]["ic95_recall"] = mo.intervalo_bootstrap(y(t), prob[n], lambda a, q, u: recall_score(a, q >= u))
        prueba[n]["ic95_precision"] = mo.intervalo_bootstrap(y(t), prob[n], lambda a, q, u: precision_score(a, q >= u, zero_division=0))
    tabla = mo.tabla_metricas({NOMBRE[n]: prueba[n] for n in ["clase_mayoritaria", "modelo_base", *COMPLEJIDAD]})
    tabla.to_csv(RES / "beca_comparacion_prueba.csv", encoding="utf-8-sig")
    # Certeza en el grupo de mayor riesgo: de los marcados, ¿cuántos pierden de verdad la beca? (precisión por corte)
    orden = np.argsort(-prob[elegido])
    yt = y(t).to_numpy()[orden]
    cortes = pd.DataFrame([{"pct_marcado": q, "marcados": int(round(q * len(yt))),
                            "pierden_entre_marcados": float(yt[: int(round(q * len(yt)))].mean()),
                            "pct_de_los_que_pierden_detectados": float(yt[: int(round(q * len(yt)))].sum() / yt.sum())}
                           for q in [0.1, 0.2, 0.3, 0.4, 0.5]])
    cortes.to_csv(RES / "beca_certeza_por_grupo_de_riesgo.csv", index=False)
    final = mo.construir_pipeline(elegido, mejores[elegido]["parametros"], V, cfg["modelado"]["semilla"]).fit(X(b), y(b))
    meta = {"objetivo": "perdio_beca_semestre_1", "tipo": elegido, "parametros": mejores[elegido]["parametros"],
            "variables": V, "entrenado_con": sorted(b["periodo"].unique()), "n": int(len(b)),
            "metricas_prueba_2026_1": prueba[elegido], "version": VERSION, "semilla": cfg["modelado"]["semilla"]}
    joblib.dump({"modelo": final, "meta": meta}, MOD / "modelo_beca.joblib")
    (MOD / "modelo_beca.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return {"mejores": mejores, "elegido": elegido, "prueba": prueba, "prob": prob, "y_prueba": y(t), "tabla": tabla,
            "cortes": cortes, "final": final}


def tabla_prediccion(d: pd.DataFrame, ref: dict, cfg: dict, final_m, final_b, elegido_m: str, elegido_b: str) -> pd.DataFrame:
    """Bloque 3 del dashboard: una predicción por inscrito (histórico: dentro del entrenamiento; 2027-1: a futuro)."""
    pm = final_m.predict_proba(mo.preparar_X(d, ref, mo.VARIABLES_MATRICULA))[:, 1]
    pb = final_b.predict_proba(mo.preparar_X(d, ref, mo.VARIABLES_BECA))[:, 1]
    s = cfg["modelado"]["segmentos_propension"]
    pm = np.round(pm, 4)              # el segmento se calcula con la misma probabilidad que se publica (4 decimales)
    return pd.DataFrame({
        "inscripcion_id": d["inscripcion_id"].to_numpy(), "periodo": d["periodo"].to_numpy(),
        "tipo_prediccion": np.where(d["particion"] == "CAMPANA", "CAMPANA_A_FUTURO", "HISTORICO_ENTRENAMIENTO"),
        "modelo_matricula": elegido_m, "prob_matricula": pm,
        "decil_propension": pd.qcut(pd.Series(pm).rank(method="first"), 10, labels=False).to_numpy() + 1,
        "segmento_propension": np.select([pm >= s["ALTA"], pm < s["BAJA"]], ["ALTA", "BAJA"], "MEDIA"),
        "modelo_beca": np.where(d["beca"] != "NINGUNA", elegido_b, None),
        "prob_perdida_beca": np.where(d["beca"] != "NINGUNA", pb.round(4), np.nan),
        "version": VERSION, "fecha_generacion": date.today().isoformat()})


def figuras(r1: dict, r2: dict) -> None:
    t = r1["tabla"]
    fig, ejes = plt.subplots(1, 2, figsize=(13, 4.5))
    colores = [GRIS, NARANJA, AZUL, AZUL, AZUL]
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
        if n == "clase_mayoritaria":
            continue
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

    fig, ejes = plt.subplots(1, 2, figsize=(12, 4.5))
    t2 = r2["tabla"]
    ejes[0].barh(t2.index, t2["auc_roc"], color=colores)
    for i, v in enumerate(t2["auc_roc"]):
        ejes[0].text(v, i, f" {v:.3f}", va="center", fontsize=9)
    ejes[0].invert_yaxis()
    ejes[0].axvline(0.5, color=GRIS, ls=":")
    ejes[0].set_title(f"Pérdida de beca: AUC en prueba 2026-1 ({len(r2['y_prueba'])} becados)")
    c = r2["cortes"]
    ejes[1].bar(c["pct_marcado"].map(lambda q: f"{q:.0%}"), 100 * c["pierden_entre_marcados"], color=AZUL)
    ejes[1].axhline(100 * r2["y_prueba"].mean(), color=NARANJA, ls="--", label="tasa general de pérdida")
    ejes[1].set(title="De los marcados como riesgo, % que sí perdió la beca", xlabel="% de becados marcados (mayor riesgo)", ylabel="%")
    ejes[1].legend(fontsize=8)
    plt.tight_layout()
    fig.savefig(FIG / "beca_resultados.png", dpi=120)
    plt.close(fig)


def main() -> None:
    for c in (RES, FIG, MOD):
        c.mkdir(parents=True, exist_ok=True)
    f = flujo.cargar_y_construir("local" if "--local" in sys.argv else "auto")
    cfg = ca.configuracion()
    print(f"Datos: {f['origen']}")
    r1 = objetivo_matricula(f["inscritos"], f["referencias"], cfg)
    r2 = objetivo_beca(f["permanencia"], f["referencias"], cfg)
    pred = tabla_prediccion(f["inscritos"], f["referencias"], cfg, r1["final"], r2["final"], r1["elegido"], r2["elegido"])
    pred.to_csv(RES / "prediccion.csv", index=False, encoding="utf-8-sig")
    base, elegido = r1["prueba"]["modelo_base"], r1["prueba"][r1["elegido"]]
    frase = (f"El cálculo sencillo de la Semana 2 (modelo base) tenía un error del {base['error_pct']:.1f}%, mientras que "
             f"el modelo de la Semana 3 ({NOMBRE[r1['elegido']]}) tiene un error del {elegido['error_pct']:.1f}% "
             f"en los inscritos de 2026-2, que ningún modelo vio al entrenar.")
    resumen = {"frase_docente": frase, "origen_datos": f["origen"],
               "matricula": {"elegido": r1["elegido"], "prueba_2026_2": r1["prueba"],
                             "mejores_validacion": {k: v.drop("parametros").to_dict() | {"parametros": v["parametros"]} for k, v in r1["mejores"].items()}},
               "beca": {"elegido": r2["elegido"], "prueba_2026_1": r2["prueba"], "cortes": r2["cortes"].to_dict(orient="records"),
                        "mejores_cv": {k: v.drop("parametros").to_dict() | {"parametros": v["parametros"]} for k, v in r2["mejores"].items()}}}
    (RES / "metricas_sprint3.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    figuras(r1, r2)
    print("\nOBJETIVO 1 — matrícula (prueba 2026-2):")
    print(r1["tabla"][["n", "error_pct", "auc_roc", "auc_pr", "brier"]])
    print(f"Elegido por validación: {NOMBRE[r1['elegido']]}")
    print("\nOBJETIVO 2 — pérdida de beca (prueba 2026-1):")
    print(r2["tabla"][["n", "error_pct", "auc_roc", "brier", "precision", "recall"]])
    print(r2["cortes"].round(3))
    print(f"Elegido por validación cruzada: {NOMBRE[r2['elegido']]}")
    print("\n" + frase)


if __name__ == "__main__":
    main()
