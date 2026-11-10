"""PASO 2 — Generar la base de datos sintética de aspirantes (Semana 1).

IDEA GENERAL (muestreo ancestral sobre un grafo dirigido):
cada variable se genera DESPUÉS de sus "causas" y condicionada a ellas. El orden sigue el
embudo comercial completo: lead -> inscrito -> admitido -> matriculado -> semestres cursados.

  ETAPA 1  Registros REALES del Saber 11    <- estudiantes de Bogotá y Sabana Centro (ICFES, kgxf-xxbe)
  ETAPA 2  Selección de leads               <- perfil de la universidad + distancia al campus (Huff)
  ETAPA 3  Registro del lead (BLOQUE 1)     <- periodo y programa de interés, canal, evento, asesor
  ETAPA 4  Conversión lead -> inscripción    <- modelo logístico con parámetros conocidos
  ETAPA 5  Datos personales                 <- preinscripción (todos) y formulario de admisión (inscritos)
  ETAPA 6  Documentos académicos (BLOQUE 2)  <- Saber 11 (real) y notas de grados 10 y 11 (simuladas)
  ETAPA 7  Proceso de admisión (BLOQUE 2)    <- becas, valores, MATRÍCULA (objetivo 1), beneficio, financiación
  ETAPA 8  Gestión del lead (BLOQUE 5)       <- contactos de los asesores e inversión de captación
  ETAPA 9  Seguimiento académico            <- promedios, deserción y CONSERVACIÓN DE BECA (objetivo 2)

Los modelos de las etapas 4, 7 y 9 tienen parámetros CONOCIDOS (config/reglas_negocio.yaml).
Conocerlos permite comprobar en el paso 3 que un modelo estadístico los recupera.

Qué es real y qué es simulado: los puntajes Saber 11, el colegio, el estrato, el género, la edad al presentar el
examen y el municipio de residencia de cada lead vienen de UN registro real y distinto del ICFES (anónimo, CC BY-SA
4.0). Los nombres, documentos, contactos, el proceso comercial y las notas del colegio son simulados.

Uso:  python src/s02_generar_datos_sinteticos.py
"""
from __future__ import annotations

import json
import unicodedata
from datetime import date, timedelta

import numpy as np
import pandas as pd
from faker import Faker
from scipy import stats

import catalogos as cat
import reglas_negocio as rn
from comun import DATA_PROCESSED, DATA_RAW, asegurar_carpetas, cargar_config

AREAS = ["punt_lectura_critica", "punt_matematicas", "punt_sociales_ciudadanas", "punt_c_naturales", "punt_ingles"]
# Áreas obligatorias de la media (Ley 115 de 1994, art. 23) que también evalúa el Saber 11
AREAS_NOTA = {"LENGUAJE": "punt_lectura_critica", "MATEMATICAS": "punt_matematicas",
              "CIENCIAS_SOCIALES": "punt_sociales_ciudadanas", "CIENCIAS_NATURALES": "punt_c_naturales",
              "INGLES": "punt_ingles"}
SINTETICO_DIR = DATA_PROCESSED / "sintetico"
OCULTO_DIR = DATA_PROCESSED / "oculto"
DIAS_PUBLICACION_ICFES = 45          # S-30: el resultado se publica ~45 días después del examen
CAMPANA = "2027-1"


def puntaje_normal(x: pd.Series) -> np.ndarray:
    """Convierte un puntaje en "puntaje normal" con su rango: z = Φ⁻¹((rango − 0.5)/n).
    Así 0 es la mediana de la zona y ±1 deja por debajo al 16% / 84% de los estudiantes."""
    return stats.norm.ppf((stats.rankdata(x) - 0.5) / len(x))


# =============================================================================
# ETAPA 0 — Cargar y limpiar los registros reales del ICFES de la zona
# =============================================================================
def cargar_icfes_zona(cfg: dict) -> pd.DataFrame:
    """Limpia los registros Saber 11 de Bogotá y Sabana Centro y les agrega el contexto de su colegio.

    Todos los registros válidos se usan: cada lead será UN registro real distinto (etapa 2).
    """
    d = pd.read_parquet(DATA_RAW / "icfes_saber11_calibracion.parquet")
    n0 = len(d)
    d = d.dropna(subset=AREAS + ["punt_global", "estu_genero"])
    d = d[d["fami_estratovivienda"].isin([f"Estrato {i}" for i in range(1, 7)])]   # se excluye 'Sin Estrato' y vacíos
    d = d[(d[AREAS] > 0).all(axis=1)]                                             # H-12: pruebas en 0 (anomalía)
    d["estrato"] = d["fami_estratovivienda"].str[-1].astype(int)
    fn = pd.to_datetime(d["estu_fechanacimiento"], format="%d/%m/%Y", errors="coerce")
    d["edad_examen"] = (pd.to_datetime(d["periodo"].str[:4] + "-08-15") - fn).dt.days / 365.25
    d = d[d["edad_examen"].between(14, 30)].reset_index(drop=True)               # H-12: edades imposibles
    d = d.rename(columns={"periodo": "periodo_icfes"})       # "periodo" queda para el periodo de interés del lead
    for c in AREAS + ["punt_global"]:
        d[c] = d[c].astype(int)

    # Contexto REAL del colegio, calculado con todos sus estudiantes evaluados en la zona
    col = d.groupby("cole_cod_dane_establecimiento")["punt_global"]
    d["colegio_promedio_saber11"] = col.transform("mean")
    d["colegio_evaluados"] = col.transform("size")
    # Nivel del colegio = tercil del promedio global del colegio (conserva el "efecto colegio")
    d["nivel_colegio"] = pd.qcut(d["colegio_promedio_saber11"].rank(method="first"), 3,
                                 labels=["BAJO", "MEDIO", "ALTO"]).astype(str)

    # Posición de cada estudiante en la zona y DENTRO de su colegio (insumo de las notas, etapa 6)
    k = cfg["generador"]["bachillerato"]["encogimiento_colegio"]
    d["z_global"] = puntaje_normal(d["punt_global"])
    for area, c in AREAS_NOTA.items():
        d[f"z_{area}"] = puntaje_normal(d[c])
    media_col = d.groupby("cole_cod_dane_establecimiento")["z_global"].transform("mean")
    # Colegios con pocos evaluados: su promedio se acerca a la media de la zona (n / (n + k))
    d["z_colegio"] = media_col * d["colegio_evaluados"] / (d["colegio_evaluados"] + k)
    d["z_dentro_colegio"] = d["z_global"] - d["z_colegio"]
    print(f"  Registros ICFES: {n0:,} -> {len(d):,} válidos "
          f"({n0 - len(d):,} excluidos por estrato vacío, puntajes en 0 o edad imposible) "
          f"de {d['cole_cod_dane_establecimiento'].nunique():,} colegios")
    return d


