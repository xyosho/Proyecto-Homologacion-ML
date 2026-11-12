"""SPRINT 2 — Ingeniería de características y regresión logística (genera todo el entregable de la Semana 2).

Pasos:
  1. Lee dataset_matricula y la rúbrica de la entrevista, dataset_entrevista (Supabase por la API de solo lectura;
     sin credenciales, los CSV).
  2. Convierte la entrevista cualitativa en un número: índice vocacional de 0 a 100 (regla fija, S-46).
  3. Aprende con el ENTRENAMIENTO (2024-1 a 2025-2) las referencias: estandarización y segmentos de k-means
     (src/caracteristicas.py).
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
                        ("indice_vocacional", gr.indice_vocacional(ent)),
                        ("logistica_error", gr.error_logistica(metr))]:
        fig.savefig(FIG / f"{nombre}.png", dpi=120, bbox_inches="tight")
        plt.close(fig)


def main() -> None:
    RES.mkdir(exist_ok=True)
    FIG.mkdir(exist_ok=True)
    fuente = "local" if "--local" in sys.argv else "auto"
    ins, origen = datos.cargar_inscritos(fuente)
    print(f"Datos: {len(ins):,} inscritos, {int(ins['entrevista_realizada'].sum()):,} con entrevista · origen: {origen}")

    ref = ca.ajustar_referencias(ins)
    d = ca.construir_caracteristicas(ins, ref)
    print(f"Columnas nuevas: {len(ca.NUEVAS)} · segmentos de mercado (k-means): k = {ref['kmeans']['k']}")

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
    rubrica = pd.DataFrame({"seccion": ca.DIMENSIONES_ENTREVISTA,
                            "que_califica": [cfg["generador"]["entrevista"]["dimensiones"][c] for c in ca.DIMENSIONES_ENTREVISTA],
                            "escala": "1 = muy débil · 2 = débil · 3 = aceptable · 4 = bueno · 5 = sobresaliente"})
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
        rubrica.to_excel(w, sheet_name="rubrica_entrevista", index=False)
        pd.DataFrame(ref["kmeans"]["evaluacion"]).to_excel(w, sheet_name="kmeans_eleccion_k", index=False)
        segmentos.to_excel(w, sheet_name="segmentos_mercado")
        por_grupo.to_excel(w, sheet_name="matricula_por_grupo", index=False)
        coeficientes.round(4).to_excel(w, sheet_name="logistica_coeficientes", index=False)
        metr.astype(float).round(4).to_excel(w, sheet_name="logistica_metricas")
    joblib.dump({"referencias": ref, "logistica_sprint2": logistica}, RES / "referencias_caracteristicas.joblib")
    (RES / "metricas_logistica_sprint2.json").write_text(json.dumps(
        {f"logistica_sprint2|{c}": v for c, v in resultados.items()} | {"origen_datos": origen}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    figuras(d, ref, metr.astype(float))
    print(f"Listo: {RES.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
