"""Gráficas del Sprint 2 en español sencillo. Las usan ejecutar_sprint2.py (las guarda en PNG) y el cuaderno (las muestra).

Cada función devuelve la figura de matplotlib. Los ejes y títulos usan nombres claros (NOMBRES_LEGIBLES) en vez de los
nombres técnicos de las columnas, y las barras llevan su valor escrito para leerlas sin mirar el eje.
"""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import caracteristicas as ca

AZUL, NARANJA, GRIS, VERDE = "#1B365D", "#E07B39", "#9AA5B1", "#2E7D5B"
COLORES_SEGMENTO = ["#791734", "#C9A227", "#E07B39", "#4A6FA5", "#2E7D5B"]      # S1 a S5
NOMBRE_CORTO = {"estrato": "estrato", "log_distancia": "distancia al campus", "punt_global": "puntaje ICFES",
                "promedio_acumulado_colegio": "notas del colegio", "edad_al_inscribirse": "edad",
                "colegio_privado": "colegio privado", "colegio_promedio_saber11": "nivel del colegio"}
ORDEN = {"segmento_rendimiento_icfes": ["BAJO", "MEDIO", "ALTO", "SUPERIOR"], "zona_distancia": ["CERCA", "MEDIA", "LEJOS"],
         "estrato_grupo": ["BAJO", "MEDIO", "ALTO"], "rezago_saber11": ["INMEDIATO", "UN_ANIO", "DOS_O_MAS"],
         "aplica_beca_mi_vocacion": ["No", "Sí"], "canal_agrupado": ["DIGITAL", "EVENTO", "RELACIONAL"]}


def eleccion_k(ref: dict) -> plt.Figure:
    km = ref["kmeans"]
    ev = pd.DataFrame(km["evaluacion"])
    fig, ejes = plt.subplots(1, 2, figsize=(12, 4))
    ejes[0].plot(ev["k"], ev["inercia"], "o-", color=AZUL)
    ejes[0].set(title="Método del codo: con más grupos, cada grupo es más parejo",
                xlabel="número de segmentos (k)", ylabel="dispersión dentro de los grupos (inercia)")
    ejes[1].plot(ev["k"], ev["silueta"], "o-", color=NARANJA)
    ejes[1].axvline(km["k"], color=GRIS, ls="--", label=f"se eligieron {km['k']} segmentos")
    ejes[1].set(title="Silueta: qué tan separados quedan los grupos (más alto = mejor)",
                xlabel="número de segmentos (k)", ylabel="silueta media (de −1 a 1)")
    ejes[1].legend(fontsize=9)
    for ax in ejes:
        ax.set_xticks(ev["k"])
    fig.tight_layout()
    return fig


def mapa_segmentos(d: pd.DataFrame, ref: dict) -> plt.Figure:
    """Cómo se ven los segmentos de k-means. k-means trabaja con 6 variables a la vez; para dibujarlas en un plano se
    proyectan en sus 2 componentes principales (PCA con las medias y escalas del entrenamiento). Cada punto es un
    inscrito, su color es el segmento que le asignó k-means y los círculos grandes son los centros de cada segmento."""
    km = ref["kmeans"]
    Z = ((d[km["variables"]] - km["medias"]) / km["desv"]).to_numpy(float)
    ent = (d["particion"] == "ENTRENAMIENTO").to_numpy()
    media = Z[ent].mean(axis=0)
    _, s, vt = np.linalg.svd(Z[ent] - media, full_matrices=False)
    comp = vt[:2].copy()
    for i in range(2):                                   # la variable con más peso apunta a la derecha / arriba
        if comp[i][np.argmax(np.abs(comp[i]))] < 0:
            comp[i] = -comp[i]
    var = (s ** 2 / (s ** 2).sum())[:2]
    P = (Z - media) @ comp.T
    C = (km["centros_z"].to_numpy(float) - media) @ comp.T          # centros, en el mismo orden que los nombres
    fig, ax = plt.subplots(figsize=(13.5, 7.6))
    for i, nombre in enumerate(km["nombres"]):
        m = (d["segmento_mercado"] == nombre).to_numpy()
        ax.scatter(P[m, 0], P[m, 1], s=16, alpha=0.35, color=COLORES_SEGMENTO[i % 5], edgecolors="none",
                   label=f"{nombre} ({format(int(m.sum()), ',').replace(',', '.')} inscritos)")
    for i, nombre in enumerate(km["nombres"]):
        ax.scatter(*C[i], s=900, color=COLORES_SEGMENTO[i % 5], edgecolors="white", linewidths=3, zorder=5)
        ax.annotate(nombre.split(":")[0], C[i], ha="center", va="center", color="white", fontsize=13,
                    fontweight="bold", zorder=6)

    def eje(i: int) -> str:
        cargas = pd.Series(comp[i], index=km["variables"])
        top = cargas.abs().sort_values(ascending=False).index[:2]
        partes = [("más " if cargas[v] > 0 else "menos ") + NOMBRE_CORTO.get(v, v) for v in top]
        return f"Dimensión {i + 1} ({var[i] * 100:.0f}% de la variación) → {' y '.join(partes)}"

    ax.set(xlabel=eje(0), ylabel=eje(1),
           title="Así se ven los segmentos de k-means: cada punto es un inscrito; el círculo grande, el centro del grupo")
    ley = ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1), frameon=False, fontsize=10, markerscale=2.2)
    for h in ley.legend_handles:
        h.set_alpha(1)
    ax.axhline(0, color=GRIS, lw=0.6, ls=":")
    ax.axvline(0, color=GRIS, lw=0.6, ls=":")
    fig.tight_layout()
    return fig