# =============================================================================
# ETAPA 6b — Notas de grados 10 y 11 por área (SIMULADAS: supuestos S-25, S-34 a S-36)
# =============================================================================
def simular_notas_bachillerato(ref: pd.DataFrame, ld: pd.DataFrame, cfg: dict,
                               rng: np.random.Generator) -> tuple[pd.DataFrame, np.ndarray]:
    """Simula las notas finales de grados 10 y 11 en las cinco áreas que también evalúa el Saber 11.

    No hay un dato abierto colombiano que reúna, por estudiante, notas del colegio y puntaje Saber 11
    (bitácora H-31), así que las notas se simulan a partir del registro Saber 11 REAL de cada lead.

    Cada colegio fija su propio sistema de evaluación (Decreto 1290 de 2009, art. 4), así que la nota
    refleja sobre todo la posición del estudiante FRENTE A SUS COMPAÑEROS. La "nota latente" es:

        L = a·w + b·m + u_colegio + e
          w: qué tan arriba o abajo de su colegio quedó en el Saber 11 (dato real, estandarizado)
          m: nivel del colegio en el Saber 11 (dato real, estandarizado; peso pequeño)
          u: exigencia del colegio al calificar (aleatoria, la misma para todos sus estudiantes)
          e: esfuerzo, disciplina y asistencia, que pesan en la nota pero no en el examen

    Por eso aparecen casos de buen ICFES con promedio regular (colegio exigente o poco esfuerzo) y al revés.
    L se convierte al promedio en escala 3.0-5.0 con una distribución Beta (media y DE de S-25). Después se
    reparte en 10 notas: cada área se mueve según la fortaleza relativa del estudiante en esa prueba del
    Saber 11 y hay una tendencia de grado 10 a 11.
    Devuelve las notas (una fila por lead, grado y área) y el componente de esfuerzo estandarizado (etapa 9).
    """
    b = cfg["generador"]["bachillerato"]
    s_w, s_m = ref["z_dentro_colegio"].std(), ref["z_colegio"].std()
    var_u, peso_m = b["sd_exigencia_colegio"] ** 2, b["peso_nivel_colegio"]
    # Varianza total 1: a² + σe² = 1 − b² − σu²; entre compañeros corr(nota, Saber 11) = a / √(a² + σe²)
    resto = 1 - peso_m ** 2 - var_u
    a = b["correlacion_dentro_colegio"] * np.sqrt(resto)
    sd_e = np.sqrt(resto - a ** 2)

    colegios = np.sort(ref["cole_cod_dane_establecimiento"].unique())
    exigencia = dict(zip(colegios, rng.normal(0, np.sqrt(var_u), len(colegios))))
    n = len(ld)
    esfuerzo = rng.normal(size=n)
    latente = (a * ld["z_dentro_colegio"] / s_w + peso_m * ld["z_colegio"] / s_m
               + ld["cole_cod_dane_establecimiento"].map(exigencia) + sd_e * esfuerzo).to_numpy(float)

    m = (b["media"] - b["minimo_aprobado"]) / (5.0 - b["minimo_aprobado"])
    v = (b["sd"] / (5.0 - b["minimo_aprobado"])) ** 2
    k = m * (1 - m) / v - 1                                  # Beta con la media y la DE del supuesto S-25
    promedio_objetivo = b["minimo_aprobado"] + (5.0 - b["minimo_aprobado"]) * stats.beta.ppf(stats.norm.cdf(latente), m * k, (1 - m) * k)

    areas = list(AREAS_NOTA)
    fortaleza = ld[[f"z_{x}" for x in areas]].to_numpy(float).copy()
    fortaleza -= fortaleza.mean(axis=1, keepdims=True)                  # área fuerte (+) o débil (−) del estudiante
    tendencia = rng.normal(0, b["sd_tendencia_grado"], n)
    filas = []
    for grado, signo in [(10, -0.5), (11, 0.5)]:
        desv = b["sensibilidad_area"] * fortaleza + (signo * tendencia)[:, None] + rng.normal(0, b["sd_nota_area"], (n, len(areas)))
        filas.append(desv)
    desv = np.stack(filas, axis=1)                                       # (lead, grado, área)
    desv -= desv.mean(axis=(1, 2), keepdims=True)                        # el promedio de las 10 notas = objetivo
    notas = np.clip(np.round(promedio_objetivo[:, None, None] + desv, 1), b["minimo_aprobado"], 5.0)

    largo = pd.DataFrame({
        "fila": np.repeat(np.arange(n), 2 * len(areas)),
        "grado": np.tile(np.repeat([10, 11], len(areas)), n),
        "area": np.tile(areas, 2 * n),
        "nota": notas.reshape(-1)})
    return largo, esfuerzo


# =============================================================================
# ETAPA 2 — Residencia y selección de leads (modelo gravitacional de Huff)
# =============================================================================
def _con_direccion(df: pd.DataFrame, dirs: pd.DataFrame, idx: np.ndarray) -> pd.DataFrame:
    """Copia a df la dirección real número idx de la tabla de direcciones (con su coordenada y distancias)."""
    d = dirs.iloc[idx]
    return df.assign(codigo_direccion=d["codigo_fuente"].to_numpy(), direccion=d["direccion"].to_numpy(),
                     direccion_lat=d["lat"].round(6).to_numpy(), direccion_lon=d["lon"].round(6).to_numpy(),
                     distancia_campus_km=d["distancia_campus_km"].to_numpy(),
                     distancia_vial_km=d["distancia_vial_km"].to_numpy())


