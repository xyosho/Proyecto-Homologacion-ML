"""SPRINT 5 — Validación con datos no vistos e impacto en matrículas.

Pasos:
  1. Se abre el "sobre sellado": el resultado real de la campaña 2027-1 (todos sus inscritos), guardado desde la Semana 1 y
     nunca usado para entrenar ni elegir modelos.
  2. Se evalúa el modelo del Sprint 3 (entrenado con 2024-1 a 2026-2) contra ese resultado: ¿acierta o falla?
  3. Escenario 1: seguimiento priorizado de los inscritos de la campaña (¿a quién llamar primero?).
  4. Escenario 2: Expo Estudiantes (matrículas extra con seguimiento y segmentos a priorizar).
  5. Sensibilidad de cada supuesto (±50%) y tabla de acciones por segmento de mercado.
No se calculan costos: el proyecto no tiene datos del costo del seguimiento ni de la inversión en eventos.

Uso:  python sprints/sprint_5_validacion_impacto/ejecutar_sprint5.py [--local]
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
from sklearn.metrics import confusion_matrix, roc_auc_score  # noqa: E402

import caracteristicas as ca  # noqa: E402
import datos  # noqa: E402
import flujo  # noqa: E402
import impacto as im  # noqa: E402
import modelado as mo  # noqa: E402

RES, FIG = AQUI / "resultados", AQUI / "resultados" / "figuras"
MOD = RAIZ / "sprints" / "sprint_3_modelado" / "modelos"
AZUL, NARANJA, GRIS, VERDE = "#1B365D", "#E07B39", "#9AA5B1", "#2E7D5B"
COP = lambda v: f"${v:,.0f}".replace(",", ".")      # noqa: E731
NOMBRES_SUPUESTOS = {"capacidad_pct": "la capacidad de seguimiento", "efecto_maximo": "el efecto de la llamada"}
ELEGIDO, SPRINT2 = "Regresión logística con NLP (elegida)", "Regresión logística (Sprint 2)"


def tornado(ax, t: pd.DataFrame, titulo: str, nombres: dict) -> None:
    t = t.iloc[::-1]
    base = t["resultado_base"].iloc[0]
    for i, r in enumerate(t.itertuples()):
        ax.barh(i, r.resultado_bajo - base, left=base, color=NARANJA, label="supuesto −50%" if i == 0 else None)
        ax.barh(i, r.resultado_alto - base, left=base, color=AZUL, label="supuesto +50%" if i == 0 else None)
    ax.set_ylim(-1.1, len(t) - 0.5)       # franja libre abajo para la leyenda, sin tapar las barras
    ax.legend(fontsize=8, loc="lower center", ncol=2)
    ax.axvline(base, color="black", lw=1)
    ax.set_yticks(range(len(t)), [nombres.get(s, s) for s in t["supuesto"]])
    for i, r in enumerate(t.itertuples()):
        ax.text(r.resultado_bajo, i, f"{r.resultado_bajo:.1f} ".replace(".", ","), ha="right", va="center", fontsize=8)
        ax.text(r.resultado_alto, i, f" {r.resultado_alto:.1f}".replace(".", ","), ha="left", va="center", fontsize=8)
    ax.margins(x=0.15)
    ax.set_title(titulo, fontsize=10)
    ax.set_xlabel("matrículas adicionales esperadas")


def main() -> None:
    RES.mkdir(exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    fuente = "local" if "--local" in sys.argv else "auto"
    f = flujo.cargar_y_construir(fuente)
    d, ref, cfg = f["inscritos"], f["referencias"], ca.configuracion()
    sellado, origen_sellado = datos.cargar("resultado_campana_2027_1", fuente)
    imp_cfg = cfg["impacto"]
    print(f"Datos: {f['origen']} · resultado 2027-1: {origen_sellado}")

    # 1-2) Prueba con datos no vistos
    # El modelo elegido y XGBoost usan el puntaje NLP del Sprint 2; la logística del Sprint 2 (modelo base), no
    V, V2 = mo.VARIABLES_MATRICULA_NLP, mo.VARIABLES_MATRICULA
    camp = flujo.conjunto(d, "CAMPANA").merge(sellado, on="inscripcion_id", how="left", validate="one_to_one")
    assert camp["matriculado_real"].notna().all() and len(camp) == len(sellado)
    yc = camp["matriculado_real"].astype(int)
    modelos = {ELEGIDO: joblib.load(MOD / "modelo_matricula.joblib")["modelo"],
               "XGBoost": joblib.load(MOD / "modelo_matricula_xgboost.joblib")["modelo"],
               SPRINT2: joblib.load(MOD / "logistica_sprint2_matricula.joblib")["modelo"]}
    variables = {ELEGIDO: V, "XGBoost": V, SPRINT2: V2}
    prob = {n: m.predict_proba(mo.preparar_X(camp, ref, variables[n]))[:, 1] for n, m in modelos.items()}
    hist = flujo.conjunto(d, "ENTRENAMIENTO", "VALIDACION", "PRUEBA")
    met = {n: mo.metricas(yc, q) for n, q in prob.items()}
    for n in met:
        met[n]["ic95_auc"] = mo.intervalo_bootstrap(yc, prob[n], lambda a, b, u: roc_auc_score(a, b))
        met[n]["ic95_error_pct"] = mo.intervalo_bootstrap(yc, prob[n], lambda a, b, u: 100 * ((b >= u) != a).mean())
    tabla = mo.tabla_metricas(met)
    tabla.to_csv(RES / "prueba_campana_2027_1.csv", encoding="utf-8-sig")
    p_final = prob[ELEGIDO]
    ic_dif = mo.diferencia_error(yc, prob[SPRINT2], p_final)
    deciles = pd.DataFrame({"prob": p_final, "real": yc}).assign(
        grupo=lambda x: pd.qcut(x["prob"].rank(method="first"), 5, labels=["Q1 menor", "Q2", "Q3", "Q4", "Q5 mayor"]))
    por_quintil = deciles.groupby("grupo", observed=True).agg(inscritos=("real", "size"), prob_media=("prob", "mean"),
                                                              tasa_real=("real", "mean"))
    por_quintil.round(3).to_csv(RES / "prueba_campana_por_quintil.csv", encoding="utf-8-sig")
    cm = confusion_matrix(yc, p_final >= cfg["modelado"]["umbral_clasificacion"])

    # 3) Escenario 1: seguimiento priorizado (campaña 2027-1)
    s = imp_cfg["seguimiento"]
    camp["prob"] = p_final
    e1 = im.escenario_seguimiento(camp["prob"], camp["valor_neto_primer_semestre"], s["capacidad_pct"], s["efecto_maximo"])
    e1.to_csv(RES / "escenario1_seguimiento.csv", index=False, encoding="utf-8-sig")

    def ganancia_modelo(capacidad_pct, efecto_maximo):
        t = im.escenario_seguimiento(camp["prob"], camp["valor_neto_primer_semestre"], capacidad_pct, efecto_maximo)
        return {"matriculas_con_modelo": float(t.iloc[2]["matriculas_adicionales"]),
                "ventaja_vs_azar": float(t.iloc[2]["matriculas_adicionales"] - t.iloc[0]["matriculas_adicionales"])}
    sens1 = im.sensibilidad(ganancia_modelo, dict(s), list(s), "matriculas_con_modelo")
    sens1.to_csv(RES / "escenario1_sensibilidad.csv", index=False, encoding="utf-8-sig")

    # 4) Escenario 2: Expo Estudiantes (campañas históricas con resultado)
    lm = modelos[ELEGIDO]
    expo_hist = hist[hist["canal"] == "EXPOESTUDIANTES"].copy()
    expo_hist["prob"] = lm.predict_proba(mo.preparar_X(expo_hist, ref, V))[:, 1]
    filas = []
    for per, g in expo_hist.groupby("periodo"):
        reales = int(g["matriculado"].astype(int).sum())
        t = im.escenario_seguimiento(g["prob"], g["valor_neto_primer_semestre"], 1.0, s["efecto_maximo"])
        t_mod = im.escenario_seguimiento(g["prob"], g["valor_neto_primer_semestre"], s["capacidad_pct"], s["efecto_maximo"])
        filas.append({"campana": per, "inscritos_desde_expo": len(g), "matriculados_reales": reales,
                      "inscritos_con_seguimiento": int(t_mod.iloc[2]["inscritos_con_seguimiento"]),
                      "matriculas_adicionales_con_modelo": float(t_mod.iloc[2]["matriculas_adicionales"]),
                      "seguimiento_a_todos_matriculas_adicionales": float(t.iloc[0]["matriculas_adicionales"])})
    e2 = pd.DataFrame(filas)
    e2.to_csv(RES / "escenario2_expo.csv", index=False, encoding="utf-8-sig")
    seg_expo = (expo_hist.assign(matriculado=expo_hist["matriculado"].astype(float))
                .groupby("segmento_mercado").agg(inscritos=("inscripcion_id", "size"), tasa_matricula=("matriculado", "mean"),
                                                 prob_media=("prob", "mean")).sort_values("tasa_matricula", ascending=False))
    seg_expo.round(3).to_csv(RES / "escenario2_segmentos_expo.csv", encoding="utf-8-sig")

    # 5) Acciones por segmento de mercado (campaña 2027-1)
    acciones = im.acciones_por_segmento(camp, camp["prob"], cfg["modelado"]["segmentos_propension"])
    acciones.round(3).to_csv(RES / "acciones_por_segmento.csv", encoding="utf-8-sig")

    figuras(tabla, por_quintil, cm, e1, sens1, e2)
    resumen = {"origen_datos": f["origen"], "prueba_campana_2027_1": met, "ic95_diferencia_error_puntos": ic_dif,
               "matriz_confusion": cm.tolist(), "escenario1": e1.to_dict(orient="records"),
               "escenario2": e2.to_dict(orient="records")}
    (RES / "metricas_sprint5.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (RES / "resumen_impacto.md").write_text(texto_resumen(met, ic_dif, por_quintil, e1, e2, sens1, acciones), encoding="utf-8")
    print(tabla[["n", "error_pct", "auc_roc", "brier"]])
    print(e1[["estrategia", "matriculas_adicionales", "ingreso_primer_semestre_cop"]].round(1))
    print(e2.round(1).to_string())
    print(f"Listo: {RES.relative_to(RAIZ)}")


def figuras(tabla, por_quintil, cm, e1, sens1, e2) -> None:
    fig, ejes = plt.subplots(1, 3, figsize=(17, 4.5))
    t = tabla.iloc[::-1]
    ejes[0].barh(t.index, t["error_pct"], color=[NARANJA if "Sprint 2" in i else AZUL for i in t.index])
    for i, v in enumerate(t["error_pct"]):
        ejes[0].text(v, i, f" {v:.1f}%".replace(".", ","), va="center", fontsize=9)
    ejes[0].margins(x=0.15)      # espacio para que la etiqueta de la barra más larga no se salga del marco
    ejes[0].set_title("Error en la campaña 2027-1 (datos nunca vistos)")
    x = np.arange(len(por_quintil))
    ejes[1].bar(x - 0.2, por_quintil["prob_media"], 0.4, color=AZUL, label="probabilidad predicha")
    ejes[1].bar(x + 0.2, por_quintil["tasa_real"], 0.4, color=NARANJA, label="tasa real")
    ejes[1].set_xticks(x, por_quintil.index)
    ejes[1].set_title("Por quintil de propensión: predicho vs. real")
    ejes[1].legend(fontsize=8)
    ejes[2].imshow(cm, cmap="Blues")
    for (i, j), v in np.ndenumerate(cm):
        ejes[2].text(j, i, v, ha="center", va="center", fontsize=13, color="white" if v > cm.max() / 2 else "black")
    ejes[2].set_xticks([0, 1], ["predice NO", "predice SÍ"])
    ejes[2].set_yticks([0, 1], ["no se matriculó", "se matriculó"])
    ejes[2].set_title("Matriz de confusión (campaña 2027-1)")
    plt.tight_layout()
    fig.savefig(FIG / "prueba_campana_2027_1.png", dpi=120)
    plt.close(fig)

    fig, ejes = plt.subplots(1, 2, figsize=(15, 4.5))
    ejes[0].barh(e1["estrategia"], e1["ingreso_primer_semestre_cop"] / 1e6, color=[GRIS, NARANJA, AZUL])
    for i, r in enumerate(e1.itertuples()):
        ejes[0].text(r.ingreso_primer_semestre_cop / 1e6, i, f"  {r.matriculas_adicionales:.1f}".replace(".", ",")
                     + f" matrículas\n  {COP(r.ingreso_primer_semestre_cop)}", va="center", fontsize=8)
    ejes[0].set(title="Escenario 1: ingreso adicional del 1er semestre según a quién se llama", xlabel="millones de COP")
    ejes[0].set_xlim(0, e1["ingreso_primer_semestre_cop"].max() / 1e6 * 1.45)
    tornado(ejes[1], sens1, "Sensibilidad: matrículas adicionales con el modelo (supuestos ±50%)",
            {"capacidad_pct": "capacidad de seguimiento (30%)", "efecto_maximo": "efecto máximo de la llamada (10 pts)"})
    plt.tight_layout()
    fig.savefig(FIG / "escenario1_seguimiento.png", dpi=120)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = np.arange(len(e2))
    ax.bar(x, e2["matriculados_reales"], 0.6, color=GRIS, label="matriculados reales")
    ax.bar(x, e2["matriculas_adicionales_con_modelo"], 0.6, bottom=e2["matriculados_reales"], color=AZUL,
           label="adicionales esperadas con seguimiento priorizado")
    for i, r in enumerate(e2.itertuples()):
        ax.text(i, r.matriculados_reales + r.matriculas_adicionales_con_modelo,
                f"+{r.matriculas_adicionales_con_modelo:.1f}".replace(".", ","), ha="center", va="bottom", fontsize=9)
    ax.set_xticks(x, e2["campana"])
    ax.set(title="Escenario 2: matrículas de los inscritos de Expo Estudiantes", ylabel="matrículas")
    ax.legend(fontsize=8, loc="lower right")
    plt.tight_layout()
    fig.savefig(FIG / "escenario2_expo.png", dpi=120)
    plt.close(fig)


def texto_resumen(met, ic_dif, por_quintil, e1, e2, sens1, acciones) -> str:
    m, b = met[ELEGIDO], met[SPRINT2]
    num = lambda v: f"{v:.1f}".replace(".", ",")   # noqa: E731
    comparacion = (f"La diferencia con la logística del Sprint 2 ({num(m['error_pct'] - b['error_pct'])} puntos) está dentro "
                   f"del margen del azar (IC 95%: {num(ic_dif[0])} a {num(ic_dif[1])}): los dos rinden igual."
                   if ic_dif[0] <= 0 <= ic_dif[1] else
                   f"Frente a la logística del Sprint 2 la diferencia es de {num(m['error_pct'] - b['error_pct'])} puntos "
                   f"(IC 95%: {num(ic_dif[0])} a {num(ic_dif[1])}).")
    ult = e2.iloc[-1]
    azar, modelo = e1.iloc[0], e1.iloc[2]
    L = ["# Sprint 5 — Resultados de validación e impacto", "",
         "## 1. ¿Acierta con datos que nunca vio?", "",
         f"Se abrió el resultado de la campaña 2027-1 ({int(m['n'])} inscritos, sellado desde la Semana 1). El modelo se equivocó en "
         f"**{m['error_pct']:.1f}%** de los casos (IC 95%: {m['ic95_error_pct'][0]:.1f}%–{m['ic95_error_pct'][1]:.1f}%) frente a "
         f"{b['error_pct']:.1f}% de la regresión logística del Sprint 2. Su AUC fue {m['auc_roc']:.3f} "
         f"(IC 95%: {m['ic95_auc'][0]:.3f}–{m['ic95_auc'][1]:.3f}). " + comparacion, "",
         f"Lo más útil es el **orden**: en el 20% de inscritos con mayor probabilidad se matriculó el "
         f"{por_quintil['tasa_real'].iloc[-1]:.0%}, y en el 20% con menor probabilidad, el {por_quintil['tasa_real'].iloc[0]:.0%}.", "",
         "## 2. Escenario 1 · ¿A quién llamar primero?", "",
         f"Con capacidad de seguimiento para {int(modelo['inscritos_con_seguimiento'])} inscritos (30%):", "",
         "| Estrategia | Matrículas adicionales | Ingreso 1er semestre |", "|---|---|---|"]
    L += [f"| {r.estrategia} | {num(r.matriculas_adicionales)} | {COP(r.ingreso_primer_semestre_cop)} |" for r in e1.itertuples()]
    L += ["", f"Priorizar a los indecisos con el modelo deja {num(modelo['matriculas_adicionales'] - azar['matriculas_adicionales'])} "
          f"matrículas y {COP(modelo['ingreso_primer_semestre_cop'] - azar['ingreso_primer_semestre_cop'])} más que llamar al azar en "
          f"una sola campaña. Llamar primero a los de mayor probabilidad es lo peor: ellos se iban a matricular de todos modos. "
          f"El supuesto que más mueve el resultado es **{NOMBRES_SUPUESTOS[sens1.iloc[0]['supuesto']]}**: con ±50%, las "
          f"matrículas adicionales van de {num(sens1.iloc[0]['resultado_bajo'])} a {num(sens1.iloc[0]['resultado_alto'])}.", "",
          "## 3. Escenario 2 · Expo Estudiantes", "",
          f"En la Expo de la campaña {ult['campana']} se inscribieron {int(ult['inscritos_desde_expo'])} aspirantes y se matricularon "
          f"{int(ult['matriculados_reales'])}. Con seguimiento priorizado a {int(ult['inscritos_con_seguimiento'])} de ellos (30%), se esperan "
          f"{num(ult['matriculas_adicionales_con_modelo'])} matrículas más. No se calcula el costo por matriculado porque no hay "
          "datos de la inversión en el evento.", "",
          "## 4. Acciones por segmento de mercado (campaña 2027-1)", "",
          "| Segmento | Inscritos | Propensión media | Acción sugerida |", "|---|---|---|---|"]
    L += [f"| {seg} | {int(r.inscritos)} | {r.propension_media:.0%} | {r.accion_sugerida} |" for seg, r in acciones.iterrows()]
    L += ["", "> Las cifras usan dos supuestos (la capacidad de seguimiento y el efecto de la llamada) y datos sintéticos; la "
          "sensibilidad muestra cómo cambian. El ingreso sale de las tarifas oficiales menos la beca de cada inscrito. No se "
          "incluyen costos porque no hay datos de ellos. Con datos reales de Admisiones, el mismo cálculo se repite."]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
