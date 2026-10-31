"""SPRINT 2 — Ingeniería de características: columnas nuevas y útiles sobre la tabla plana dataset_matricula.

Regla de oro contra la FUGA DE DATOS: todo lo que se APRENDE de los datos (tasas de acceso a beca, la regresión del
promedio, las medias para estandarizar y los grupos de k-means) se ajusta SOLO con el conjunto de ENTRENAMIENTO
(2024-1 a 2025-2) y después se aplica igual a validación, prueba, campaña y a cualquier aspirante nuevo (Sprint 6).
Si se ajustara con todos los datos, el modelo "vería" información del futuro y sus métricas serían optimistas.

Funciones principales:
  particion_temporal(periodo)                      -> ENTRENAMIENTO / VALIDACION / PRUEBA / CAMPANA
  ajustar_referencias(inscritos, permanencia)      -> lo aprendido del entrenamiento (un diccionario)
  construir_caracteristicas(inscritos, referencias) -> la misma tabla con las columnas nuevas
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

NUEVAS = [
    "particion", "aplica_beca_saber11", "aplica_beca_mi_vocacion", "probabilidad_acceso_beca",
    "segmento_rendimiento_icfes", "promedio_estimado_universidad", "brecha_colegio_vs_icfes",
    "ahorro_beca_primer_semestre", "log_distancia", "zona_distancia", "rezago_saber11",
    "canal_agrupado", "estrato_grupo", "colegio_privado", "segmento_mercado",
]

# Descripción de cada columna nueva (diccionario del Sprint 2)
DICCIONARIO = {
    "particion": "Conjunto temporal: ENTRENAMIENTO (2024-1 a 2025-2), VALIDACION (2026-1), PRUEBA (2026-2), CAMPANA (2027-1)",
    "aplica_beca_saber11": "Sí/No: puntaje global Saber 11 ≥ 310 (requisito de la Beca Saber 11)",
    "aplica_beca_mi_vocacion": "Sí/No: presentó entrevista y su puntaje vocacional es ≥ 3 (requisito de Mi Vocación)",
    "probabilidad_acceso_beca": "Probabilidad de recibir alguna beca según los requisitos que cumple (frecuencia histórica del entrenamiento, con suavizado de Laplace)",
    "segmento_rendimiento_icfes": "BAJO (< 250), MEDIO (250-309), ALTO (310-349: ya aplica a beca) o SUPERIOR (≥ 350)",
    "promedio_estimado_universidad": "Promedio esperado en el 1er semestre (regresión lineal con Saber 11, promedio del colegio y estrato bajo)",
    "brecha_colegio_vs_icfes": "z(promedio del colegio) − z(Saber 11): positivo = rinde más en el colegio que en el examen",
    "ahorro_beca_primer_semestre": "Cuánto le ahorra la beca en el 1er semestre (tarifa plena − precio neto), en COP",
    "log_distancia": "Logaritmo natural de la distancia por vías desde la dirección hasta el campus (S-44; reduce la cola larga)",
    "zona_distancia": "Distancia por vías desde la dirección: CERCA (≤ 10 km), MEDIA (10-20 km) o LEJOS (> 20 km)",
    "rezago_saber11": "INMEDIATO (presentó el Saber 11 el año anterior), UN_ANIO o DOS_O_MAS",
    "canal_agrupado": "EVENTO (Expo, Campus Day), RELACIONAL (referido, inmersión, convenio) o DIGITAL (web, redes, llamada)",
    "estrato_grupo": "BAJO (1-2), MEDIO (3) o ALTO (4-6)",
    "colegio_privado": "1 si el colegio es privado",
    "segmento_mercado": "Perfil del aspirante según k-means (segmentación de mercado), nombrado por sus rasgos principales",
}

ETIQUETAS_KMEANS = {   # (si el centro está por encima, si está por debajo) de la media del entrenamiento
    "estrato": ("estrato más alto", "estrato más bajo"),
    "log_distancia": ("viven lejos del campus", "viven cerca del campus"),
    "punt_global": ("buen puntaje ICFES", "puntaje ICFES bajo"),
    "promedio_acumulado_colegio": ("buenas notas en el colegio", "notas bajas en el colegio"),
    "edad_al_inscribirse": ("aspirantes mayores", "aspirantes más jóvenes"),
    "colegio_privado": ("colegio privado", "colegio público"),
    "colegio_promedio_saber11": ("colegio de alto nivel", "colegio de nivel bajo"),
}

# Nombres en español sencillo para tablas y gráficas (los nombres técnicos de las columnas no cambian)
NOMBRES_LEGIBLES = {
    "estrato": "Estrato promedio",
    "log_distancia": "Distancia por vías (km)",
    "distancia_vial_km": "Distancia por vías (km)",
    "punt_global": "Puntaje ICFES",
    "promedio_acumulado_colegio": "Notas del colegio (1 a 5)",
    "edad_al_inscribirse": "Edad (años)",
    "colegio_privado": "% de colegio privado",
    "colegio_promedio_saber11": "Nivel ICFES del colegio",
    "segmento_mercado": "Segmento de mercado",
    "segmento_rendimiento_icfes": "Puntaje ICFES",
    "aplica_beca_mi_vocacion": "¿Aplica a la beca Mi Vocación?",
    "aplica_beca_saber11": "¿Aplica a la beca Saber 11?",
    "canal_agrupado": "Canal por el que llegó",
    "zona_distancia": "Distancia al campus",
    "estrato_grupo": "Estrato",
    "rezago_saber11": "Tiempo desde el ICFES",
}

# El ICFES llama "oficial" al colegio público. Los datos y los modelos conservan el código OFICIAL; en todo texto que
# se muestra (explicaciones, gráficas, script de predicción) se dice "público".
NOMBRE_TIPO_COLEGIO = {"OFICIAL": "público", "PRIVADO": "privado", "TECNICO": "técnico"}


def tipo_colegio_codigo(valor: str) -> str:
    """Código de datos del tipo de colegio: acepta PUBLICO (o PÚBLICO) como sinónimo de OFICIAL."""
    v = str(valor).strip().upper().replace("Ú", "U").replace("É", "E")
    return "OFICIAL" if v == "PUBLICO" else v


def etiquetas_categorias(cfg: dict | None = None) -> dict:
    """Texto claro para los códigos de las columnas categóricas nuevas (p. ej. CERCA → "Cerca (hasta 10 km)")."""
    c = (cfg or configuracion())["caracteristicas"]
    z = c["zonas_distancia_km"]
    icfes = {b["segmento"]: (f"{b['segmento'].capitalize()} (menos de {b['hasta']})" if b["desde"] == 0 else
                             f"{b['segmento'].capitalize()} ({b['desde']} o más)" if b["hasta"] > 500 else
                             f"{b['segmento'].capitalize()} ({b['desde']} a {b['hasta'] - 1})") for b in c["bandas_icfes"]}
    return {
        "segmento_rendimiento_icfes": icfes,
        "zona_distancia": {"CERCA": f"Cerca (hasta {z['CERCA']} km)", "MEDIA": f"Media ({z['CERCA']} a {z['MEDIA']} km)",
                           "LEJOS": f"Lejos (más de {z['MEDIA']} km)"},
        "canal_agrupado": {"EVENTO": "Eventos (Expo, Campus Day)", "RELACIONAL": "Relacional (referido, convenio…)",
                           "DIGITAL": "Digital (web, redes, llamada)"},
        "estrato_grupo": {"BAJO": "Estratos 1 y 2", "MEDIO": "Estrato 3", "ALTO": "Estratos 4 a 6"},
        "rezago_saber11": {"INMEDIATO": "Sin pausa tras el colegio", "UN_ANIO": "1 año de pausa", "DOS_O_MAS": "2 años o más de pausa"},
        "aplica_beca_mi_vocacion": {"Sí": "Sí aplica", "No": "No aplica"},
        "aplica_beca_saber11": {"Sí": "Sí aplica", "No": "No aplica"},
    }


def tabla_segmentos(d: pd.DataFrame) -> pd.DataFrame:
    """Resumen de cada segmento de mercado con valores reales (no estandarizados), listo para leer o presentar."""
    m = d.assign(matriculado=d["matriculado"].astype(float))
    def resumen(g: pd.DataFrame) -> dict:
        return {"Inscritos": len(g), "% del total": len(g) / len(d) * 100,
                "% que se matriculó": g["matriculado"].mean() * 100, "Puntaje ICFES": g["punt_global"].mean(),
                "Notas del colegio (1 a 5)": g["promedio_acumulado_colegio"].mean(),
                "Distancia por vías (km)": g["distancia_vial_km"].mean(), "Estrato promedio": g["estrato"].mean(),
                "% de colegio público": (1 - g["colegio_privado"].mean()) * 100, "Edad (años)": g["edad_al_inscribirse"].mean()}
    t = pd.DataFrame({s: resumen(g) for s, g in m.groupby("segmento_mercado")}).T
    t.loc["Todos los inscritos"] = resumen(m)
    t.index.name = "Segmento de mercado"
    return t.round({"Inscritos": 0, "% del total": 1, "% que se matriculó": 1, "Puntaje ICFES": 0,
                    "Notas del colegio (1 a 5)": 2, "Distancia por vías (km)": 1, "Estrato promedio": 1,
                    "% de colegio público": 0, "Edad (años)": 1}).astype({"Inscritos": int})


def configuracion() -> dict:
    """Parámetros del proyecto: config/reglas_negocio.yaml en el computador; en Colab, la copia del cuaderno."""
    try:
        from comun import cargar_config
        return cargar_config()
    except ImportError:
        return CONFIG_PROYECTO  # noqa: F821  (lo define una celda del cuaderno de Colab)


# ----------------------------------------------------------------------------- reglas (no se aprenden de datos)
def particion_temporal(periodo: pd.Series, cfg: dict | None = None) -> pd.Series:
    p = (cfg or configuracion())["particion"]
    mapa = {per: nombre.upper() for nombre in ("entrenamiento", "validacion", "prueba", "campana") for per in p[nombre]}
    return periodo.map(mapa)


def segmento_icfes(punt_global: pd.Series, cfg: dict | None = None) -> pd.Series:
    bandas = (cfg or configuracion())["caracteristicas"]["bandas_icfes"]
    cortes = [bandas[0]["desde"]] + [b["hasta"] for b in bandas]
    return pd.cut(punt_global, bins=cortes, right=False, labels=[b["segmento"] for b in bandas]).astype(str)


def grupo_requisitos(df: pd.DataFrame) -> pd.Series:
    """Grupo para la probabilidad de acceso a beca. Sin requisitos no hay beca posible (regla institucional)."""
    voc = df["puntaje_vocacional"].astype("Float64").fillna(0).astype(int).astype(str)
    return np.where(df["cumple_req_saber11"] == 1, "SABER_11",
                    np.where(df["cumple_req_mi_vocacion"] == 1, "MI_VOCACION_" + voc, "SIN_REQUISITOS"))


def _reglas(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    c = cfg["caracteristicas"]
    d = df.copy()
    d["particion"] = particion_temporal(d["periodo"], cfg)
    d["aplica_beca_saber11"] = np.where(d["punt_global"] >= cfg["becas"]["SABER_11"]["umbral_icfes"], "Sí", "No")
    d["aplica_beca_mi_vocacion"] = np.where(d["cumple_req_mi_vocacion"] == 1, "Sí", "No")
    d["segmento_rendimiento_icfes"] = segmento_icfes(d["punt_global"], cfg)
    # El precio que se usa es el neto del 1er semestre (valor_neto_primer_semestre, ya en dataset_matricula)
    d["ahorro_beca_primer_semestre"] = d["valor_semestre_bruto"] - d["valor_neto_primer_semestre"]
    vial = d["distancia_vial_km"].astype(float)                 # desde la dirección del formulario (S-44)
    d["log_distancia"] = np.log(np.maximum(vial, 0.5))           # piso de 0,5 km: un vecino del campus no da −∞
    z = c["zonas_distancia_km"]
    d["zona_distancia"] = np.select([vial <= z["CERCA"], vial <= z["MEDIA"]],
                                    ["CERCA", "MEDIA"], "LEJOS")
    d["rezago_saber11"] = np.select([d["anios_desde_saber11"] == 0, d["anios_desde_saber11"] == 1],
                                    ["INMEDIATO", "UN_ANIO"], "DOS_O_MAS")
    canal = {canal: grupo for grupo, canales in c["canal_agrupado"].items() for canal in canales}
    d["canal_agrupado"] = d["canal"].map(canal)
    d["estrato_grupo"] = d["estrato"].map(lambda e: c["estrato_grupo"][int(e)])
    d["colegio_privado"] = (d["colegio_naturaleza"] == "PRIVADO").astype(int)
    return d


# ----------------------------------------------------------------------------- lo que se aprende del entrenamiento
def ajustar_referencias(inscritos: pd.DataFrame, permanencia: pd.DataFrame, cfg: dict | None = None) -> dict:
    """Aprende, SOLO con las filas de ENTRENAMIENTO, todo lo que necesitan las columnas nuevas."""
    cfg = cfg or configuracion()
    ent = _reglas(inscritos, cfg)
    ent = ent[ent["particion"] == "ENTRENAMIENTO"]
    ref: dict = {"periodos_entrenamiento": sorted(ent["periodo"].unique()), "n_entrenamiento": len(ent)}

    # 1) Probabilidad de acceso a beca: frecuencia con suavizado de Laplace (k + 1) / (n + 2)
    grupo = pd.Series(grupo_requisitos(ent), index=ent.index)
    con_beca = (ent["beca"] != "NINGUNA").astype(int)
    tabla = con_beca.groupby(grupo).agg(["size", "sum"]).rename(columns={"size": "n", "sum": "con_beca"})
    tabla["probabilidad"] = (tabla["con_beca"] + 1) / (tabla["n"] + 2)
    tabla.loc["SIN_REQUISITOS", ["probabilidad"]] = 0.0          # regla: sin requisitos no hay beca
    ref["tabla_acceso_beca"] = tabla

    # 2) Promedio estimado: regresión lineal por mínimos cuadrados con los matriculados del entrenamiento
    perm = permanencia[particion_temporal(permanencia["periodo"], cfg) == "ENTRENAMIENTO"]
    X = np.column_stack([np.ones(len(perm)), perm["punt_global"], perm["promedio_acumulado_colegio"],
                         (perm["estrato"] <= 2).astype(float)])
    y = perm["promedio_semestre_1"].to_numpy(float)
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    pred = X @ coef
    ref["regresion_promedio"] = {"coeficientes": dict(zip(["intercepto", "punt_global", "promedio_acumulado_colegio",
                                                           "estrato_bajo"], coef.round(6).tolist())),
                                 "r2": float(1 - ((y - pred) ** 2).sum() / ((y - y.mean()) ** 2).sum()),
                                 "n": int(len(perm)), "error_tipico": float(np.sqrt(((y - pred) ** 2).mean()))}

    # 3) Estandarización (z) con medias y desviaciones del entrenamiento
    ref["estandarizacion"] = {c: (float(ent[c].mean()), float(ent[c].std())) for c in ["punt_global", "promedio_acumulado_colegio"]}

    # 4) Segmentación de mercado con k-means: se prueba k = k_min..k_max; se elige el MENOR k cuya silueta esté a
    #    menos de tolerancia_silueta de la mejor (parsimonia: menos segmentos son más fáciles de usar para Mercadeo)
    km = cfg["caracteristicas"]["kmeans"]
    variables = km["variables"]
    medias, desv = ent[variables].mean(), ent[variables].std()
    Z = ((ent[variables] - medias) / desv).to_numpy(float)
    evaluacion = []
    for k in range(km["k_min"], km["k_max"] + 1):
        modelo = KMeans(n_clusters=k, n_init=20, random_state=km["semilla"]).fit(Z)
        evaluacion.append({"k": k, "inercia": float(modelo.inertia_),
                           "silueta": float(silhouette_score(Z, modelo.labels_, random_state=km["semilla"]))})
    tope = max(e["silueta"] for e in evaluacion) - km.get("tolerancia_silueta", 0.0)
    mejor = min((e for e in evaluacion if e["silueta"] >= tope), key=lambda e: e["k"])
    modelo = KMeans(n_clusters=mejor["k"], n_init=20, random_state=km["semilla"]).fit(Z)
    orden = np.argsort(-np.bincount(modelo.labels_))            # segmento 1 = el más grande
    centros = pd.DataFrame(modelo.cluster_centers_[orden], columns=variables)
    nombres = []
    for i, fila in centros.iterrows():
        rasgos = fila.abs().sort_values(ascending=False).index[:2]
        rasgos_txt = ", ".join(ETIQUETAS_KMEANS[v][0 if fila[v] > 0 else 1] for v in rasgos)
        nombres.append(f"S{i + 1}: " + rasgos_txt[0].upper() + rasgos_txt[1:])   # "S1: Colegio público, viven cerca…"
    ref["kmeans"] = {"modelo": modelo, "orden": orden.tolist(), "variables": variables, "medias": medias, "desv": desv,
                     "evaluacion": evaluacion, "k": mejor["k"], "nombres": nombres, "centros_z": centros}
    return ref


def construir_caracteristicas(inscritos: pd.DataFrame, ref: dict, cfg: dict | None = None) -> pd.DataFrame:
    """Devuelve la misma tabla con las columnas nuevas, aplicando lo aprendido del entrenamiento."""
    cfg = cfg or configuracion()
    d = _reglas(inscritos, cfg)
    tabla = ref["tabla_acceso_beca"]["probabilidad"]
    d["probabilidad_acceso_beca"] = pd.Series(grupo_requisitos(d), index=d.index).map(tabla).fillna(
        tabla.drop("SIN_REQUISITOS").mean()).round(4)         # grupo nunca visto: promedio de los grupos con requisitos
    b = ref["regresion_promedio"]["coeficientes"]
    d["promedio_estimado_universidad"] = (b["intercepto"] + b["punt_global"] * d["punt_global"]
                                          + b["promedio_acumulado_colegio"] * d["promedio_acumulado_colegio"]
                                          + b["estrato_bajo"] * (d["estrato"] <= 2)).clip(0, 5).round(2)
    (mg, sg), (mc, sc) = ref["estandarizacion"]["punt_global"], ref["estandarizacion"]["promedio_acumulado_colegio"]
    d["brecha_colegio_vs_icfes"] = (((d["promedio_acumulado_colegio"] - mc) / sc) - ((d["punt_global"] - mg) / sg)).round(3)
    km = ref["kmeans"]
    Z = ((d[km["variables"]] - km["medias"]) / km["desv"]).to_numpy(float)
    etiqueta = km["modelo"].predict(Z)
    posicion = {original: nuevo for nuevo, original in enumerate(km["orden"])}
    d["segmento_mercado"] = [km["nombres"][posicion[e]] for e in etiqueta]
    return d[list(inscritos.columns) + [c for c in NUEVAS if c not in inscritos.columns]]