def asignar_residencia(pobl: pd.DataFrame, dirs: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Cada registro recibe una dirección REAL con coordenada (Catastro Bogotá o DANE) y su distancia al campus.

    Bogotá: localidad ~ P(localidad | estrato) ∝ población 15-19 × proporción de placas de ese estrato en la localidad
            (estratificación oficial por manzana de la SDP, S-19); luego una placa al azar de esa localidad en una
            manzana del MISMO estrato del registro ICFES. El barrio es el sector catastral de la placa.
    Sabana Centro: se conserva el municipio real del registro ICFES y se toma una dirección al azar del DANE.
    (El ICFES publica el municipio, no la dirección; por eso la dirección se asigna.)"""
    pob = cat.poblacion_15_19_localidades()
    conteo = cat.placas_por_localidad_estrato().set_index(["localidad", "estrato"])["placas"]
    proporcion = conteo / conteo.groupby(level="localidad").transform("sum")
    locs = [l["codigo"] for l in cat.LOCALIDADES]
    n = len(pobl)
    ubic, barrio, fila_dir = np.zeros(n, dtype=int), np.empty(n, dtype=object), np.full(n, -1)
    mpio, estr = pobl["estu_cod_reside_mcpio"].astype(str).to_numpy(), pobl["estrato"].to_numpy()
    for m in cat.MUNICIPIOS:
        idx = np.where(mpio == str(m["codigo"]))[0]
        ubic[idx] = m["codigo"]
        barrio[idx] = rng.choice(m["barrios"], size=len(idx))
        fila_dir[idx] = rng.choice(np.where(dirs["ubicacion_id"] == m["codigo"])[0], size=len(idx))
    for e in range(1, 7):
        idx = np.where((mpio == "11001") & (estr == e))[0]
        pesos = np.array([pob[l] * proporcion.get((l, e), 0.0) for l in locs], dtype=float)
        ubic[idx] = rng.choice(locs, size=len(idx), p=pesos / pesos.sum())
        for l in locs:
            filas = idx[ubic[idx] == l]
            if len(filas):
                candidatas = np.where((dirs["ubicacion_id"] == l) & (dirs["estrato"] == e))[0]
                fila_dir[filas] = rng.choice(candidatas, size=len(filas))
    assert (ubic > 0).all() and (fila_dir >= 0).all(), "Hay registros sin residencia o sin dirección"
    pobl = pobl.copy()
    pobl["ubicacion_id"] = ubic
    es_bogota = mpio == "11001"
    barrio[es_bogota] = dirs["barrio"].to_numpy()[fila_dir[es_bogota]]
    pobl["barrio"] = barrio
    pobl["fila_direccion"] = fila_dir
    pobl = _con_direccion(pobl, dirs, fila_dir)
    centro = cat.tabla_ubicaciones().set_index("ubicacion_id")["distancia_campus_km"]
    pobl["distancia_localidad_km"] = pobl["ubicacion_id"].map(centro)     # lo único que se sabe del lead
    return pobl


def direcciones_unicas(ld: pd.DataFrame, dirs: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Dos leads distintos no comparten vivienda: si una placa se repite, se toma otra de la misma localidad (o
    municipio) y del mismo estrato de manzana (en Bogotá)."""
    usadas: set[int] = set()
    filas = ld["fila_direccion"].to_numpy().copy()
    for i, f in enumerate(filas):
        if f in usadas:
            r = dirs.iloc[f]
            mismo = (dirs["ubicacion_id"] == r["ubicacion_id"]) & (dirs["estrato"] == r["estrato"])
            libres = np.setdiff1d(np.where(mismo)[0], list(usadas))
            if len(libres) == 0:                         # celda agotada: otra placa libre de la misma localidad
                libres = np.setdiff1d(np.where(dirs["ubicacion_id"] == r["ubicacion_id"])[0], list(usadas))
            filas[i] = rng.choice(libres)
        usadas.add(int(filas[i]))
    ld = ld.assign(fila_direccion=filas)
    ld["barrio"] = np.where(ld["ubicacion_id"] < 100, dirs["barrio"].to_numpy()[filas], ld["barrio"])
    return _con_direccion(ld, dirs, filas)


def otra_direccion(ubicacion_id: int, dirs: pd.DataFrame, rng: np.random.Generator) -> str:
    """Dirección real al azar en la misma localidad o municipio (vivienda del contacto de emergencia)."""
    return dirs.at[int(rng.choice(np.where(dirs["ubicacion_id"] == ubicacion_id)[0])), "direccion"]


def peso_seleccion(pobl: pd.DataFrame, cfg: dict) -> np.ndarray:
    """Peso relativo de que un bachiller de la población se registre como lead de Unicervantes (S-05).

    peso = w(estrato) × w(género) × w(puntaje) × max(distancia por vías desde su dirección, 2 km)^(-β)
    El último factor es el modelo gravitacional de Huff (1964): la atracción de un
    destino decae con la distancia.
    """
    s = cfg["generador"]["seleccion"]
    w = pobl["estrato"].map(s["peso_estrato"]).to_numpy(float).copy()
    w *= pobl["estu_genero"].map(s["peso_genero"]).to_numpy(float)
    g = pobl["punt_global"].to_numpy()
    wp = np.zeros(len(g))
    for tramo in s["peso_puntaje"]:
        wp[(g >= tramo["desde"]) & (g < tramo["hasta"])] = tramo["peso"]
    w *= wp
    w *= np.maximum(pobl["distancia_vial_km"].to_numpy(float), s["distancia_minima_km"]) ** (-s["beta_distancia"])
    return w


def repartir_cupos(cfg: dict) -> list[tuple[str, str]]:
    """Reparte N leads entre (programa, periodo de interés) según el volumen relativo (S-04)."""
    vol = cfg["generador"]["volumen_relativo"]
    pares = [(prog, per, v) for prog, d in vol.items() for per, v in d.items() if rn.programa_disponible(prog, per)]
    total = sum(v for *_, v in pares)
    n = cfg["proyecto"]["n_leads"]
    exactos = [n * v / total for *_, v in pares]
    cupos = [int(x) for x in exactos]
    for i in np.argsort([-(x - int(x)) for x in exactos])[: n - sum(cupos)]:   # mayor residuo
        cupos[i] += 1
    return [(prog, per) for (prog, per, _), c in zip(pares, cupos) for _ in range(c)]


# =============================================================================
# ETAPA 3 — Registro del lead: canal, evento, fecha y asesor
# =============================================================================
def eventos_por_campana(cfg: dict, corte: date) -> dict[tuple[str, str], dict]:
    """(campaña, canal) -> evento ya realizado a la fecha de corte."""
    res = {}
    for e in cfg["eventos_captacion"]:
        if date.fromisoformat(e["inicio"]) <= corte:
            res[(e["campana"], e["canal"])] = e
    return res


def fecha_en_ventana(inicio: date, fin: date, rng: np.random.Generator) -> date:
    """Fecha con densidad Beta(2, 1.5): el interés crece a medida que se acerca el inicio de clases."""
    return inicio + timedelta(days=int(rng.beta(2, 1.5) * max((fin - inicio).days, 1)))


# =============================================================================
# ETAPA 4 y 7 — Modelos logísticos con parámetros conocidos
# =============================================================================
def sigmoide(x):
    return 1 / (1 + np.exp(-x))


def logit_conversion(df: pd.DataFrame, a: dict, efecto_asesor: np.ndarray, intercepto: float) -> np.ndarray:
    """η = α0 + α_canal + α_estrato + α_dist·log(dist/10) + α_SSIA + efecto del asesor
    dist = distancia del centro de su localidad o municipio: del lead solo se conoce eso (la dirección llega con el
    formulario de inscripción)."""
    eta = (intercepto
           + df["canal"].map(a["alpha_canal"])
           + df["estrato"].map(a["alpha_estrato"])
           + a["alpha_log_distancia"] * np.log(np.maximum(df["distancia_localidad_km"], 2.0) / 10)
           + a["alpha_programa_ssia"] * (df["programa"] == "SSIA").astype(float)
           + efecto_asesor[df["asesor_id"].to_numpy() - 1])
    return np.asarray(eta, dtype=float)


def logit_matricula(df: pd.DataFrame, b: dict, intercepto: float) -> np.ndarray:
    """η = β0 + β_desc·descuento + β_estrato + β_dist·log(dist/10) + β_icfes·((global−280)/50)²
           + β_canal + β_entrevista + β_SSIA + β_periodo2 + β_FOES·apoyo_FOES"""
    eta = (intercepto
           + b["beta_descuento"] * df["pct_descuento_inicial"]
           + df["estrato"].map(b["beta_estrato"])
           + b["beta_log_distancia"] * np.log(np.maximum(df["distancia_vial_km"], 2.0) / 10)     # desde su dirección
           + b["beta_icfes_cuadratico"] * ((df["punt_global"] - 280) / 50) ** 2
           + df["canal"].map(b["beta_canal"])
           + b["beta_entrevista"] * df["entrevista_realizada"].astype(float)
           + b["beta_programa_ssia"] * (df["programa"] == "SSIA").astype(float)
           + b["beta_periodo_2"] * df["periodo"].str.endswith("-2").astype(float)
           + b["beta_foes"] * df["apoyo_foes"].astype(float))
    return np.asarray(eta, dtype=float)


def calibrar_intercepto(funcion_eta, tasa: float, peso=None) -> float:
    """Busca el intercepto (bisección) para que la probabilidad promedio sea `tasa`."""
    lo, hi = -10.0, 10.0
    for _ in range(60):
        mid = (lo + hi) / 2
        p = sigmoide(funcion_eta(mid))
        media = (p * peso).mean() if peso is not None else p.mean()
        lo, hi = (mid, hi) if media < tasa else (lo, mid)
    return (lo + hi) / 2


# =============================================================================
# ETAPA 5 — Datos personales (ficticios)
# =============================================================================
def sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)).lower()


