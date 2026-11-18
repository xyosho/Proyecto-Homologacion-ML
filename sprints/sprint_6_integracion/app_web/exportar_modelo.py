"""SPRINT 6 — Exporta el modelo a JSON para la app web (Vercel), sin Python en el servidor.

La app publicada calcula la predicción en el navegador con modelo.js. Para que dé EXACTAMENTE lo mismo que
prediccion.predecir, este script copia lo que el proyecto ya aprendió:
  - Sprint 2: estandarización, centros del k-means y el modelo NLP de la entrevista (vocabulario, idf y pesos de Ridge de
    cada sección), para calcular en el navegador el puntaje vocacional que se lee en las respuestas del aspirante;
  - Sprint 3: el modelo elegido para la matrícula, con su escalado y categorías. Si es una regresión logística, sus
    coeficientes; si es un Random Forest, sus árboles (variable, umbral, hijos y proporción de casos positivos en cada
    hoja);
  - Sprint 4: muestra de referencia de SHAP (la media para la logística y 100 casos para los árboles);
  - reglas de config/reglas_negocio.yaml: tarifas, becas, ubicaciones y umbrales.

Con --casos N también guarda N aspirantes al azar con la predicción de Python (pruebas/casos_verificacion.json), y
pruebas/verificar_modelo.mjs comprueba que modelo.js da lo mismo.

Uso:
  python sprints/sprint_6_integracion/app_web/exportar_modelo.py
  python sprints/sprint_6_integracion/app_web/exportar_modelo.py --casos 300
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from datetime import date
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(AQUI.parent))
warnings.filterwarnings("ignore")

import caracteristicas as ca  # noqa: E402
import nlp_vocacion as nlp  # noqa: E402
import explicabilidad as ex  # noqa: E402
import modelado as mo  # noqa: E402
import predecir_aspirante as pa  # noqa: E402
import prediccion as pr  # noqa: E402

PERIODOS = ["2027-1", "2027-2"]
# Municipios vecinos que NO están en los datos de entrenamiento (Bogotá y Sabana Centro). El modelo los puede calcular
# porque solo usa la distancia al campus; la app avisa que es una extrapolación. Coordenada de la cabecera: DIVIPOLA
# del DANE (datos.gov.co, conjunto gdxc-w37w).
VECINOS = [{"ubicacion_id": 25754, "nombre": "Soacha", "tipo": "MUNICIPIO", "municipio": "Soacha", "departamento": "CUNDINAMARCA",
            "lat": 4.579268, "lon": -74.215463, "fuera_de_entrenamiento": True,
            "fuente": "DANE, DIVIPOLA (datos.gov.co/resource/gdxc-w37w)"}]


def _lista(v) -> list:
    return [x.item() if hasattr(x, "item") else x for x in np.asarray(v).ravel()]


def _preparacion(modelo) -> dict:
    """Columnas, categorías del one-hot y escalado (si lo hay) del ColumnTransformer del Sprint 3."""
    prep = modelo.named_steps["preparacion"]
    num, cat = prep.named_transformers_["num"], prep.named_transformers_["cat"]
    salida = {"numericas": list(prep.transformers_[0][2]), "categoricas": list(prep.transformers_[1][2]),
              "categorias": [[str(c) for c in cs] for cs in cat.categories_], "nombres": list(prep.get_feature_names_out())}
    if hasattr(num, "mean_"):
        salida |= {"media": _lista(num.mean_), "escala": _lista(num.scale_)}
    return salida


def _arbol(est) -> dict:
    t = est.tree_
    v = t.value[:, 0, :]
    return {"variable": _lista(t.feature), "umbral": _lista(t.threshold), "izquierda": _lista(t.children_left),
            "derecha": _lista(t.children_right), "valor": _lista(v[:, 1] / v.sum(axis=1))}   # proporción que se matricula


def _modelo(modelo, X_fondo, grupos: dict) -> dict:
    """Regresión logística (SHAP lineal con la media del fondo) o Random Forest (TreeSHAP con 100 casos), como el Sprint 4."""
    clf, prep = modelo.named_steps["modelo"], modelo.named_steps["preparacion"]
    base = _preparacion(modelo) | {"grupos": grupos}
    if hasattr(clf, "coef_"):
        return base | {"tipo": "logistica", "coef": _lista(clf.coef_), "intercepto": float(clf.intercept_[0]),
                       "fondo_media": _lista(prep.transform(X_fondo).mean(axis=0))}
    if hasattr(clf, "estimators_"):
        return base | {"tipo": "arboles", "arboles": [_arbol(e) for e in clf.estimators_],
                       "fondo": [_lista(f) for f in prep.transform(X_fondo)[:100]]}
    raise SystemExit(f"modelo.js no sabe calcular un {type(clf).__name__}: elija regresión logística o Random Forest.")


def _nlp(ref_nlp: dict) -> dict:
    """El modelo NLP del Sprint 2 en datos: por sección, los términos (en el orden de las columnas), su idf y su peso en
    Ridge. modelo.js repite analizar(), el TF-IDF (tf sublineal y norma L2 por sección) y la suma de Ridge."""
    pipe = ref_nlp["modelo"]
    ct, ridge = pipe.named_steps["tfidf"], pipe.named_steps["ridge"]
    coef, inicio, secciones = _lista(ridge.coef_), 0, []
    for nombre, vec, col in ct.transformers_:
        if nombre == "remainder":
            continue
        terminos = list(vec.get_feature_names_out())
        secciones.append({"columna": col, "terminos": terminos, "idf": _lista(vec.idf_),
                          "pesos": coef[inicio:inicio + len(terminos)], "sublineal": bool(vec.sublinear_tf), "norma": vec.norm})
        inicio += len(terminos)
    assert inicio == len(coef)
    return {"intercepto": float(ridge.intercept_), "minimo": 1, "maximo": 5, "decimales": 3,
            "palabras_vacias": list(nlp.STOPWORDS_ES), "ngramas": [1, 2], "secciones": secciones}


def exportar(artefactos: dict, cfg: dict) -> dict:
    ref = artefactos["referencias"]
    km = ref["kmeans"]
    u = pr.ubicaciones()
    mm = artefactos["modelo_matricula"]
    Xf = artefactos["fondo_matricula"]          # ya son columnas del modelo (Sprint 4)
    b = cfg["becas"]
    return {
        "version": 1, "generado": date.today().isoformat(),
        "fuente": "Unicervantes · proyecto de homologación (Sprints 2 a 4). Datos de entrenamiento simulados.",
        "reglas": {
            "campus": {"lat": cfg["campus"]["lat"], "lon": cfg["campus"]["lon"]},
            "periodos": PERIODOS,
            "tarifas": {p: {str(a): int(v["valor"]) for a, v in t.items()} for p, t in cfg["tarifas"].items()},
            "becas": {k: {"nombre": b[k]["nombre"], "pct_primer": b[k]["pct_primer_periodo"], "pct_siguientes": b[k]["pct_siguientes"]}
                      for k in ("SABER_11", "MI_VOCACION", "NINGUNA")},
            "descuentos": {"tope": float(cfg["descuentos"]["tope_beca_mas_descuento"]),
                           "tipos": {k: {"nombre": t["nombre"], "pct": [float(x) for x in t["pct"]]}
                                     for k, t in cfg["descuentos"]["tipos"].items()}},
            "icetex": {"plan": cfg["icetex"]["plan"], "pct_paga_mientras_estudia": cfg["icetex"]["pct_paga_mientras_estudia"],
                       "tasa": cfg["icetex"]["tasa"],
                       "merito_minimo": {m: int(v["merito_minimo"]) for m, v in cfg["icetex"]["merito_minimo_por_municipio"].items()}},
            "umbral_icfes": int(b["SABER_11"]["umbral_icfes"]), "puntaje_vocacional_minimo": 3,
            "promedio_minimo_beca": b["SABER_11"]["promedio_minimo"],
            "umbral_clasificacion": cfg["modelado"]["umbral_clasificacion"],
            "segmentos_propension": cfg["modelado"]["segmentos_propension"],
            "bandas_icfes": cfg["caracteristicas"]["bandas_icfes"],
            "zonas_distancia_km": cfg["caracteristicas"]["zonas_distancia_km"],
            "fondos_municipales": sorted(int(f["ubicacion_id"]) for f in cfg["fondos_educacion_municipal"].values()),
            "canales": pr.CANALES, "defectos": {k: v for k, v in pr.DEFECTOS.items() if v is not None},
        },
        "ubicaciones": [{"ubicacion_id": int(r.ubicacion_id), "nombre": r.nombre, "tipo": r.tipo, "municipio": r.municipio,
                         "departamento": r.departamento, "lat": float(r.lat), "lon": float(r.lon)} for r in u.itertuples()] + VECINOS,
        "referencias": {
            "estandarizacion": {k: list(v) for k, v in ref["estandarizacion"].items()},
            "kmeans": {"variables": km["variables"], "medias": [float(km["medias"][v]) for v in km["variables"]],
                       "desv": [float(km["desv"][v]) for v in km["variables"]],
                       "centros": [_lista(c) for c in km["modelo"].cluster_centers_],      # orden original de sklearn
                       "posicion": {str(o): n for n, o in enumerate(km["orden"])}, "nombres": km["nombres"]},
        },
        "nlp": _nlp(ref["nlp"]),
        "matricula": _modelo(mm, Xf, ex.GRUPOS_MATRICULA),
    }


def _respuestas_simuladas() -> list[dict]:
    """Respuestas reales del banco simulado (S-48), separadas por pregunta, para verificar el NLP en el navegador."""
    import pandas as pd
    from comun import TABLAS_DIR
    preg = pd.read_csv(TABLAS_DIR / "pregunta_entrevista.csv")
    resp = pd.read_csv(TABLAS_DIR / "respuesta_entrevista.csv").merge(preg, on="pregunta_id")
    col = {"INTERES_PROGRAMA": "texto_interes_programa", "HISTORIA_VIDA": "texto_historia_vida",
           "INTERES_UNIVERSIDAD": "texto_interes_universidad"}
    salida = []
    for _, g in resp.sort_values(["inscripcion_id", "orden"]).groupby("inscripcion_id"):
        salida.append({col[s]: list(gg["respuesta"]) for s, gg in g.groupby("seccion")})
        if len(salida) >= 400:
            break
    return salida


def casos(n: int, artefactos: dict, cfg: dict, semilla: int = 20261126) -> list[dict]:
    """Aspirantes al azar (con coordenada, sin Catastro) y lo que responde prediccion.predecir en Python."""
    rng = np.random.default_rng(semilla)
    u = pr.ubicaciones()
    banco = _respuestas_simuladas()
    salida = []
    for _ in range(n):
        fila = u.iloc[rng.integers(len(u))]
        entrevista = bool(rng.random() < 0.8)
        e = {"punt_global": int(rng.integers(150, 451)), "estrato": int(rng.integers(1, 7)),
             "programa": str(rng.choice(["AD", "SSIA"])), "periodo": str(rng.choice(PERIODOS)),
             "genero": str(rng.choice(["M", "F"])), "edad": int(rng.integers(16, 30)), "ubicacion": fila["nombre"],
             "tipo_colegio": str(rng.choice(["PUBLICO", "PRIVADO", "TECNICO"])),
             "canal": str(rng.choice(pr.CANALES)),
             "entrevista": entrevista, "puntaje_vocacional": int(rng.integers(1, 6)),
             "anios_desde_saber11": int(rng.choice([0, 0, 0, 1, 2, 4])), "apoyo_foes": bool(rng.random() < 0.5),
             "beca": str(rng.choice(["auto", "auto", "NINGUNA", "MI_VOCACION", "SABER_11"]))}
        if rng.random() < 0.3:                       # una minoría con descuento institucional
            tipo = str(rng.choice(list(cfg["descuentos"]["tipos"])))
            e["tipo_descuento"] = tipo
            e["pct_descuento_adicional"] = float(rng.choice(cfg["descuentos"]["tipos"][tipo]["pct"]))
        if rng.random() < 0.4:
            e["solicita_icetex"] = True
        if rng.random() < 0.3:
            e["regimen_salud"] = str(rng.choice(["CONTRIBUTIVO", "SUBSIDIADO", "ESPECIAL"]))
        # 70%: con las respuestas abiertas de la entrevista (el NLP lee el puntaje); 30%: solo el puntaje de la psicóloga
        if entrevista and rng.random() < 0.7:
            e["respuestas_entrevista"] = banco[int(rng.integers(len(banco)))]
        if rng.random() < 0.6:                       # casi siempre con coordenada cerca del centro de la ubicación
            e["lat"] = round(float(fila["lat"]) + float(rng.normal(0, 0.01)), 6)
            e["lon"] = round(float(fila["lon"]) + float(rng.normal(0, 0.01)), 6)
        r = pr.predecir(e, artefactos, cfg)
        salida.append({"entrada": e, "salida": json.loads(json.dumps(r, default=float))})
    return salida


def main() -> None:
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--casos", type=int, default=0, help="aspirantes al azar para verificar modelo.js")
    args = a.parse_args()
    cfg = ca.configuracion()
    artefactos = pa.cargar_artefactos()
    destino = AQUI / "modelo.json"
    destino.write_text(json.dumps(exportar(artefactos, cfg), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Modelo exportado: {destino.relative_to(RAIZ)} ({destino.stat().st_size / 1024:.0f} KB)")
    if args.casos:
        (AQUI / "pruebas").mkdir(exist_ok=True)
        ruta = AQUI / "pruebas" / "casos_verificacion.json"
        ruta.write_text(json.dumps(casos(args.casos, artefactos, cfg), ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"Casos de verificación: {ruta.relative_to(RAIZ)} ({args.casos})")


if __name__ == "__main__":
    main()
