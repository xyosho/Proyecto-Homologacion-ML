"""Catálogos de referencia (listas de valores permitidos) con su fuente.

Separar los catálogos del generador permite auditarlos: cada lista dice de dónde sale.
Los valores marcados como supuesto (S-xx) están en config/reglas_negocio.yaml.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from comun import DATA_RAW, cargar_config

# ---------------------------------------------------------------------------
# Ubicaciones: 19 localidades urbanas de Bogotá + 11 municipios de Sabana Centro.
# Coordenadas: centroides urbanos aproximados (OpenStreetMap). Sumapaz se excluye (rural).
# estratos: distribución aproximada de hogares por estrato en la localidad. Desde el 23-oct-2026 la generación usa la
#           capa oficial (estratificación por manzana de la SDP, s01b); estos valores quedan como referencia.
# calles/carreras y barrios: referencia de la versión anterior. Hoy la dirección de Bogotá es una placa real de Catastro
#           y el barrio es su sector catastral; en Sabana Centro la dirección es del DANE y el barrio sale de esta lista.
# ---------------------------------------------------------------------------
LOCALIDADES = [
    {"codigo": 1, "nombre": "Usaquén", "lat": 4.725, "lon": -74.035,
     "estratos": {1: .03, 2: .10, 3: .22, 4: .25, 5: .17, 6: .23},
     "calles": (100, 200, ""), "carreras": (1, 50, ""),
     "barrios": [("Santa Bárbara", 5, 6), ("Cedritos", 4, 5), ("Toberín", 3, 3), ("Verbenal", 1, 2),
                 ("Usaquén", 5, 6), ("San Cristóbal Norte", 2, 3), ("Country Club", 6, 6), ("Lisboa", 2, 3)]},
    {"codigo": 2, "nombre": "Chapinero", "lat": 4.648, "lon": -74.060,
     "estratos": {1: .03, 2: .05, 3: .07, 4: .25, 5: .15, 6: .45},
     "calles": (39, 99, ""), "carreras": (1, 20, ""),
     "barrios": [("Chicó", 6, 6), ("Rosales", 6, 6), ("Chapinero Central", 3, 4), ("Quinta Camacho", 5, 5),
                 ("El Lago", 5, 5), ("Pardo Rubio", 2, 4), ("San Luis", 1, 2)]},
    {"codigo": 3, "nombre": "Santa Fe", "lat": 4.605, "lon": -74.066,
     "estratos": {1: .15, 2: .45, 3: .30, 4: .08, 5: .01, 6: .01},
     "calles": (1, 39, ""), "carreras": (1, 14, " Este"),
     "barrios": [("Las Aguas", 3, 4), ("La Macarena", 4, 4), ("Las Cruces", 2, 2), ("Lourdes", 1, 2),
                 ("La Perseverancia", 2, 2), ("Germania", 3, 3)]},
    {"codigo": 4, "nombre": "San Cristóbal", "lat": 4.560, "lon": -74.085,
     "estratos": {1: .25, 2: .65, 3: .10},
     "calles": (1, 50, " Sur"), "carreras": (1, 15, " Este"),
     "barrios": [("20 de Julio", 2, 3), ("La Victoria", 1, 2), ("Villa Javier", 2, 2), ("Altamira", 1, 2),
                 ("Los Libertadores", 1, 2), ("San Blas", 2, 3)]},
    {"codigo": 5, "nombre": "Usme", "lat": 4.490, "lon": -74.115,
     "estratos": {1: .55, 2: .43, 3: .02},
     "calles": (50, 135, " Sur"), "carreras": (1, 20, " Este"),
     "barrios": [("Santa Librada", 2, 2), ("Usme Pueblo", 1, 2), ("Danubio", 1, 2), ("Yomasa", 1, 2),
                 ("Alfonso López", 1, 1)]},
    {"codigo": 6, "nombre": "Tunjuelito", "lat": 4.575, "lon": -74.135,
     "estratos": {2: .45, 3: .55},
     "calles": (47, 75, " Sur"), "carreras": (10, 35, ""),
     "barrios": [("Tunjuelito", 2, 3), ("San Carlos", 3, 3), ("Venecia", 2, 3), ("Abraham Lincoln", 2, 2),
                 ("Fátima", 3, 3)]},
    {"codigo": 7, "nombre": "Bosa", "lat": 4.615, "lon": -74.190,
     "estratos": {1: .10, 2: .85, 3: .05},
     "calles": (49, 90, " Sur"), "carreras": (72, 100, ""),
     "barrios": [("Bosa Centro", 2, 2), ("Bosa Recreo", 2, 3), ("El Porvenir", 2, 2), ("Brasilia", 2, 2),
                 ("Islandia", 1, 2)]},
    {"codigo": 8, "nombre": "Kennedy", "lat": 4.630, "lon": -74.155,
     "estratos": {1: .03, 2: .45, 3: .47, 4: .05},
     "calles": (1, 50, " Sur"), "carreras": (68, 100, ""),
     "barrios": [("Kennedy Central", 3, 3), ("Castilla", 3, 4), ("Timiza", 2, 3), ("Patio Bonito", 1, 2),
                 ("Américas", 3, 3), ("Carvajal", 2, 3), ("Banderas", 3, 3)]},
    {"codigo": 9, "nombre": "Fontibón", "lat": 4.675, "lon": -74.145,
     "estratos": {2: .10, 3: .55, 4: .33, 5: .02},
     "calles": (13, 26, ""), "carreras": (90, 140, ""),
     "barrios": [("Modelia", 4, 4), ("Hayuelos", 4, 4), ("Fontibón Centro", 3, 3), ("Zona Franca", 2, 3),
                 ("Capellanía", 4, 5)]},
    {"codigo": 10, "nombre": "Engativá", "lat": 4.705, "lon": -74.110,
     "estratos": {1: .01, 2: .23, 3: .70, 4: .06},
     "calles": (63, 91, ""), "carreras": (68, 130, ""),
     "barrios": [("Normandía", 4, 4), ("Boyacá Real", 3, 3), ("Engativá Pueblo", 2, 2), ("Minuto de Dios", 3, 3),
                 ("Álamos", 3, 3), ("Garcés Navas", 3, 3), ("Bolivia", 3, 3), ("Villas de Granada", 3, 3)]},
    {"codigo": 11, "nombre": "Suba", "lat": 4.745, "lon": -74.085,
     "estratos": {1: .01, 2: .30, 3: .33, 4: .18, 5: .12, 6: .06},
     "calles": (100, 170, ""), "carreras": (50, 150, ""),
     "barrios": [("Niza", 5, 5), ("Colina Campestre", 5, 6), ("Suba Centro", 3, 3), ("Tibabuyes", 2, 2),
                 ("El Rincón", 1, 2), ("Pontevedra", 5, 5), ("Prado Veraniego", 4, 4), ("Mazurén", 4, 4),
                 ("San José de Bavaria", 5, 6), ("Britalia", 3, 4)]},
    {"codigo": 12, "nombre": "Barrios Unidos", "lat": 4.668, "lon": -74.075,
     "estratos": {3: .45, 4: .45, 5: .10},
     "calles": (63, 100, ""), "carreras": (14, 60, ""),
     "barrios": [("Siete de Agosto", 3, 3), ("Polo Club", 4, 5), ("Rionegro", 4, 4), ("Doce de Octubre", 3, 3),
                 ("Los Andes", 4, 5), ("La Castellana", 5, 5)]},
    {"codigo": 13, "nombre": "Teusaquillo", "lat": 4.640, "lon": -74.090,
     "estratos": {3: .10, 4: .85, 5: .05},
     "calles": (26, 63, ""), "carreras": (14, 60, ""),
     "barrios": [("Galerías", 4, 4), ("Palermo", 4, 4), ("La Soledad", 4, 4), ("Teusaquillo", 4, 4),
                 ("Ciudad Salitre Oriental", 4, 4), ("Pablo VI", 4, 4), ("Quinta Paredes", 3, 4)]},
    {"codigo": 14, "nombre": "Los Mártires", "lat": 4.605, "lon": -74.090,
     "estratos": {2: .10, 3: .88, 4: .02},
     "calles": (1, 26, ""), "carreras": (14, 30, ""),
     "barrios": [("Santa Isabel", 3, 3), ("Ricaurte", 3, 3), ("La Estanzuela", 3, 3), ("Voto Nacional", 2, 3),
                 ("Eduardo Santos", 3, 3)]},
    {"codigo": 15, "nombre": "Antonio Nariño", "lat": 4.585, "lon": -74.100,
     "estratos": {2: .10, 3: .90},
     "calles": (1, 31, " Sur"), "carreras": (10, 30, ""),
     "barrios": [("Restrepo", 3, 3), ("Ciudad Jardín Sur", 3, 3), ("Santander", 3, 3), ("La Fragua", 3, 3)]},
    {"codigo": 16, "nombre": "Puente Aranda", "lat": 4.615, "lon": -74.115,
     "estratos": {2: .02, 3: .98},
     "calles": (1, 26, ""), "carreras": (30, 68, ""),
     "barrios": [("Ciudad Montes", 3, 3), ("Galán", 3, 3), ("Alcalá", 3, 3), ("Muzú", 3, 3),
                 ("Pensilvania", 3, 3)]},
    {"codigo": 17, "nombre": "La Candelaria", "lat": 4.597, "lon": -74.072,
     "estratos": {2: .40, 3: .55, 4: .05},
     "calles": (6, 20, ""), "carreras": (1, 10, ""),
     "barrios": [("La Concordia", 2, 3), ("Egipto", 2, 2), ("Centro Administrativo", 3, 4), ("Belén", 2, 2)]},
    {"codigo": 18, "nombre": "Rafael Uribe Uribe", "lat": 4.565, "lon": -74.115,
     "estratos": {1: .12, 2: .55, 3: .33},
     "calles": (22, 60, " Sur"), "carreras": (1, 30, ""),
     "barrios": [("Quiroga", 3, 3), ("Marco Fidel Suárez", 2, 2), ("Diana Turbay", 1, 2), ("Olaya", 3, 3),
                 ("Molinos", 2, 2), ("San Jorge", 2, 2)]},
    {"codigo": 19, "nombre": "Ciudad Bolívar", "lat": 4.545, "lon": -74.150,
     "estratos": {1: .60, 2: .38, 3: .02},
     "calles": (60, 90, " Sur"), "carreras": (18, 80, ""),
     "barrios": [("Lucero", 1, 2), ("Arborizadora", 2, 2), ("Ismael Perdomo", 2, 2), ("Jerusalén", 1, 1),
                 ("Candelaria La Nueva", 2, 2), ("Madelena", 2, 3)]},
]

# Municipios de Sabana Centro (código DIVIPOLA = el mismo del ICFES)
MUNICIPIOS = [
    {"codigo": 25175, "nombre": "Chía", "lat": 4.861, "lon": -74.058,
     "barrios": ["Centro", "Samaria", "Bojacá", "Fagua", "Fonquetá", "La Balsa"]},
    {"codigo": 25126, "nombre": "Cajicá", "lat": 4.918, "lon": -74.028,
     "barrios": ["Centro", "Capellanía", "Granjitas", "Rincón Santo", "Calahorra"]},
    {"codigo": 25214, "nombre": "Cota", "lat": 4.809, "lon": -74.103,
     "barrios": ["Centro", "Siberia", "Parcelas", "Rozo"]},
    {"codigo": 25899, "nombre": "Zipaquirá", "lat": 5.022, "lon": -74.004,
     "barrios": ["Centro", "San Pablo", "Algarra", "Barandillas", "La Esmeralda"]},
    {"codigo": 25758, "nombre": "Sopó", "lat": 4.908, "lon": -73.938,
     "barrios": ["Centro", "La Diana", "Pueblo Viejo"]},
    {"codigo": 25817, "nombre": "Tocancipá", "lat": 4.965, "lon": -73.913,
     "barrios": ["Centro", "La Esmeralda", "Verganzo"]},
    {"codigo": 25799, "nombre": "Tenjo", "lat": 4.872, "lon": -74.144,
     "barrios": ["Centro", "La Punta", "Chacal"]},
    {"codigo": 25785, "nombre": "Tabio", "lat": 4.916, "lon": -74.096,
     "barrios": ["Centro", "Río Frío", "El Salitre"]},
    {"codigo": 25200, "nombre": "Cogua", "lat": 5.061, "lon": -73.979,
     "barrios": ["Centro", "Rodamontal"]},
    {"codigo": 25295, "nombre": "Gachancipá", "lat": 4.991, "lon": -73.873,
     "barrios": ["Centro", "San Bartolomé"]},
    {"codigo": 25486, "nombre": "Nemocón", "lat": 5.067, "lon": -73.879,
     "barrios": ["Centro", "Patio Bonito"]},
]

# EPS vigentes en Bogotá por régimen (Listado MinSalud de EPS por régimen, 2025). Pesos: supuesto S-20.
EPS = [
    {"nombre": "COMPENSAR EPS", "regimen": "CONTRIBUTIVO", "peso": 0.22},
    {"nombre": "EPS SANITAS", "regimen": "CONTRIBUTIVO", "peso": 0.20},
    {"nombre": "FAMISANAR EPS", "regimen": "CONTRIBUTIVO", "peso": 0.14},
    {"nombre": "NUEVA EPS", "regimen": "CONTRIBUTIVO", "peso": 0.14},
    {"nombre": "SALUD TOTAL EPS", "regimen": "CONTRIBUTIVO", "peso": 0.12},
    {"nombre": "EPS SURA", "regimen": "CONTRIBUTIVO", "peso": 0.13},
    {"nombre": "ALIANSALUD EPS", "regimen": "CONTRIBUTIVO", "peso": 0.05},
    {"nombre": "CAPITAL SALUD EPS-S", "regimen": "SUBSIDIADO", "peso": 0.70},
    {"nombre": "NUEVA EPS", "regimen": "SUBSIDIADO", "peso": 0.30},
    {"nombre": "SANIDAD MILITAR / POLICIAL / MAGISTERIO", "regimen": "ESPECIAL", "peso": 1.00},
]
# Probabilidad de régimen subsidiado según estrato (supuesto S-20)
PROB_SUBSIDIADO = {1: 0.55, 2: 0.35, 3: 0.12, 4: 0.04, 5: 0.02, 6: 0.01}
PROB_REGIMEN_ESPECIAL = 0.03

CANALES = {
    "EXPOESTUDIANTES": "Feria ExpoEstudiantes",
    "SITIO_WEB": "Sitio web / formulario de preinscripción",
    "REDES_SOCIALES": "Redes sociales (pauta y contenido)",
    "REFERIDO": "Referido por estudiante o egresado",
    "CAMPUS_DAY": "Campus Day / Familia Fest",
    "LLAMADA_WHATSAPP": "Llamada o WhatsApp de asesor",
    "INMERSION": "Programa de inmersión universitaria",
    "COLEGIO_CONVENIO": "Colegio en convenio",
}

TIPOS_DOCUMENTO = {"TI": "Tarjeta de Identidad", "CC": "Cédula de Ciudadanía", "CE": "Cédula de Extranjería",
                   "PPT": "Permiso por Protección Temporal", "PEP": "Permiso Especial de Permanencia (vencido)"}

ESTADOS_CIVILES = {"SOLTERO": "Soltero/a", "CASADO": "Casado/a", "UNION_LIBRE": "Unión libre"}

DOCUMENTOS_SOPORTE = {
    "DOC_IDENTIDAD": "Fotocopia del documento de identidad",
    "ACTA_GRADO": "Fotocopia del acta de grado de bachiller",
    "DIPLOMA": "Fotocopia del diploma de bachiller",
    "RESULTADO_ICFES": "Fotocopia de los resultados Saber 11",
    "CERT_EPS": "Certificado de afiliación a EPS",
}

# Parentesco del contacto de emergencia (supuesto S-08 extendido)
PARENTESCOS = {"MADRE": 0.50, "PADRE": 0.22, "HERMANO/A": 0.10, "ABUELO/A": 0.06, "TIO/A": 0.06, "OTRO": 0.03,
               "CONYUGE/COMPAÑERO/A": 0.03}

# Lugar de nacimiento de aspirantes colombianos (supuesto: mayoría nacidos en Bogotá)
LUGAR_NACIMIENTO_COL = {"Bogotá D.C.": 0.78, "MUNICIPIO_RESIDENCIA": 0.07, "Tunja": 0.02, "Villavicencio": 0.02,
                        "Ibagué": 0.02, "Medellín": 0.015, "Cali": 0.015, "Bucaramanga": 0.015, "Neiva": 0.01,
                        "Girardot": 0.01, "Fusagasugá": 0.01, "Barranquilla": 0.01}
LUGAR_NACIMIENTO_VEN = ["Caracas", "Maracaibo", "Valencia", "Barquisimeto", "San Cristóbal", "Maracay"]

DOMINIO_CORREO = "correo.test"   # dominio reservado (RFC 2606): no corresponde a buzones reales


def distancia_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia en línea recta sobre la esfera terrestre (fórmula de Haversine)."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def distancias_campus(lat, lon) -> tuple[np.ndarray, np.ndarray]:
    """Distancia al campus (km) desde una coordenada, en línea recta (Haversine) y por vías estimada (supuesto S-44).

    La distancia por vías se estima como la suma del tramo norte-sur y del tramo oriente-occidente (distancia "de
    cuadra" o Manhattan): en Bogotá las calles corren de oriente a occidente y las carreras de norte a sur, y el campus
    queda al norte. No hay un estudio colombiano del factor de rodeo, por eso no se usa un factor de otro país.
    """
    cfg = cargar_config()["campus"]
    lat, lon = np.asarray(lat, dtype=float), np.asarray(lon, dtype=float)
    r = 6371.0
    p1, p2 = np.radians(lat), math.radians(cfg["lat"])
    dp, dl = p2 - p1, np.radians(cfg["lon"] - lon)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * math.cos(p2) * np.sin(dl / 2) ** 2
    recta = 2 * r * np.arcsin(np.sqrt(a))
    norte_sur = r * np.abs(dp)
    oriente_occidente = r * np.abs(dl) * np.cos((p1 + p2) / 2)
    return recta, norte_sur + oriente_occidente


def direcciones() -> pd.DataFrame:
    """Direcciones REALES con coordenadas para la residencia de los aspirantes (s01b_descargar_direcciones.py).

    Bogotá: placas de Catastro (UAECD) con el estrato de su manzana (SDP) y su barrio catastral.
    Sabana Centro: nivel de direcciones del MGN 2025 (DANE). Se asignan al azar a personas ficticias.
    """
    bog = pd.read_parquet(DATA_RAW / "direcciones_bogota.parquet")
    sab = pd.read_parquet(DATA_RAW / "direcciones_sabana_centro.parquet").assign(estrato=0, barrio=None)
    d = pd.concat([bog, sab[bog.columns]], ignore_index=True)
    recta, vial = distancias_campus(d["lat"], d["lon"])
    return d.assign(distancia_campus_km=recta.round(2), distancia_vial_km=vial.round(2))


def placas_por_localidad_estrato() -> pd.DataFrame:
    """Placas residenciales de TODA Bogotá por localidad y estrato de su manzana (para los pesos de residencia)."""
    return pd.read_csv(DATA_RAW / "direcciones_conteo_bogota.csv")


def poblacion_15_19_localidades(anio: int = 2025) -> dict[int, int]:
    """Población de 15 a 19 años por localidad (Datos Abiertos Bogotá / Observatorio de Salud)."""
    p = pd.read_csv(DATA_RAW / "osb_poblacion_localidad.csv", encoding="utf-8-sig", sep=None, engine="python")
    p.columns = [c.strip().lstrip("﻿") for c in p.columns]
    q = p[(p["ANO"] == anio) & (p["EDAD"].between(15, 19)) & (p["CODIGO_LOCALIDAD"] > 0)]
    return q.groupby("CODIGO_LOCALIDAD")["POBLACION"].sum().astype(int).to_dict()


def tabla_ubicaciones() -> pd.DataFrame:
    """Catálogo único de ubicaciones con distancia al campus."""
    cfg = cargar_config()["campus"]
    pob = poblacion_15_19_localidades()
    filas = []
    for loc in LOCALIDADES:
        filas.append({"ubicacion_id": loc["codigo"], "nombre": loc["nombre"], "tipo": "LOCALIDAD",
                      "municipio": "Bogotá D.C.", "departamento": "BOGOTÁ D.C.", "cod_divipola": 11001,
                      "lat": loc["lat"], "lon": loc["lon"],
                      "poblacion_15_19": pob.get(loc["codigo"])})
    for m in MUNICIPIOS:
        filas.append({"ubicacion_id": m["codigo"], "nombre": m["nombre"], "tipo": "MUNICIPIO",
                      "municipio": m["nombre"], "departamento": "CUNDINAMARCA", "cod_divipola": m["codigo"],
                      "lat": m["lat"], "lon": m["lon"],
                      "poblacion_15_19": None})
    df = pd.DataFrame(filas)
    df["distancia_campus_km"] = [round(distancia_km(r.lat, r.lon, cfg["lat"], cfg["lon"]), 1) for r in df.itertuples()]
    return df