class GeneradorPersonas:
    def __init__(self, semilla: int, rng: np.random.Generator):
        Faker.seed(semilla)
        self.fk = Faker("es_CO")
        self.rng = rng
        self.documentos: set = set()
        self.celulares: set[str] = set()
        self.correos: set[str] = set()

    def nombres(self, genero: str) -> str:
        f = self.fk.first_name_female if genero == "F" else self.fk.first_name_male
        uno = f()
        if self.rng.random() < 0.6:                       # en Colombia es común tener dos nombres
            dos = f()
            return f"{uno} {dos}" if dos != uno else uno
        return uno

    def apellido(self) -> str:
        return self.fk.last_name()

    def celular(self) -> str:
        prefijos = [300, 301, 302, 303, 304, 305, 310, 311, 312, 313, 314, 315, 316, 317, 318, 319, 320, 321,
                    322, 323, 324, 350, 351]
        while True:
            num = f"{self.rng.choice(prefijos)}{self.rng.integers(0, 10**7):07d}"
            if num not in self.celulares:
                self.celulares.add(num)
                return num

    def fijo(self) -> str:
        return f"601{self.rng.integers(2, 9)}{self.rng.integers(0, 10**6):06d}"

    def documento(self, tipo: str, anio_nac: int) -> str:
        while True:
            if tipo in ("TI", "CC") and anio_nac >= 1993:
                num = f"10{self.rng.integers(0, 10**8):08d}"         # NUIP de 10 dígitos
            elif tipo == "CC":
                num = f"{self.rng.choice([52, 53, 79, 80])}{self.rng.integers(0, 10**6):06d}"   # cédulas antiguas de 8 dígitos
            elif tipo == "CE":
                num = f"{self.rng.integers(10**5, 10**7)}"
            else:   # PPT
                num = f"{self.rng.integers(10**6, 10**7)}"
            if (tipo, num) not in self.documentos:
                self.documentos.add((tipo, num))
                return num

    def correo(self, nombres: str, apellido1: str) -> str:
        n1, a1 = sin_tildes(nombres.split()[0]), sin_tildes(apellido1.split()[0])
        while True:
            patron = self.rng.integers(3)
            base = [f"{n1}.{a1}", f"{n1}{a1}", f"{n1[0]}{a1}"][patron]
            c = f"{base}{self.rng.integers(1, 100)}@{cat.DOMINIO_CORREO}"
            if c not in self.correos:
                self.correos.add(c)
                return c


def elegir(rng: np.random.Generator, dist: dict):
    claves = list(dist)
    p = np.array([dist[k] for k in claves], dtype=float)
    return claves[rng.choice(len(claves), p=p / p.sum())]


def grupo_edad(edad: int) -> str:
    return "18-22" if edad <= 22 else ("23-29" if edad <= 29 else "30+")


