"""SPRINT 2 — Ingeniería de características y modelo base (genera todo el entregable de la Semana 2).

Pasos:
  1. Lee dataset_matricula y dataset_permanencia (Supabase por la API de solo lectura; sin credenciales, los CSV).
  2. Aprende con el ENTRENAMIENTO (2024-1 a 2025-2) las referencias: acceso a beca, regresión del promedio,
     estandarización y segmentos de k-means (src/caracteristicas.py).
  3. Construye la misma tabla con 15 columnas nuevas para TODOS los inscritos.
  4. Entrena el MODELO BASE (tasa histórica por beca × canal) y lo evalúa en validación (2026-1) y prueba (2026-2).
  5. Guarda: resultados/dataset_caracteristicas.csv y .xlsx, referencias_caracteristicas.joblib, métricas y figuras.

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
import pandas as pd  # noqa: E402

import caracteristicas as ca  # noqa: E402
import datos  # noqa: E402
import graficas_sprint2 as gr  # noqa: E402
import modelado as mo  # noqa: E402

RES = AQUI / "resultados"
FIG = RES / "figuras"


COLUMNAS_MATRICULA = ["segmento_rendimiento_icfes", "aplica_beca_mi_vocacion", "canal_agrupado", "zona_distancia",
                      "estrato_grupo", "rezago_saber11"]


def figuras(d: pd.DataFrame, ref: dict, perm: pd.DataFrame, metr: pd.DataFrame) -> None:
    """Gráficas en español sencillo (src/graficas_sprint2.py): las mismas que muestra el cuaderno."""
    ent = d[d["particion"] == "ENTRENAMIENTO"]
    p_ent = perm[ca.particion_temporal(perm["periodo"]) == "ENTRENAMIENTO"].merge(
        d[["inscripcion_id", "promedio_estimado_universidad"]], on="inscripcion_id")
    for nombre, fig in [("kmeans_eleccion_k", gr.eleccion_k(ref)),
                        ("segmentos_mapa", gr.mapa_segmentos(d, ref)),
                        ("segmentos_perfil", gr.perfil_segmentos(d)),
                        ("segmentos_tamano_y_matricula", gr.tamano_y_matricula(d)),
                        ("tasa_por_caracteristica", gr.matricula_por_grupo(ent, COLUMNAS_MATRICULA)),
                        ("promedio_estimado_vs_real", gr.promedio_estimado(p_ent, ref["regresion_promedio"]["r2"])),
                        ("modelo_base_error", gr.error_modelo_base(metr))]:
        fig.savefig(FIG / f"{nombre}.png", dpi=120, bbox_inches="tight")
        plt.close(fig)


def main() -> None:
    RES.mkdir(exist_ok=True)
    FIG.mkdir(exist_ok=True)
    fuente = "local" if "--local" in sys.argv else "auto"
    ins, origen = datos.cargar("dataset_matricula", fuente)
    perm, _ = datos.cargar("dataset_permanencia", fuente)
    print(f"Datos: {len(ins):,} inscritos y {len(perm):,} matriculados con semestre cerrado · origen: {origen}")

    ref = ca.ajustar_referencias(ins, perm)
    d = ca.construir_caracteristicas(ins, ref)
    print(f"Columnas nuevas: {len(ca.NUEVAS)} · segmentos de mercado (k-means): k = {ref['kmeans']['k']}")

    ent = d[d["particion"] == "ENTRENAMIENTO"]
    base = mo.ModeloBase(m=ca.configuracion()["caracteristicas"]["peso_previo_modelo_base"]).fit(ent, ent["matriculado"])
    mayoria = mo.ClaseMayoritaria().fit(ent, ent["matriculado"])
    resultados = {}
    for conjunto in ["VALIDACION", "PRUEBA"]:
        X = d[d["particion"] == conjunto]
        resultados[("modelo_base", conjunto)] = mo.metricas(X["matriculado"], base.predict_proba(X)[:, 1])
        resultados[("clase_mayoritaria", conjunto)] = mo.metricas(X["matriculado"], mayoria.predict_proba(X)[:, 1])
    metr = pd.DataFrame(resultados).T
    metr.index.names = ["modelo", "conjunto"]
    print(metr[["n", "error_pct", "auc_roc", "brier"]].astype(float).round(3))

    d.to_csv(RES / "dataset_caracteristicas.csv", index=False, encoding="utf-8-sig")
    diccionario = pd.DataFrame({"columna": list(ca.DICCIONARIO), "descripcion": list(ca.DICCIONARIO.values())})
    segmentos = ca.tabla_segmentos(d)
    segmentos.to_csv(RES / "tabla_segmentos.csv", encoding="utf-8-sig")
    por_grupo = gr.tabla_matricula_por_grupo(d[d["particion"] == "ENTRENAMIENTO"], COLUMNAS_MATRICULA)
    por_grupo.to_csv(RES / "tabla_matricula_por_grupo.csv", index=False, encoding="utf-8-sig")
    with pd.ExcelWriter(RES / "dataset_caracteristicas.xlsx", engine="openpyxl") as w:
        d.to_excel(w, sheet_name="dataset_caracteristicas", index=False)
        diccionario.to_excel(w, sheet_name="columnas_nuevas", index=False)
        ref["tabla_acceso_beca"].to_excel(w, sheet_name="acceso_beca")
        pd.DataFrame([ref["regresion_promedio"]["coeficientes"] | {k: v for k, v in ref["regresion_promedio"].items() if k != "coeficientes"}]).to_excel(w, sheet_name="regresion_promedio", index=False)
        pd.DataFrame(ref["kmeans"]["evaluacion"]).to_excel(w, sheet_name="kmeans_eleccion_k", index=False)
        segmentos.to_excel(w, sheet_name="segmentos_mercado")
        por_grupo.to_excel(w, sheet_name="matricula_por_grupo", index=False)
        base.tabla_.round(4).to_excel(w, sheet_name="modelo_base_tabla")
        metr.astype(float).round(4).to_excel(w, sheet_name="modelo_base_metricas")
    joblib.dump({"referencias": ref, "modelo_base": base}, RES / "referencias_caracteristicas.joblib")
    (RES / "metricas_modelo_base.json").write_text(json.dumps(
        {f"{m}|{c}": v for (m, c), v in resultados.items()} | {"origen_datos": origen}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    figuras(d, ref, perm, metr.astype(float))
    print(f"Listo: {RES.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