def perfil_segmentos(d: pd.DataFrame) -> plt.Figure:
    """Tabla de colores: cada celda muestra el valor REAL promedio del segmento; el color dice si está por encima
    (rojo) o por debajo (azul) del promedio de todos los inscritos."""
    t = ca.tabla_segmentos(d)
    cols = ["Puntaje ICFES", "Notas del colegio (1 a 5)", "Distancia por vías (km)", "Estrato promedio",
            "% de colegio público", "Edad (años)", "% que se matriculó"]
    valores = t[cols]
    seg, total = valores.drop(index="Todos los inscritos"), valores.loc["Todos los inscritos"]
    rel = (seg - total) / seg.std().replace(0, 1)
    fig, ax = plt.subplots(figsize=(13, 0.75 * len(valores) + 1.8))
    colores = np.vstack([rel.clip(-1.5, 1.5).to_numpy(float), np.zeros((1, len(cols)))])
    ax.imshow(colores, cmap="coolwarm", vmin=-2.2, vmax=2.2, aspect="auto")
    ax.set_xticks(range(len(cols)), [c.replace(" (", "\n(") for c in cols], fontsize=9)
    ax.xaxis.tick_top()
    ax.set_yticks(range(len(valores)), valores.index, fontsize=9)
    for (i, j), v in np.ndenumerate(valores.to_numpy(float)):
        texto = f"{v:.0f}%" if cols[j].startswith("%") else f"{v:.2f}" if "Notas" in cols[j] else \
            f"{v:.0f}" if cols[j] == "Puntaje ICFES" else f"{v:.1f}"
        ax.text(j, i, texto, ha="center", va="center", fontsize=10,
                fontweight="bold" if i == len(valores) - 1 else "normal")
    ax.axhline(len(valores) - 1.5, color="black", lw=1)
    ax.set_title("¿Cómo es cada segmento? Promedio de cada grupo  ·  rojo = más alto que el promedio · azul = más bajo",
                 fontsize=11, pad=12)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    fig.tight_layout()
    return fig


def tamano_y_matricula(d: pd.DataFrame) -> plt.Figure:
    t = ca.tabla_segmentos(d).drop(index="Todos los inscritos").iloc[::-1]
    tasa_total = d["matriculado"].astype(float).mean() * 100
    fig, ejes = plt.subplots(1, 2, figsize=(13, 0.6 * len(t) + 1.6), sharey=True)
    b = ejes[0].barh(t.index, t["Inscritos"], color=AZUL)
    ejes[0].bar_label(b, labels=[f"{n:,}  ({p:.0f}%)".replace(",", ".") for n, p in zip(t["Inscritos"], t["% del total"])],
                      padding=3, fontsize=9)
    ejes[0].set(title="¿Cuántos inscritos hay en cada segmento?", xlabel="inscritos")
    ejes[0].set_xlim(0, t["Inscritos"].max() * 1.3)
    b = ejes[1].barh(t.index, t["% que se matriculó"], color=[VERDE if v >= tasa_total else NARANJA for v in t["% que se matriculó"]])
    ejes[1].bar_label(b, fmt="%.0f%%", padding=3, fontsize=9)
    ejes[1].axvline(tasa_total, color=GRIS, ls="--", label=f"todos los inscritos: {tasa_total:.0f}%")
    ejes[1].set(title="¿Qué porcentaje se matriculó?", xlabel="% que pagó la matrícula", xlim=(0, 70))
    ejes[1].legend(fontsize=9, loc="lower right")
    fig.tight_layout()
    return fig


def tabla_matricula_por_grupo(ent: pd.DataFrame, columnas: list[str], cfg: dict | None = None) -> pd.DataFrame:
    """Tabla larga: para cada característica y cada grupo, cuántos inscritos hay y qué % se matriculó."""
    etiq = ca.etiquetas_categorias(cfg)
    filas = []
    for c in columnas:
        g = ent.assign(m=ent["matriculado"].astype(float)).groupby(c)["m"].agg(["size", "mean"])
        g = g.reindex([o for o in ORDEN.get(c, g.index) if o in g.index])
        for codigo, (n, tasa) in g.iterrows():
            filas.append({"Característica": ca.NOMBRES_LEGIBLES.get(c, c), "Grupo": etiq.get(c, {}).get(codigo, codigo),
                          "Inscritos": int(n), "% que se matriculó": round(tasa * 100, 1)})
    return pd.DataFrame(filas)