# =============================================================================
# PROGRAMA PRINCIPAL
# =============================================================================
def main() -> None:
    asegurar_carpetas()
    SINTETICO_DIR.mkdir(parents=True, exist_ok=True)
    OCULTO_DIR.mkdir(parents=True, exist_ok=True)
    cfg = cargar_config()
    g, cap = cfg["generador"], cfg["generador"]["captacion"]
    semilla = cfg["proyecto"]["semilla"]
    corte = date.fromisoformat(cfg["proyecto"]["fecha_corte"])
    rng = np.random.default_rng(semilla)
    periodos = {p["codigo"]: p for p in cfg["periodos"]}

    print("ETAPA 0: registros reales del ICFES de la zona de influencia")
    ref = cargar_icfes_zona(cfg)
    ref.to_parquet(SINTETICO_DIR / "icfes_zona_referencia.parquet", index=False)
    for viejo in ["poblacion_saber11_sintetica", "icfes_entrenamiento", "icfes_reserva_validacion"]:
        (SINTETICO_DIR / f"{viejo}.parquet").unlink(missing_ok=True)    # salidas de la versión con cópula

    print("ETAPA 1 y 2: residencia y selección de leads entre los registros reales (Huff)")
    dirs = cat.direcciones()
    pobl = asignar_residencia(ref, dirs, rng)
    cupos = repartir_cupos(cfg)
    w = peso_seleccion(pobl, cfg)
    # Sin reemplazo: cada lead es un registro real DISTINTO (nunca se repite un estudiante)
    elegidos = rng.choice(len(pobl), size=len(cupos), replace=False, p=w / w.sum())
    ld = direcciones_unicas(pobl.iloc[elegidos].reset_index(drop=True), dirs, rng)
    n = len(ld)

    print("ETAPA 3: registro del lead (bloque 1): interés, canal, evento, fecha y asesor")
    orden = rng.permutation(n)
    ld["programa"] = [cupos[i][0] for i in orden]
    ld["periodo"] = [cupos[i][1] for i in orden]
    rezago = [elegir(rng, g["rezago_anios"]) for _ in range(n)]
    # S-33: el registro real (2019-2 o 2022-2) se ubica en el año de examen que corresponde al aspirante
    ld["anio_examen"] = [rn.anio_periodo(p) - 1 - r for p, r in zip(ld["periodo"], rezago)]
    ld["fecha_examen"] = [date(a, 8, 10) + timedelta(days=int(rng.integers(0, 28))) for a in ld["anio_examen"]]
    ld["fecha_nacimiento"] = [fe - timedelta(days=int(e * 365.25)) for fe, e in zip(ld["fecha_examen"], ld["edad_examen"])]

    colegios = ref.drop_duplicates("cole_cod_dane_establecimiento")["cole_cod_dane_establecimiento"]
    convenio = set(colegios[rng.random(len(colegios)) < g["prob_colegio_convenio"]])
    eventos = eventos_por_campana(cfg, corte)
    canales, evento_ids, registros = [], [], []
    for per, col in zip(ld["periodo"], ld["cole_cod_dane_establecimiento"]):
        ini, fin = rn.ventana_campana(per)
        fin = min(fin, corte)
        opciones = dict(g["canal"])
        if (per, "EXPOESTUDIANTES") not in eventos:
            opciones.pop("EXPOESTUDIANTES")                    # sin feria realizada para esa campaña
        if (per, "CAMPUS_DAY") not in eventos:
            opciones.pop("CAMPUS_DAY")
        opciones.pop("COLEGIO_CONVENIO")
        canal = "COLEGIO_CONVENIO" if (col in convenio and rng.random() < 0.6) else elegir(rng, opciones)
        ev = eventos.get((per, canal))
        if ev:
            e0, e1 = date.fromisoformat(ev["inicio"]), date.fromisoformat(ev["fin"])
            fecha = e0 + timedelta(days=int(rng.integers(0, (e1 - e0).days + 1)))
        else:
            fecha = fecha_en_ventana(ini, fin, rng)
        canales.append(canal)
        evento_ids.append(ev["evento_id"] if ev else None)
        registros.append(fecha)
    ld["canal"], ld["evento_id"], ld["fecha_registro"] = canales, evento_ids, registros
    ld["asesor_id"] = rng.integers(1, cap["n_asesores"] + 1, size=n)
    ld["edad_al_registro"] = [rn.edad_en(fn, fr) for fn, fr in zip(ld["fecha_nacimiento"], ld["fecha_registro"])]

    print("ETAPA 4: conversión lead -> inscripción (modelo logístico verdadero)")
    a = cap["conversion_lead"]
    efecto_asesor = rng.normal(0, cap["sd_efecto_asesor"], cap["n_asesores"])
    historico = (ld["periodo"] != CAMPANA).to_numpy()
    alpha0 = calibrar_intercepto(lambda c: logit_conversion(ld[historico], a, efecto_asesor, c), a["tasa_objetivo"])
    ld["prob_conversion_verdadera"] = sigmoide(logit_conversion(ld, a, efecto_asesor, alpha0))
    convierte = rng.random(n) < ld["prob_conversion_verdadera"]
    gam = cap["retraso_inscripcion_gamma"]
    fechas_insc = []
    for conv, fr, per, fe in zip(convierte, ld["fecha_registro"], ld["periodo"], ld["fecha_examen"]):
        if not conv:
            fechas_insc.append(None)
            continue
        f = fr + timedelta(days=int(rng.gamma(gam["forma"], gam["escala_dias"])))
        f = max(f, fe + timedelta(days=DIAS_PUBLICACION_ICFES))   # se inscribe con su resultado Saber 11 (S-30)
        fin = rn.ventana_campana(per)[1]
        f = min(f, fin)
        fechas_insc.append(f if (f <= corte and f >= fr) else None)
    ld["fecha_inscripcion"] = fechas_insc
    ld["inscrito"] = ld["fecha_inscripcion"].notna()
    print(f"  conversión (histórico) = {ld.loc[historico, 'inscrito'].mean():.3f} · α0 = {alpha0:.3f} · "
          f"inscritos = {ld['inscrito'].sum():,} de {n:,} leads")

    print("ETAPA 5: datos personales (preinscripción y formulario de admisión)")
    gp = GeneradorPersonas(semilla, rng)
    ubic = cat.tabla_ubicaciones().set_index("ubicacion_id")
    filas_asp, filas_form, filas_ce = [], [], []
    for i, r in ld.iterrows():
        nombres = gp.nombres(r["estu_genero"])
        ap1, ap2 = gp.apellido(), gp.apellido()
        filas_asp.append({
            "aspirante_id": i + 1, "fecha_registro": r["fecha_registro"], "periodo_interes": r["periodo"],
            "programa_interes": r["programa"], "nombres": nombres, "apellidos": f"{ap1} {ap2}",
            "genero": r["estu_genero"], "edad_al_registro": int(r["edad_al_registro"]), "celular": gp.celular(),
            "correo": gp.correo(nombres, ap1), "ubicacion_id": int(r["ubicacion_id"]), "estrato": int(r["estrato"]),
            "colegio_cod_dane": r["cole_cod_dane_establecimiento"], "canal": r["canal"], "evento_id": r["evento_id"],
            "asesor_id": int(r["asesor_id"]), "dato_sintetico": True})
        if not r["inscrito"]:
            continue
        edad = rn.edad_en(r["fecha_nacimiento"], r["fecha_inscripcion"])
        nac = "COLOMBIA" if r["estu_nacionalidad"] == "COLOMBIA" else r["estu_nacionalidad"]
        tipo = rn.tipo_documento_colombiano(edad) if nac == "COLOMBIA" else elegir(rng, g["documento_extranjero"])
        if nac not in ("COLOMBIA", "VENEZUELA"):
            tipo = "CE"
        estado = "SOLTERO" if edad < 18 else elegir(rng, g["estado_civil"][grupo_edad(edad)])
        if rng.random() < cat.PROB_REGIMEN_ESPECIAL:
            regimen = "ESPECIAL"
        else:
            regimen = "SUBSIDIADO" if rng.random() < cat.PROB_SUBSIDIADO[r["estrato"]] else "CONTRIBUTIVO"
        eps_opc = [e for e in cat.EPS if e["regimen"] == regimen]
        eps = eps_opc[rng.choice(len(eps_opc), p=np.array([e["peso"] for e in eps_opc]) / sum(e["peso"] for e in eps_opc))]
        if nac == "COLOMBIA":
            lugar = elegir(rng, cat.LUGAR_NACIMIENTO_COL)
            lugar = f"{ubic.loc[r['ubicacion_id'], 'municipio'] if lugar == 'MUNICIPIO_RESIDENCIA' else lugar}, Colombia"
        elif nac == "VENEZUELA":
            lugar = f"{rng.choice(cat.LUGAR_NACIMIENTO_VEN)}, Venezuela"
        else:
            lugar = nac.title()
        direccion = r["direccion"]
        filas_form.append({
            "aspirante_id": i + 1, "fecha_nacimiento": r["fecha_nacimiento"], "edad_al_inscribirse": int(edad),
            "nacionalidad": nac, "tipo_documento": tipo, "numero_documento": gp.documento(tipo, r["fecha_nacimiento"].year),
            "telefono_fijo": gp.fijo() if rng.random() < g["prob_telefono_fijo"] else None, "barrio": r["barrio"],
            "direccion": direccion, "estado_civil": estado, "eps": eps["nombre"], "regimen_salud": regimen,
            "lugar_nacimiento": lugar, "codigo_direccion": r["codigo_direccion"], "direccion_lat": r["direccion_lat"],
            "direccion_lon": r["direccion_lon"], "distancia_campus_km": r["distancia_campus_km"],
            "distancia_vial_km": r["distancia_vial_km"]})
        par = elegir(rng, cat.PARENTESCOS)
        if par == "CONYUGE/COMPAÑERO/A" and estado == "SOLTERO":
            par = "MADRE"
        if estado != "SOLTERO" and rng.random() < 0.6:
            par = "CONYUGE/COMPAÑERO/A"
        if par == "MADRE":
            nom_ce = f"{gp.nombres('F')} {ap2} {gp.apellido()}"
        elif par == "PADRE":
            nom_ce = f"{gp.nombres('M')} {ap1} {gp.apellido()}"
        elif par == "HERMANO/A":
            nom_ce = f"{gp.nombres(rng.choice(['F', 'M']))} {ap1} {ap2}"
        else:
            nom_ce = f"{gp.nombres(rng.choice(['F', 'M']))} {gp.apellido()} {gp.apellido()}"
        misma_casa = par in ("MADRE", "PADRE", "HERMANO/A", "CONYUGE/COMPAÑERO/A") and rng.random() < 0.85
        filas_ce.append({"contacto_id": len(filas_ce) + 1, "aspirante_id": i + 1, "nombre_completo": nom_ce,
                         "parentesco": par,
                         "direccion": direccion if misma_casa else otra_direccion(int(r["ubicacion_id"]), dirs, rng),
                         "celular": gp.celular()})
    aspirante, formulario, contacto = pd.DataFrame(filas_asp), pd.DataFrame(filas_form), pd.DataFrame(filas_ce)

    print("ETAPA 6: documentos académicos (bloque 2): Saber 11 real y notas de grados 10 y 11 simuladas")
    publicado = [fe + timedelta(days=DIAS_PUBLICACION_ICFES) for fe in ld["fecha_examen"]]
    declara = ld["inscrito"] | ((rng.random(n) < cap["prob_declara_saber11_sin_inscripcion"])
                                & (pd.Series(publicado) <= ld["fecha_registro"]))
    media_g, sd_g = ref["punt_global"].mean(), ref["punt_global"].std()
    notas, ld["esfuerzo_colegio"] = simular_notas_bachillerato(ref, ld, cfg, rng)
    notas["aspirante_id"] = notas["fila"] + 1
    notas["anio_lectivo"] = ld["anio_examen"].to_numpy()[notas["fila"]] - (11 - notas["grado"])   # Saber 11 en grado 11
    ld["promedio_acumulado_colegio"] = notas.groupby("fila")["nota"].mean().round(2).to_numpy()
    doc = ld[declara]
    resultado_s11 = pd.DataFrame({"aspirante_id": doc.index + 1, "anio_examen": doc["anio_examen"],
                                  "punt_lectura_critica": doc["punt_lectura_critica"],
                                  "punt_matematicas": doc["punt_matematicas"],
                                  "punt_sociales": doc["punt_sociales_ciudadanas"],
                                  "punt_ciencias": doc["punt_c_naturales"], "punt_ingles": doc["punt_ingles"],
                                  "punt_global": doc["punt_global"],
                                  "registro_icfes": doc["estu_consecutivo"], "periodo_icfes_origen": doc["periodo_icfes"]})
    historial = pd.DataFrame({"aspirante_id": doc.index + 1, "promedio_acumulado_colegio": doc["promedio_acumulado_colegio"],
                              "escala_colegio": "1.0-5.0",
                              "desempeno_nacional": [rn.desempeno_bachillerato(p) for p in doc["promedio_acumulado_colegio"]]})
    nota_bachillerato = notas[notas["aspirante_id"].isin(historial["aspirante_id"])].assign(
        desempeno_nacional=lambda x: x["nota"].map(rn.desempeno_bachillerato))[
        ["aspirante_id", "grado", "anio_lectivo", "area", "nota", "desempeno_nacional"]].reset_index(drop=True)

    print("ETAPA 7: proceso de admisión (bloque 2): becas, valores, matrícula, beneficio y financiación")
    ins = ld[ld["inscrito"]].copy()
    ins["aspirante_id"] = ins.index + 1
    ins = ins.reset_index(drop=True)
    ins.insert(0, "inscripcion_id", np.arange(1, len(ins) + 1))
    ins["entrevista_realizada"] = rng.random(len(ins)) < g["prob_entrevista"]
    base_voc = {1: .05, 2: .15, 3: .35, 4: .30, 5: .15}
    alto_voc = {1: .02, 2: .08, 3: .25, 4: .38, 5: .27}       # inmersión y referidos llegan más convencidos
    ins["puntaje_vocacional"] = [
        (elegir(rng, alto_voc if c in ("INMERSION", "REFERIDO") else base_voc) if e else None)
        for c, e in zip(ins["canal"], ins["entrevista_realizada"])]
    becas, evaluaciones = [], []
    for iid, pg, e, pv in zip(ins["inscripcion_id"], ins["punt_global"], ins["entrevista_realizada"], ins["puntaje_vocacional"]):
        cumple_s11, cumple_mv = rn.beca_por_icfes(pg), rn.cumple_mi_vocacion(e, pv)
        evaluaciones += [{"inscripcion_id": iid, "beca": "SABER_11", "cumple_requisitos": cumple_s11,
                          "criterio": f"Puntaje global {pg} {'≥' if cumple_s11 else '<'} 310"},
                         {"inscripcion_id": iid, "beca": "MI_VOCACION", "cumple_requisitos": cumple_mv,
                          "criterio": "Sin entrevista" if not e else f"Puntaje vocacional {pv} ({'≥' if cumple_mv else '<'} 3)"}]
        if cumple_s11:
            # S-02: no son acumulables y se aplica la mayor; quien califica a Saber 11 no recibe Mi Vocación.
            becas.append("SABER_11" if rng.random() < g["prob_solicita_beca_saber11"] else "NINGUNA")
        elif cumple_mv and rng.random() < g["prob_mi_vocacion_por_puntaje_vocacional"][pv]:
            becas.append("MI_VOCACION")
        else:
            becas.append("NINGUNA")
    ins["beca"] = becas
    evaluacion = pd.DataFrame(evaluaciones)
    ins["pct_descuento_inicial"] = [rn.pct_beca(b, 1) for b in becas]
    ins["valor_semestre_bruto"] = [rn.tarifa(p, rn.anio_periodo(per)) for p, per in zip(ins["programa"], ins["periodo"])]
    ins["valor_neto_primer_semestre"] = [rn.valor_neto(v, d) for v, d in zip(ins["valor_semestre_bruto"], ins["pct_descuento_inicial"])]
    ins["admitido"] = rng.random(len(ins)) < g["prob_admitido"]

    # Fondos municipales (FOES/FOEST): el aspirante residente solicita el apoyo con su certificado de
    # inscripción, ANTES de pagar la matrícula; por eso es un predictor válido (no es fuga de datos).
    fondos = cfg["fondos_educacion_municipal"]
    ins["fondo_elegible"] = [rn.fondo_municipal(u) for u in ins["ubicacion_id"]]
    ins["elegible_foes"] = ins["fondo_elegible"].notna()
    ins["apoyo_foes"] = ins["elegible_foes"] & (rng.random(len(ins)) < g["foes"]["prob_solicita_y_aprueba"])
    ins["fondo_id"] = [f if apo else None for f, apo in zip(ins["fondo_elegible"], ins["apoyo_foes"])]

    b = g["matricula"]
    hist_ins = (ins["periodo"] != CAMPANA).to_numpy()
    beta0 = calibrar_intercepto(lambda c: logit_matricula(ins[hist_ins], b, c), b["tasa_objetivo"],
                                peso=ins.loc[hist_ins, "admitido"].to_numpy())
    ins["prob_matricula_verdadera"] = sigmoide(logit_matricula(ins, b, beta0))
    resultado = (rng.random(len(ins)) < ins["prob_matricula_verdadera"]) & ins["admitido"]
    # 2027-1 está en campaña: el resultado aún NO existe. Se guarda "sellado" para el Sprint 5.
    sellado = ins.loc[~hist_ins, ["inscripcion_id"]].assign(matriculado_real=resultado[~hist_ins].astype(int))
    sellado.to_parquet(OCULTO_DIR / "resultado_2027_1_sellado.parquet", index=False)
    ins["matriculado"] = np.where(hist_ins, resultado.astype(int), np.nan)
    es_mat = (ins["matriculado"] == 1).to_numpy()

    dm = g["dias_matricula_antes_de_clases"]
    fechas_mat = []
    for m, per, fi in zip(es_mat, ins["periodo"], ins["fecha_inscripcion"]):
        if not m:
            fechas_mat.append(None)
            continue
        inicio = date.fromisoformat(periodos[per]["inicio_clases"])
        fechas_mat.append(max(fi + timedelta(days=1), inicio - timedelta(days=int(rng.integers(dm["min"], dm["max"] + 1)))))
    ins["fecha_matricula"] = fechas_mat
    bf, fin_cfg = g["beneficio_primer_semestre"], g["financiacion"]
    ins["beneficio"] = [elegir(rng, bf["cerca"] if d <= bf["cerca_hasta_km"] else bf["lejos"]) if m else None
                        for m, d in zip(es_mat, ins["distancia_vial_km"])]
    modalidad, entidad = [], []
    for m, e in zip(es_mat, ins["estrato"]):
        if not m:
            modalidad.append(None), entidad.append(None)
        elif rng.random() < fin_cfg["prob_credito_por_estrato"][e]:
            modalidad.append("CREDITO_EDUCATIVO"), entidad.append(elegir(rng, fin_cfg["pesos_entidad"]))
        else:
            modalidad.append("RECURSOS_PROPIOS"), entidad.append(None)
    ins["modalidad_financiacion"], ins["entidad_financiera"] = modalidad, entidad
    cambio = []
    for m, d in zip(es_mat, ins["distancia_vial_km"]):
        if not m:
            cambio.append(None)
            continue
        p = next(t["prob"] for t in g["prob_cambio_residencia"] if t["desde_km"] <= d < t["hasta_km"])
        cambio.append(bool(rng.random() < p))
    ins["cambio_residencia_por_cercania"] = cambio

    # Documentos soporte (posible FUGA DE DATOS: se entregan al formalizar la matrícula)
    docs = []
    for r in ins.itertuples():
        for tipo_doc in cat.DOCUMENTOS_SOPORTE:
            p = 0.99 if r.matriculado == 1 else (0.50 if r.periodo == CAMPANA else 0.45)
            entregado = bool(rng.random() < p)
            fecha = min(r.fecha_inscripcion + timedelta(days=int(rng.integers(0, 35))), corte) if entregado else None
            docs.append({"inscripcion_id": r.inscripcion_id, "tipo_documento_soporte": tipo_doc,
                         "entregado": entregado, "fecha_entrega": fecha})
    documento = pd.DataFrame(docs)

    print("ETAPA 8: gestión del lead (bloque 5): contactos de asesores e inversión de captación")
    it = cap["interacciones"]
    fecha_ins_por_lead = dict(zip(ins["aspirante_id"], ins["fecha_inscripcion"]))
    fecha_mat_por_lead = dict(zip(ins["aspirante_id"], ins["fecha_matricula"]))
    contactos = []
    for i, r in ld.iterrows():
        aid = i + 1
        campana = r["periodo"] == CAMPANA
        if rng.random() < (it["prob_sin_contacto_campana"] if campana else it["prob_sin_contacto_historico"]):
            continue
        fi = fecha_ins_por_lead.get(aid)
        limite = min(fi if fi else rn.ventana_campana(r["periodo"])[1], corte)
        k = 1 + rng.poisson(it["lambda_contactos"] + (it["extra_si_inscribe"] if fi else 0))
        t = r["fecha_registro"] + timedelta(days=int(rng.exponential(it["dias_primer_contacto"])))
        fechas = []
        for _ in range(k):
            if t > limite:
                break
            fechas.append(t)
            t = t + timedelta(days=1 + int(rng.exponential(it["dias_entre_contactos"])))
        for j, f in enumerate(fechas):
            ultimo = j == len(fechas) - 1
            if ultimo and fi:
                res = "CONFIRMA_INSCRIPCION"
            elif ultimo and not campana:
                res = elegir(rng, it["resultado_final_no_inscrito"])
            else:
                res = elegir(rng, it["resultado_intermedio"])
            contactos.append({"aspirante_id": aid, "asesor_id": int(r["asesor_id"]), "fecha": f,
                              "tipo": elegir(rng, it["tipo"]), "resultado": res})
        fm = fecha_mat_por_lead.get(aid)
        if fi:                                               # seguimiento posterior para formalizar la matrícula
            f = fi + timedelta(days=1 + int(rng.exponential(5)))
            if f <= corte and (fm is None or pd.isna(fm) or f <= fm):
                contactos.append({"aspirante_id": aid, "asesor_id": int(r["asesor_id"]), "fecha": f,
                                  "tipo": elegir(rng, it["tipo"]), "resultado": "SEGUIMIENTO_MATRICULA"})
    interaccion = pd.DataFrame(contactos).sort_values(["aspirante_id", "fecha"]).reset_index(drop=True)
    interaccion.insert(0, "interaccion_id", np.arange(1, len(interaccion) + 1))

    fk = Faker("es_CO")
    fk.seed_instance(semilla + 1)
    asesor = pd.DataFrame([{"asesor_id": k + 1, "nombre": f"{fk.first_name()} {fk.last_name()}",
                            "equipo": "Admisiones y Mercadeo - Bogotá", "activo": True}
                           for k in range(cap["n_asesores"])])

    inv_cfg = cfg["inversion_captacion"]
    inversion = []
    for per in periodos:
        sem = per.split("-")[1]
        ini, fin = rn.ventana_campana(per)
        fraccion = 1.0 if fin <= corte else max(0.0, (corte - ini).days / (fin - ini).days)   # campaña en curso: ejecutado a la fecha
        for canal, valores in inv_cfg["por_periodo"].items():
            inversion.append({"periodo": per, "canal": canal, "evento_id": None, "concepto": f"Inversión {canal.lower()} campaña {per}",
                              "valor_cop": int(round(valores[sem] * fraccion, -3)), "fuente": "supuesto: S-26"})
        for e in cfg["eventos_captacion"]:
            if e["campana"] == per and date.fromisoformat(e["inicio"]) <= corte:
                inversion.append({"periodo": per, "canal": e["canal"], "evento_id": e["evento_id"],
                                  "concepto": f"Participación en {e['nombre']}",
                                  "valor_cop": inv_cfg["por_evento"][e["canal"]], "fuente": "supuesto: S-26"})
    inversion = pd.DataFrame(inversion)
    inversion.insert(0, "inversion_id", np.arange(1, len(inversion) + 1))
    evento = pd.DataFrame([{k: e[k] for k in ["evento_id", "nombre", "canal", "inicio", "fin", "lugar", "organizador", "campana", "fuente"]}
                           for e in cfg["eventos_captacion"]])

    print("ETAPA 9: seguimiento académico, deserción y conservación de beca")
    rend, des = g["rendimiento"], g["desercion"]
    seg = []
    for r in ins[es_mat].itertuples():
        zz = (r.punt_global - media_g) / sd_g
        # S-36: el esfuerzo que se ve en las notas del colegio (y no en el ICFES) también pesa en la universidad
        ro, re_ = rend["rho_icfes"], rend["rho_esfuerzo_colegio"]
        habilidad = ro * zz + re_ * r.esfuerzo_colegio + np.sqrt(1 - ro ** 2 - re_ ** 2) * rng.normal()
        efecto_e = rend["efecto_estrato_bajo"] if r.estrato <= 2 else 0.0
        beca_activa, promedios, per, k = r.beca != "NINGUNA", [], r.periodo, 1
        foes_activo = bool(r.apoyo_foes)
        monto_foes = fondos[r.fondo_id]["apoyo_semestral_cop"] if isinstance(r.fondo_id, str) else 0
        while per in periodos and date.fromisoformat(periodos[per]["inicio_clases"]) <= corte:
            cerrado = date.fromisoformat(periodos[per]["fin"]) < corte
            pct = rn.pct_descuento_total(r.beca, k, beca_activa)
            fila = {"inscripcion_id": r.inscripcion_id, "semestre_cursado": k, "periodo": per,
                    "beca_activa_inicio": beca_activa if r.beca != "NINGUNA" else None,
                    "pct_descuento_aplicado": pct,
                    "valor_bruto": rn.tarifa(r.programa, rn.anio_periodo(per)),
                    "valor_pagado": rn.valor_neto(rn.tarifa(r.programa, rn.anio_periodo(per)), pct),
                    "apoyo_foes_cop": min(monto_foes, rn.valor_neto(rn.tarifa(r.programa, rn.anio_periodo(per)), pct)) if foes_activo else 0,
                    "promedio_semestre": None, "promedio_acumulado": None, "sancion_disciplinaria": None,
                    "conserva_beca": None, "estado": "EN_CURSO"}
            if not cerrado:                     # semestre en curso: aún no hay notas (censura)
                seg.append(fila)
                break
            nota = (rend["media"] + (rend["ajuste_primer_semestre"] if k == 1 else 0) + efecto_e
                    + rend["sd_estudiante"] * habilidad + rend["sd_semestre"] * rng.normal())
            nota = float(np.clip(round(nota, 2), 0.0, 5.0))
            promedios.append(nota)
            acumulado = round(float(np.mean(promedios)), 2)
            sancion = bool(rng.random() < rend["prob_sancion_semestre"])
            conserva = rn.conserva_beca(acumulado, sancion) if beca_activa else None
            fila.update(promedio_semestre=nota, promedio_acumulado=acumulado, sancion_disciplinaria=sancion,
                        conserva_beca=conserva, estado="APROBADO_SEMESTRE")
            perdio = beca_activa and not conserva
            riesgo = des["riesgo_base"].get(k, des["riesgo_base"][3])
            riesgo *= des["multiplicador_promedio_bajo"] if nota < 3.0 else 1.0
            riesgo *= des["multiplicador_perdio_beca"] if perdio else 1.0
            if rng.random() < min(riesgo, 0.95):
                fila["estado"] = "DESERTA"
                seg.append(fila)
                break
            seg.append(fila)
            if perdio:
                beca_activa = False             # S-21: la pérdida es definitiva
            if foes_activo and not (rn.foes_renueva(nota) and rng.random() < g["foes"]["prob_renueva"]):
                foes_activo = False             # S-32: sin el promedio exigido (o sin renovar a tiempo) se pierde
            per, k = rn.periodo_siguiente(per), k + 1
    seguimiento = pd.DataFrame(seg)
    seguimiento.insert(0, "seguimiento_id", np.arange(1, len(seguimiento) + 1))

    # ----------------------------------------------------------- tablas finales
    usados = ld["cole_cod_dane_establecimiento"].unique()
    colegio = (ld.drop_duplicates("cole_cod_dane_establecimiento")
               [["cole_cod_dane_establecimiento", "cole_nombre_establecimiento", "cole_naturaleza", "cole_caracter",
                 "cole_jornada", "cole_bilingue", "cole_mcpio_ubicacion", "nivel_colegio", "colegio_promedio_saber11",
                 "colegio_evaluados"]]
               .rename(columns={"cole_cod_dane_establecimiento": "colegio_cod_dane", "cole_nombre_establecimiento": "nombre",
                                "cole_naturaleza": "naturaleza", "cole_caracter": "caracter", "cole_jornada": "jornada",
                                "cole_bilingue": "bilingue", "cole_mcpio_ubicacion": "municipio", "nivel_colegio": "nivel",
                                "colegio_promedio_saber11": "promedio_saber11", "colegio_evaluados": "estudiantes_evaluados"}))
    colegio["promedio_saber11"] = colegio["promedio_saber11"].round(1)
    colegio["naturaleza"] = colegio["naturaleza"].replace({"NO OFICIAL": "PRIVADO"})
    colegio["en_convenio"] = colegio["colegio_cod_dane"].isin(convenio)
    colegio["bilingue"] = colegio["bilingue"].map({"S": True, "N": False})
    assert len(colegio) == len(usados)
    inscripcion = ins[["inscripcion_id", "aspirante_id", "programa", "periodo", "fecha_inscripcion", "entrevista_realizada",
                       "puntaje_vocacional", "beca", "pct_descuento_inicial", "valor_semestre_bruto",
                       "valor_neto_primer_semestre", "admitido", "matriculado", "fecha_matricula",
                       "beneficio", "modalidad_financiacion", "entidad_financiera", "elegible_foes", "fondo_id",
                       "cambio_residencia_por_cercania"]]

    tablas = {"aspirante": aspirante, "formulario_admision": formulario, "contacto_emergencia": contacto,
              "resultado_saber11": resultado_s11, "historial_bachillerato": historial,
              "nota_bachillerato": nota_bachillerato, "colegio": colegio,
              "inscripcion": inscripcion, "evaluacion_beca": evaluacion, "documento_soporte": documento,
              "seguimiento_academico": seguimiento, "asesor": asesor, "interaccion": interaccion,
              "evento_captacion": evento, "inversion_captacion": inversion}
    for nombre, t in tablas.items():
        t.to_parquet(SINTETICO_DIR / f"{nombre}.parquet", index=False)

    parametros = {"intercepto_calibrado": beta0, **{k: v for k, v in b.items()}, "media_global_ref": media_g,
                  "sd_global_ref": sd_g, "conversion_intercepto": alpha0, "conversion": a,
                  "efecto_asesor": efecto_asesor.tolist()}
    (OCULTO_DIR / "parametros_verdaderos.json").write_text(json.dumps(parametros, ensure_ascii=False, indent=2, default=str),
                                                          encoding="utf-8")
    print("\nResumen:")
    for nombre, t in tablas.items():
        print(f"  {nombre:<24} {len(t):>6,} filas")
    print(f"  tasa de matrícula (inscritos históricos) = {ins.loc[hist_ins, 'matriculado'].mean():.3f}   β0 = {beta0:.3f}")
    print(f"  becas en inscritos: {ins['beca'].value_counts(normalize=True).round(3).to_dict()}")
    rh = resultado_s11.merge(historial, on="aspirante_id")
    print(f"  correlación Saber 11 global vs. promedio del colegio = "
          f"{np.corrcoef(rh['punt_global'], rh['promedio_acumulado_colegio'])[0, 1]:.3f}")


if __name__ == "__main__":
    main()
