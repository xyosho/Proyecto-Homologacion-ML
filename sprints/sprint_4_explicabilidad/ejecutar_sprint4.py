"""SPRINT 4 — Machine Learning explicable: ¿por qué el modelo toma sus decisiones?

Pasos:
  1. Carga los modelos del Sprint 3 (regresión logística elegida y XGBoost para comparar) y los datos.
  2. SHAP global: qué conceptos mueven más la probabilidad de matrícula, en los dos modelos.
  3. Dependencias: cómo cambia la contribución con el descuento, la distancia y el Saber 11.
  4. Tres inscritos de la campaña 2027-1 (propensión alta, media y baja): SHAP y LIME lado a lado.
  5. Importancia por permutación en la prueba 2026-2 (chequeo independiente de SHAP).
  6. Coherencia con las reglas de negocio, paridad por género y comparación con los efectos VERDADEROS del generador.
  7. Tabla del bloque 4 (top 3 factores por inscrito, en español) y explicación para directivas.

Uso:  python sprints/sprint_4_explicabilidad/ejecutar_sprint4.py [--local]
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
sys.path.insert(0, str(RAIZ / "src"))
warnings.filterwarnings("ignore")

import joblib  # noqa: E402
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import caracteristicas as ca  # noqa: E402
import explicabilidad as ex  # noqa: E402
import flujo  # noqa: E402
import modelado as mo  # noqa: E402

RES, FIG = AQUI / "resultados", AQUI / "resultados" / "figuras"
MOD = RAIZ / "sprints" / "sprint_3_modelado" / "modelos"
AZUL, NARANJA, GRIS = "#1B365D", "#E07B39", "#9AA5B1"


def barras(ax, serie: pd.Series, titulo: str, color=AZUL) -> None:
    s = serie.sort_values()
    ax.barh(s.index, s.values, color=color)
    for i, v in enumerate(s.values):
        ax.text(v, i, f" {v:.3f}", va="center", fontsize=8)
    ax.set_title(titulo)


def cascada(ax, contrib: pd.Series, base: float, prob: float, titulo: str) -> None:
    """Gráfico de cascada: del promedio (valor base) a la probabilidad de este inscrito."""
    c = contrib.reindex(contrib.abs().sort_values(ascending=False).index)
    principales, resto = c[:7], c[7:].sum()
    etiquetas = list(principales.index) + ["Otros factores"]
    valores = list(principales.values) + [resto]
    acumulado = base
    for i, (et, v) in enumerate(zip(etiquetas, valores)):
        ax.barh(i, v, left=acumulado, color=AZUL if v > 0 else NARANJA)
        ax.text(acumulado + v, i, f" {v:+.2f}", va="center", fontsize=8)
        acumulado += v
    ax.set_yticks(range(len(etiquetas)), etiquetas)
    ax.invert_yaxis()
    ax.axvline(base, color=GRIS, ls=":")
    ax.set_title(f"{titulo}\nbase {1 / (1 + np.exp(-base)):.0%} → este inscrito {prob:.0%} (log-odds)", fontsize=10)


def main() -> None:
    RES.mkdir(exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    f = flujo.cargar_y_construir("local" if "--local" in sys.argv else "auto")
    d, ref, cfg = f["inscritos"], f["referencias"], ca.configuracion()
    V = mo.VARIABLES_MATRICULA
    final = joblib.load(MOD / "modelo_matricula.joblib")
    lm, meta = final["modelo"], final["meta"]
    xgb = joblib.load(MOD / "modelo_matricula_xgboost.joblib")["modelo"]
    hist = flujo.conjunto(d, "ENTRENAMIENTO", "VALIDACION", "PRUEBA")
    X_hist, X_todos = mo.preparar_X(hist, ref, V), mo.preparar_X(d, ref, V)
    fondo = X_hist.sample(300, random_state=1)
    print(f"Datos: {f['origen']} · modelo explicado: {meta['tipo']}")

    # 2) SHAP global (histórico) en los dos modelos
    c_lm, base_lm = ex.contribuciones(lm, fondo, X_hist, V)
    c_xg, _ = ex.contribuciones(xgb, fondo, X_hist, V)
    g_lm, g_xg = ex.agrupar(c_lm, ex.GRUPOS_MATRICULA), ex.agrupar(c_xg, ex.GRUPOS_MATRICULA)
    imp = pd.DataFrame({"regresion_logistica": ex.importancia(g_lm), "xgboost": ex.importancia(g_xg)}).sort_values(
        "regresion_logistica", ascending=False)
    imp["pct_del_total_logistica"] = 100 * imp["regresion_logistica"] / imp["regresion_logistica"].sum()
    imp.round(4).to_csv(RES / "importancia_shap_conceptos.csv", encoding="utf-8-sig")
    ex.importancia(c_lm).round(4).to_csv(RES / "importancia_shap_variables.csv", header=["importancia"], encoding="utf-8-sig")
    fig, ejes = plt.subplots(1, 2, figsize=(14, 6))
    barras(ejes[0], imp["regresion_logistica"], "Regresión logística (modelo elegido)")
    barras(ejes[1], imp["xgboost"], "XGBoost (modelo avanzado)", NARANJA)
    fig.suptitle("¿Qué mueve la probabilidad de matrícula? Importancia SHAP media |log-odds|")
    plt.tight_layout()
    fig.savefig(FIG / "shap_importancia_conceptos.png", dpi=120)
    plt.close(fig)

    # Gráfico de puntos tipo "beeswarm": cada punto es un inscrito; color = valor de la variable
    top = ex.importancia(c_lm).index[:10]
    fig, ax = plt.subplots(figsize=(10, 6))
    rng = np.random.default_rng(3)
    for i, v in enumerate(reversed(top)):
        valores = X_hist[v]
        if v in V["categoricas"]:
            color = pd.factorize(valores)[0].astype(float)
        else:
            color = valores.rank(pct=True).to_numpy()
        ax.scatter(c_lm[v], i + rng.uniform(-0.3, 0.3, len(c_lm)), c=color, cmap="coolwarm", s=4, alpha=0.5)
    ax.set_yticks(range(len(top)), list(reversed(top)))
    ax.axvline(0, color=GRIS)
    ax.set(xlabel="contribución SHAP (log-odds): derecha = sube la probabilidad",
           title="Contribución de cada variable por inscrito (rojo = valor alto, azul = valor bajo)")
    plt.tight_layout()
    fig.savefig(FIG / "shap_puntos_variables.png", dpi=120)
    plt.close(fig)

    # 3) Dependencias
    fig, ejes = plt.subplots(1, 4, figsize=(18, 4))
    ejes[0].scatter(X_hist["pct_descuento_inicial"], c_lm[["pct_descuento_inicial", "valor_neto_primer_semestre", "beca"]].sum(axis=1), s=6, alpha=0.4, color=AZUL)
    ejes[0].set(title="Beca y descuento", xlabel="descuento del 1er semestre", ylabel="contribución SHAP")
    ejes[1].scatter(np.exp(X_hist["log_distancia"]), c_lm["log_distancia"], s=6, alpha=0.4, color=AZUL)
    ejes[1].set(title="Distancia al campus", xlabel="km")
    ejes[2].scatter(X_hist["punt_global"], c_lm[["punt_global", "icfes_al_cuadrado"]].sum(axis=1), s=6, alpha=0.4, color=AZUL)
    ejes[2].axvline(310, color=NARANJA, ls="--", label="umbral beca")
    ejes[2].set(title="Saber 11: U invertida", xlabel="puntaje global")
    ejes[2].legend(fontsize=8)
    canal = (c_lm["canal"] + c_lm["captado_en_evento"]).groupby(X_hist["canal"]).mean().sort_values()
    ejes[3].barh(canal.index, canal.values, color=[NARANJA if v < 0 else AZUL for v in canal.values])
    ejes[3].set(title="Canal de captación (contribución media)")
    for ax in ejes[:3]:
        ax.axhline(0, color=GRIS, lw=0.8)
    plt.tight_layout()
    fig.savefig(FIG / "shap_dependencias.png", dpi=120)
    plt.close(fig)

    # 4) Tres casos de la campaña 2027-1: SHAP vs LIME
    camp = flujo.conjunto(d, "CAMPANA")
    X_camp = mo.preparar_X(camp, ref, V)
    prob_camp = pd.Series(lm.predict_proba(X_camp)[:, 1], index=camp.index)
    casos = {nombre: (prob_camp - prob_camp.quantile(q)).abs().idxmin() for nombre, q in [("ALTA", 0.9), ("MEDIA", 0.5), ("BAJA", 0.1)]}
    c_camp, _ = ex.contribuciones(lm, fondo, X_camp.loc[list(casos.values())], V)
    g_camp = ex.agrupar(c_camp, ex.GRUPOS_MATRICULA)
    fig, ejes = plt.subplots(2, 3, figsize=(19, 9))
    filas_casos = []
    for j, (nombre, idx) in enumerate(casos.items()):
        cascada(ejes[0, j], g_camp.loc[idx], base_lm, prob_camp[idx], f"Propensión {nombre} · inscrito {int(camp.loc[idx, 'inscripcion_id'])}")
        lime = ex.explicar_lime(lm, X_hist.sample(800, random_state=2), X_camp.loc[[idx]], V)
        nombres, pesos = zip(*lime)
        ejes[1, j].barh(range(len(pesos)), pesos, color=[AZUL if w > 0 else NARANJA for w in pesos])
        ejes[1, j].set_yticks(range(len(pesos)), nombres, fontsize=7)
        ejes[1, j].invert_yaxis()
        ejes[1, j].set_title(f"LIME (modelo lineal local) · propensión {nombre}", fontsize=10)
        top_shap = list(g_camp.loc[idx].abs().sort_values(ascending=False).index[:3])
        filas_casos.append({"caso": nombre, "inscripcion_id": int(camp.loc[idx, "inscripcion_id"]), "prob_matricula": round(float(prob_camp[idx]), 3),
                            "top3_shap": " | ".join(top_shap), "top3_lime": " | ".join(n for n, _ in lime[:3])})
    plt.tight_layout()
    fig.savefig(FIG / "casos_shap_vs_lime.png", dpi=120)
    plt.close(fig)
    casos_tabla = pd.DataFrame(filas_casos)
    casos_tabla.to_csv(RES / "casos_shap_vs_lime.csv", index=False, encoding="utf-8-sig")

    # 5) Importancia por permutación (modelo reentrenado con entrenamiento + validación, medido en prueba 2026-2)
    ev, t = flujo.conjunto(d, "ENTRENAMIENTO", "VALIDACION"), flujo.conjunto(d, "PRUEBA")
    lm_ev = mo.construir_pipeline(meta["tipo"], meta["parametros"], V, cfg["modelado"]["semilla"]).fit(
        mo.preparar_X(ev, ref, V), ev["matriculado"].astype(int))
    perm = ex.importancia_permutacion(lm_ev, mo.preparar_X(t, ref, V), t["matriculado"].astype(int), ex.GRUPOS_MATRICULA)
    perm.round(4).to_csv(RES / "importancia_permutacion.csv", index=False, encoding="utf-8-sig")

    # 6) Coherencia, paridad y comparación con el generador
    prob_hist = lm.predict_proba(X_hist)[:, 1]
    coherencia = ex.chequeos_coherencia(X_hist, c_lm, g_lm, prob_hist, hist["matriculado"])
    generador = ex.comparar_con_generador(X_hist, c_lm, cfg)
    coherencia.to_csv(RES / "coherencia_reglas_negocio.csv", index=False, encoding="utf-8-sig")
    generador.to_csv(RES / "comparacion_con_efectos_verdaderos.csv", index=False, encoding="utf-8-sig")

    # Referencias que usa el script del Sprint 6 para explicar a un aspirante nuevo sin cargar toda la base
    joblib.dump({"fondo_matricula": fondo, "valor_base_matricula": base_lm},
                RES / "fondo_shap.joblib")

    # 7) Bloque 4: top 3 factores por inscrito (todos, incluida la campaña) + explicación para directivas
    c_todos, _ = ex.contribuciones(lm, fondo, X_todos, V)
    explicacion = ex.top_factores(ex.agrupar(c_todos, ex.GRUPOS_MATRICULA), X_todos, d["inscripcion_id"])
    explicacion.to_csv(RES / "explicacion_prediccion.csv", index=False, encoding="utf-8-sig")
    veces = imp.loc["Puntaje Saber 11", "regresion_logistica"] / imp.loc["Edad y años desde el Saber 11", "regresion_logistica"]
    texto = escribir_explicacion(imp, perm, coherencia, generador, casos_tabla, veces, len(hist))
    (RES / "explicacion_para_directivas.md").write_text(texto, encoding="utf-8")
    (RES / "metricas_sprint4.json").write_text(json.dumps({
        "origen_datos": f["origen"], "modelo": meta["tipo"], "importancia_conceptos": imp["regresion_logistica"].round(4).to_dict(),
        "coherencia_cumple": int(coherencia["cumple"].sum()), "coherencia_total": len(coherencia),
        "generador_coincide": int(generador["coincide"].sum()), "generador_total": len(generador),
        "saber11_vs_edad_veces": round(float(veces), 2)}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(imp.round(3).head(8))
    print(coherencia[["regla", "cumple"]].to_string(index=False))
    print(f"Comparación con el generador: {int(generador['coincide'].sum())} de {len(generador)} efectos coinciden")
    print(f"Explicación del bloque 4: {len(explicacion):,} filas · {RES.relative_to(RAIZ)}")


def escribir_explicacion(imp, perm, coherencia, generador, casos, veces, n_hist: int) -> str:
    n_txt = f"{n_hist:,}".replace(",", ".")
    total = imp["regresion_logistica"].sum()
    top = imp["regresion_logistica"].head(5)
    L = ["# ¿Por qué el modelo toma sus decisiones? (explicación para directivas)", "",
         "El modelo estima, para cada inscrito, la probabilidad de que pague la matrícula. Con la técnica SHAP se mide "
         "cuánto aporta cada factor a esa probabilidad, sumando o restando frente a un inscrito promedio.", "",
         "## Lo que más pesa", ""]
    L += [f"{i}. **{g}** — {100 * v / total:.0f}% del peso total de las explicaciones." for i, (g, v) in enumerate(top.items(), 1)]
    L += ["", f"El modelo le da **{veces:.1f} veces más peso al puntaje Saber 11 que a la edad** del aspirante.", "",
          "## ¿Tiene sentido para la Universidad?", ""]
    L += [f"- {'✅' if r.cumple else '❌'} {r.regla}. ({r.evidencia})" for r in coherencia.itertuples()]
    L += ["", "## ¿El modelo encontró las causas reales?", "",
          "Como los datos son sintéticos, conocemos los efectos verdaderos con los que se generaron. La explicación SHAP "
          f"recupera **{int(generador['coincide'].sum())} de {len(generador)}** efectos:", ""]
    L += [f"- {'✅' if r.coincide else '⚠️'} {r.efecto}: verdadero {r._2}; según el modelo, {r._3}." for r in generador.itertuples()]
    L += ["", f"Los efectos que no recupera son pequeños, tienen pocos casos (con {n_txt} inscritos no se distinguen del azar) "
          "o son asociaciones: el modelo le da peso a algo que en el generador no causa la matrícula porque va de la mano con "
          "otras variables. Lección: una explicación muestra lo que el modelo aprendió, no garantiza la causa.", "",
          "## Un chequeo independiente", "",
          f"Al desordenar cada factor en los inscritos de 2026-2, el que más hace caer la exactitud del modelo es "
          f"**{perm.iloc[0]['concepto']}** (el AUC cae {perm.iloc[0]['caida_auc']:.3f}), seguido de **{perm.iloc[1]['concepto']}**. "
          + ("Los dos están entre los tres primeros de SHAP." if set(perm["concepto"].iloc[:2]) <= set(imp.index[:3])
             else "SHAP los ordena distinto: los dos métodos miden cosas diferentes (cuánto mueve la probabilidad frente a "
                  "cuánto empeora el orden)."), "",
          "## Tres inscritos de la campaña 2027-1", ""]
    L += [f"- Propensión **{r.caso}** (inscrito {r.inscripcion_id}, {r.prob_matricula:.0%}): SHAP señala {r.top3_shap}; "
          f"LIME, {r.top3_lime}." for r in casos.itertuples()]
    L += ["", "> Recordatorio: el resultado de matrícula y las notas son sintéticos. Con datos reales de Admisiones, este "
          "análisis se repite sin cambios y puede mostrar otros pesos."]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
