"""SPRINT 2 — Ingeniería de características y regresión logística (genera todo el entregable de la Semana 2).

Pasos:
  1. Lee dataset_matricula y las respuestas de la entrevista, dataset_entrevista (Supabase por la API de solo
     lectura; sin credenciales, los CSV).
  2. Aprende con el ENTRENAMIENTO (2024-1 a 2025-2) las referencias: estandarización, segmentos de k-means y el
     modelo NLP que lee el puntaje vocacional en las palabras del aspirante (src/caracteristicas.py,
     src/nlp_vocacion.py). Lo mide en la validación (2026-1).
  3. Muestra las palabras que determinan la vocación en cada sección de la entrevista.
  4. Construye la misma tabla con 14 columnas nuevas para TODOS los inscritos.
  5. Entrena la REGRESIÓN LOGÍSTICA, el modelo base del proyecto (sin ajuste de hiperparámetros, C = 1), con el
     entrenamiento y la evalúa en validación (2026-1) y prueba (2026-2).
  6. Guarda: resultados/dataset_caracteristicas.csv y .xlsx, referencias_caracteristicas.joblib, métricas y figuras.

Uso:  python sprints/sprint_2_caracteristicas/ejecutar_sprint2.py [--local]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
sys.path.insert(0, str(RAIZ / "src"))

import joblib  # noqa: E402
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import caracteristicas as ca  # noqa: E402
import datos  # noqa: E402
import graficas_sprint2 as gr  # noqa: E402
import modelado as mo  # noqa: E402
import nlp_vocacion as nv  # noqa: E402

RES = AQUI / "resultados"
FIG = RES / "figuras"


COLUMNAS_MATRICULA = ["segmento_rendimiento_icfes", "aplica_beca_mi_vocacion", "canal_agrupado", "zona_distancia",
                      "estrato_grupo", "rezago_saber11"]


def figuras(d: pd.DataFrame, ref: dict, metr: pd.DataFrame) -> None:
    """Gráficas en español sencillo (src/graficas_sprint2.py): las mismas que muestra el cuaderno."""
    ent = d[d["particion"] == "ENTRENAMIENTO"]
    for nombre, fig in [("kmeans_eleccion_k", gr.eleccion_k(ref)),
                        ("segmentos_mapa", gr.mapa_segmentos(d, ref)),
                        ("segmentos_perfil", gr.perfil_segmentos(d)),
                        ("segmentos_tamano_y_matricula", gr.tamano_y_matricula(d)),
                        ("tasa_por_caracteristica", gr.matricula_por_grupo(ent, COLUMNAS_MATRICULA)),
                        ("nlp_palabras_clave", gr.palabras_nlp(nv.palabras_clave(ref["nlp"]))),
                        ("nlp_puntaje_vocacional", gr.puntaje_nlp(d, "VALIDACION")),
                        ("logistica_error", gr.error_logistica(metr))]:
        fig.savefig(FIG / f"{nombre}.png", dpi=120, bbox_inches="tight")
        plt.close(fig)


def metricas_nlp(d: pd.DataFrame, ref: dict) -> dict:
    """Qué tan bien lee el NLP el puntaje del entrevistador (entrenamiento: fuera de pliegue; validación: modelo
    completo) y, como control de verosimilitud del supuesto S-49, el AUC del puntaje NLP solo frente a la matrícula."""
    from sklearn.metrics import roc_auc_score
    salida = {}
    for conjunto in ["ENTRENAMIENTO", "VALIDACION"]:
        x = d[(d["particion"] == conjunto) & d["puntaje_vocacional_nlp"].notna()]
        salida[conjunto] = nv.metricas(x["puntaje_vocacional"], x["puntaje_vocacional_nlp"], ref["nlp"]["media_entrenamiento"]) | {
            "auc_matricula_solo_nlp": float(roc_auc_score(x["matriculado"].astype(int), x["puntaje_vocacional_nlp"])),
            "auc_matricula_solo_entrevistador": float(roc_auc_score(x["matriculado"].astype(int), x["puntaje_vocacional"]))}
    return salida


def main() -> None:
    RES.mkdir(exist_ok=True)
    FIG.mkdir(exist_ok=True)
    fuente = "local" if "--local" in sys.argv else "auto"
    ins, origen = datos.cargar_inscritos(fuente)
    print(f"Datos: {len(ins):,} inscritos, {int(ins['entrevista_realizada'].sum()):,} con entrevista · origen: {origen}")

    ref = ca.ajustar_referencias(ins)
    d = ca.construir_caracteristicas(ins, ref)
    print(f"Columnas nuevas: {len(ca.NUEVAS)} · segmentos de mercado (k-means): k = {ref['kmeans']['k']}")
    metr_nlp = metricas_nlp(d, ref)
    print(f"NLP (validación 2026-1): MAE {metr_nlp['VALIDACION']['mae']:.2f} frente a {metr_nlp['VALIDACION']['mae_promedio']:.2f} "
          f"de predecir el promedio · Spearman {metr_nlp['VALIDACION']['spearman']:.2f} · "
          f"AUC del puntaje NLP solo {metr_nlp['VALIDACION']['auc_matricula_solo_nlp']:.3f}")

    cfg = ca.configuracion()
    V = mo.VARIABLES_MATRICULA
    ent = d[d["particion"] == "ENTRENAMIENTO"]
    # Regresión logística con los hiperparámetros fijados ANTES de ver resultados (modelado.sprint2_logistica)
    logistica = mo.construir_pipeline("logistica", cfg["modelado"]["sprint2_logistica"], V,
                                      cfg["modelado"]["semilla"]).fit(mo.preparar_X(ent, ref, V), ent["matriculado"].astype(int))
    resultados = {}
    for conjunto in ["VALIDACION", "PRUEBA"]:
        X = d[d["particion"] == conjunto]
        resultados[conjunto] = mo.metricas(X["matriculado"], logistica.predict_proba(mo.preparar_X(X, ref, V))[:, 1])
    metr = pd.DataFrame(resultados).T
    metr.index.name = "conjunto"
    print(metr[["n", "error_pct", "auc_roc", "brier"]].astype(float).round(3))

    d.to_csv(RES / "dataset_caracteristicas.csv", index=False, encoding="utf-8-sig")
    diccionario = pd.DataFrame({"columna": list(ca.DICCIONARIO), "descripcion": list(ca.DICCIONARIO.values())})
    preguntas = pd.DataFrame(cfg["generador"]["entrevista_texto"]["preguntas"]).rename(columns={"id": "pregunta_id"})
    clf = logistica.named_steps["modelo"]
    coeficientes = pd.DataFrame({"variable": logistica.named_steps["preparacion"].get_feature_names_out(),
                                 "coeficiente": clf.coef_[0]}).assign(
        odds_ratio=lambda t: np.exp(t["coeficiente"])).sort_values("coeficiente", key=abs, ascending=False)
    segmentos = ca.tabla_segmentos(d)
    segmentos.to_csv(RES / "tabla_segmentos.csv", encoding="utf-8-sig")
    por_grupo = gr.tabla_matricula_por_grupo(d[d["particion"] == "ENTRENAMIENTO"], COLUMNAS_MATRICULA)
    por_grupo.to_csv(RES / "tabla_matricula_por_grupo.csv", index=False, encoding="utf-8-sig")
    with pd.ExcelWriter(RES / "dataset_caracteristicas.xlsx", engine="openpyxl") as w:
        d.to_excel(w, sheet_name="dataset_caracteristicas", index=False)
        diccionario.to_excel(w, sheet_name="columnas_nuevas", index=False)
        preguntas.to_excel(w, sheet_name="preguntas_entrevista", index=False)
        nv.palabras_clave(ref["nlp"], 15).to_excel(w, sheet_name="nlp_palabras_clave", index=False)
        pd.DataFrame(metr_nlp).T.round(4).to_excel(w, sheet_name="nlp_metricas")
        pd.DataFrame(ref["kmeans"]["evaluacion"]).to_excel(w, sheet_name="kmeans_eleccion_k", index=False)
        segmentos.to_excel(w, sheet_name="segmentos_mercado")
        por_grupo.to_excel(w, sheet_name="matricula_por_grupo", index=False)
        coeficientes.round(4).to_excel(w, sheet_name="logistica_coeficientes", index=False)
        metr.astype(float).round(4).to_excel(w, sheet_name="logistica_metricas")
    joblib.dump({"referencias": ref, "logistica_sprint2": logistica}, RES / "referencias_caracteristicas.joblib")
    (RES / "metricas_logistica_sprint2.json").write_text(json.dumps(
        {f"logistica_sprint2|{c}": v for c, v in resultados.items()} | {"origen_datos": origen}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    (RES / "metricas_nlp_vocacion.json").write_text(json.dumps(
        metr_nlp | {"alpha_ridge": ref["nlp"]["alpha"], "terminos": ref["nlp"]["n_terminos"],
                    "entrevistas_entrenamiento": ref["nlp"]["n_entrevistas"], "origen_datos": origen},
        ensure_ascii=False, indent=2), encoding="utf-8")
    figuras(d, ref, metr.astype(float))
    print(f"Listo: {RES.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