def matricula_por_grupo(ent: pd.DataFrame, columnas: list[str], cfg: dict | None = None) -> plt.Figure:
    t = tabla_matricula_por_grupo(ent, columnas, cfg)
    tasa_total = ent["matriculado"].astype(float).mean() * 100
    filas = int(np.ceil(len(columnas) / 3))
    fig, ejes = plt.subplots(filas, 3, figsize=(16, 3.6 * filas))
    for ax, c in zip(ejes.flat, columnas):
        g = t[t["Característica"] == ca.NOMBRES_LEGIBLES.get(c, c)].iloc[::-1]
        b = ax.barh(g["Grupo"], g["% que se matriculó"],
                    color=[VERDE if v >= tasa_total else NARANJA for v in g["% que se matriculó"]])
        ax.bar_label(b, labels=[f"{v:.0f}%  (n = {n})" for v, n in zip(g["% que se matriculó"], g["Inscritos"])],
                     padding=3, fontsize=8)
        ax.axvline(tasa_total, color=GRIS, ls="--")
        ax.set_xlim(0, 85)
        ax.set_title(ca.NOMBRES_LEGIBLES.get(c, c), fontsize=11)
        ax.set_xlabel("% que se matriculó")
    for ax in list(ejes.flat)[len(columnas):]:
        ax.axis("off")
    fig.suptitle(f"¿Qué porcentaje se matricula en cada grupo? · inscritos de entrenamiento ({len(ent):,}) · verde = más "
                 f"que el promedio ({tasa_total:.0f}%, línea gris)".replace(",", "."), fontsize=12)
    fig.tight_layout()
    return fig


def indice_vocacional(ent: pd.DataFrame) -> plt.Figure:
    """De la entrevista cualitativa al índice de 0 a 100: distribución y matrícula por tramo del índice."""
    con = ent[ent["entrevista_realizada"] == 1]
    tramos = pd.cut(con["indice_vocacional"], [-0.1, 40, 60, 80, 100], labels=["0 a 40", "41 a 60", "61 a 80", "81 a 100"])
    tasa = con["matriculado"].astype(float).groupby(tramos, observed=True).mean() * 100
    sin = ent.loc[ent["entrevista_realizada"] == 0, "matriculado"].astype(float).mean() * 100
    fig, ejes = plt.subplots(1, 2, figsize=(12, 4.2))
    ejes[0].hist(con["indice_vocacional"], bins=17, color=AZUL, edgecolor="white")
    ejes[0].set(title="¿Cómo se reparte el índice vocacional?", xlabel="índice vocacional (0 a 100)", ylabel="inscritos")
    barras = ejes[1].bar(list(tasa.index.astype(str)) + ["sin entrevista"], list(tasa) + [sin],
                         color=[AZUL] * len(tasa) + [GRIS])
    ejes[1].bar_label(barras, fmt="%.0f%%", fontsize=9)
    ejes[1].set(title="¿Qué porcentaje se matricula según su índice?", xlabel="índice vocacional", ylabel="% que se matriculó")
    fig.suptitle(f"Entrevista de admisión convertida en número · inscritos de entrenamiento ({len(ent):,})".replace(",", "."))
    fig.tight_layout()
    return fig


def error_logistica(metr: pd.DataFrame) -> plt.Figure:
    """metr: índice = conjunto (VALIDACION, PRUEBA) con las columnas error_pct y auc_roc de la regresión logística."""
    conjuntos = {"VALIDACION": "Validación (2026-1)", "PRUEBA": "Prueba (2026-2)"}
    m = metr.rename(index=conjuntos).loc[list(conjuntos.values())]
    fig, ejes = plt.subplots(1, 2, figsize=(10, 4))
    for ax, col, titulo, fmt in [(ejes[0], "error_pct", "¿Cuántas veces se equivoca? (más bajo = mejor)", "{:.1f}%"),
                                 (ejes[1], "auc_roc", "¿Qué tan bien ordena? AUC (0,5 = azar; 1 = perfecto)", "{:.3f}")]:
        barras = ax.bar(m.index, m[col], color=[AZUL, NARANJA])
        ax.bar_label(barras, labels=[fmt.format(v) for v in m[col]], fontsize=9)
        ax.set(title=titulo, ylim=(0, m[col].max() * 1.25))
    ejes[0].set_ylabel("% de inscritos mal clasificados")
    fig.suptitle("Regresión logística del Sprint 2", fontsize=11)
    fig.tight_layout()
    return fig
