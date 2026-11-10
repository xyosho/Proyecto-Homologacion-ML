"""PASO 1b — Descargar direcciones REALES con coordenadas (datos abiertos colombianos).

¿Por qué? Antes la distancia al campus se medía desde el centro de la localidad o del municipio (28 valores
distintos). Con una dirección por aspirante, la distancia se calcula desde su casa.

Fuentes (todas colombianas y abiertas):
  - Bogotá: Placa Domiciliaria (Catastro Bogotá, UAECD): cada placa con su dirección y coordenada.
            Estratificación por manzana (Secretaría Distrital de Planeación): estrato de la manzana de cada placa.
            Localidades (SDP) y sectores catastrales (UAECD): localidad y nombre del barrio catastral.
  - Sabana Centro: Nivel de direcciones del Marco Geoestadístico Nacional 2025 (DANE), por municipio.

Salidas (pequeñas, se versionan; los archivos grandes quedan en data/raw/cache_geo/, que no se versiona):
  data/raw/direcciones_bogota.parquet          muestra de hasta 2.000 placas por localidad y estrato
  data/raw/direcciones_conteo_bogota.csv       placas por localidad y estrato en TODA la ciudad (pesos de Bayes)
  data/raw/direcciones_sabana_centro.parquet   muestra de hasta 1.500 direcciones por municipio
  data/raw/direcciones_metadatos.json          fuentes, fechas y conteos

Nota ética: las direcciones existen (son viviendas reales), pero se asignan AL AZAR a personas ficticias; ninguna
dirección corresponde a la persona sintética que la recibe. Por ser un dato personal, la dirección y su coordenada
quedan solo en formulario_admision (cerrada por RLS); la tabla plana solo trae las distancias.

Uso:  python src/s01b_descargar_direcciones.py   (usa la caché si ya existe)
"""
from __future__ import annotations

import json
import re
import sqlite3
import zipfile
from datetime import datetime

import numpy as np
import pandas as pd
import requests
from matplotlib.path import Path as Ruta

import catalogos as cat
from comun import DATA_RAW, asegurar_carpetas

CACHE = DATA_RAW / "cache_geo"
FUENTES = {
    "placas": ("https://datosabiertos.bogota.gov.co/dataset/d4a31443-789c-478a-9db2-ff967e1d9a50/resource/"
               "12e0fd4d-33b6-4beb-b9df-5b7e1adc5b40/download/pdom.geojson.09.26", "placa_domiciliaria.geojson"),
    "estratos": ("https://datosabiertos.bogota.gov.co/dataset/55467552-0af4-4524-a390-a2956035744e/resource/"
                 "cde22374-35e8-4c7d-abf9-903cd82faa42/download/manzanaestratificacion.gpkg", "estratificacion_manzana.gpkg"),
    "localidades": ("https://datosabiertos.bogota.gov.co/dataset/856cb657-8ca3-4ee8-857f-37211173b1f8/resource/"
                    "497b8756-0927-4aee-8da9-ca4e32ca3a8a/download/loca.json", "localidades.geojson"),
    "sectores": ("https://serviciosgis.catastrobogota.gov.co/arcgis/rest/services/catastro/sectorcatastral/MapServer/0/"
                 "query?where=1%3D1&outFields=SCACODIGO,SCANOMBRE&returnGeometry=false&f=json", "sectores.json"),
}
DANE = ("https://geoportal.dane.gov.co/mparcgis/rest/services/NIVEL_DE_DIRECCIONES/Serv_NivelDirecciones_2025/"
        "MapServer/325/query")
MUESTRA_BOGOTA, MUESTRA_MUNICIPIO, SEMILLA = 2000, 1500, 20261023

# Formato de las direcciones: solo placas principales con nomenclatura estándar (se descartan mejoras, interiores…)
VIA = re.compile(r"^(CL|KR|DG|TV|AC|AK) (\d+)([A-Z]?)(BIS)? ?([A-Z])?$")
PLACA = re.compile(r"^(\d+)([A-Z]?)( BIS)?( [A-Z])? (\d+)$")
TIPOS = {"CL": "Calle", "KR": "Carrera", "DG": "Diagonal", "TV": "Transversal", "AC": "Avenida Calle",
         "AK": "Avenida Carrera"}
SUFIJOS = {"S": "Sur", "SUR": "Sur", "E": "Este", "ESTE": "Este"}


def _sin_sufijo(texto: str) -> tuple[str, str]:
    """'CL 43 S' -> ('CL 43', ' Sur'): el sufijo Sur/Este va al final de la vía o de la placa."""
    partes = str(texto).strip().split()
    if len(partes) > 2 and partes[-1] in SUFIJOS:
        return " ".join(partes[:-1]), " " + SUFIJOS[partes[-1]]
    return " ".join(partes), ""


def formatear(via: str, placa: str) -> str | None:
    """'KR 69B' + '37A 35 S'  ->  'Carrera 69B # 37A-35 Sur'. Devuelve None si no es una placa estándar."""
    (via, suf_v), (placa, suf_p) = _sin_sufijo(via), _sin_sufijo(placa)
    v, p = VIA.match(via.replace(" BIS", "BIS")), PLACA.match(placa)
    if not v or not p:
        return None
    tipo, num, letra, bis, letra2 = v.groups()
    cruce, letra_c, bis_c, letra_c2, numero = p.groups()
    nombre_via = f"{TIPOS[tipo]} {num}{letra}{' Bis' if bis else ''}{(' ' + letra2) if letra2 else ''}{suf_v}"
    cruce_txt = f"{cruce}{letra_c}{' Bis' if bis_c else ''}{(' ' + letra_c2.strip()) if letra_c2 else ''}"
    return f"{nombre_via} # {cruce_txt}-{numero}{suf_p}"


def formatear_dane(texto: str) -> str | None:
    """Dirección normalizada del DANE en una sola cadena ('KR 4 6 72', 'CL 9 BIS A 7 65 SUR') -> mismo formato."""
    t = str(texto).strip().upper().split()
    sufijo = [t.pop()] if len(t) > 3 and t[-1] in SUFIJOS else []
    if len(t) < 4 or t[0] not in TIPOS or not t[-1].isdigit():
        return None
    resto, i = t[1:-1], 1                     # resto = vía + cruce; el cruce empieza en el siguiente token con dígito
    while i < len(resto) and not resto[i][0].isdigit():
        i += 1
    via, cruce = resto[:i], resto[i:]
    if not cruce:
        return None
    via_txt = " ".join(via).replace(" BIS", "BIS")
    return formatear(f"{t[0]} {via_txt}", " ".join(cruce + [t[-1]] + sufijo))


def descargar(nombre: str) -> None:
    url, archivo = FUENTES[nombre]
    destino = CACHE / archivo
    if destino.exists():
        return
    print(f"  descargando {archivo} …")
    r = requests.get(url, timeout=900)
    r.raise_for_status()
    destino.write_bytes(r.content)


def placas_bogota() -> pd.DataFrame:
    """Todas las placas principales con estrato de manzana, localidad y barrio catastral."""
    filas = []
    with zipfile.ZipFile(CACHE / FUENTES["placas"][1]).open("PDOM.geojson") as f:
        for linea in f:                                   # una placa por línea: se lee sin cargar 500 MB en memoria
            if not linea.startswith(b'{ "type": "Feature"'):
                continue
            x = json.loads(linea.rstrip(b",\r\n"))
            p, c = x["properties"], x["geometry"]["coordinates"]
            if p["PDOTIPO"] == 1:                         # placa principal del predio
                filas.append((p["PDOCODIGO"], p["PDONVIAL"], p["PDOTEXTO"], p["PDOCLOTE"], c[0], c[1]))
    pl = pd.DataFrame(filas, columns=["codigo_fuente", "via", "placa", "lote", "lon", "lat"])
    con = sqlite3.connect(CACHE / FUENTES["estratos"][1])
    est = pd.read_sql("SELECT CODIGO_MANZANA AS manzana, ESTRATO AS estrato FROM ManzanaEstratificacion", con)
    con.close()
    pl["manzana"] = pl["lote"].str[:8]
    pl = pl.merge(est.drop_duplicates("manzana"), on="manzana", how="inner")
    pl = pl[pl["estrato"].between(1, 6)].copy()      # 0 = manzana sin uso residencial
    loc = json.loads((CACHE / FUENTES["localidades"][1]).read_text(encoding="utf-8"))
    pl["localidad"] = 0
    puntos = pl[["lon", "lat"]].to_numpy()
    for feat in loc["features"]:
        dentro = np.zeros(len(pl), bool)
        for anillo in feat["geometry"]["rings"]:          # regla par-impar: los huecos se restan
            dentro ^= Ruta(np.array(anillo)).contains_points(puntos)
        pl.loc[dentro, "localidad"] = int(feat["attributes"]["LocCodigo"])
    sect = json.loads((CACHE / FUENTES["sectores"][1]).read_text(encoding="utf-8"))
    nombres = {s["attributes"]["SCACODIGO"]: s["attributes"]["SCANOMBRE"].title() for s in sect["features"]}
    pl["barrio"] = pl["lote"].str[:6].map(nombres)
    pl["direccion"] = [formatear(v, p) for v, p in zip(pl["via"], pl["placa"])]
    validas = pl["direccion"].notna() & pl["barrio"].notna() & pl["localidad"].isin([l["codigo"] for l in cat.LOCALIDADES])
    validas &= ~pl["codigo_fuente"].duplicated(keep=False)      # el Catastro repite algunos códigos de placa: se descartan
    print(f"  placas principales en manzanas residenciales: {len(pl):,}; con formato estándar, barrio y localidad: "
          f"{validas.sum():,}")
    return pl[validas]


def direcciones_dane(municipio: int) -> pd.DataFrame:
    """Nivel de direcciones del MGN (DANE) para un municipio, en páginas de 2.000 ordenadas por OBJECTID."""
    cache = CACHE / f"dane_{municipio}.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    filas, ultimo = [], 0
    while True:
        r = requests.get(DANE, params={"where": f"MPIO_CDPMP='{municipio}' AND OBJECTID>{ultimo}",
                                       "outFields": "OBJECTID,CLAS_CCDGO,MANZ_CCNCT,LONG_PLACA,LATI_PLACA,DIR_NORMSC",
                                       "orderByFields": "OBJECTID", "returnGeometry": "false", "f": "json"}, timeout=120)
        r.raise_for_status()
        pagina = [f["attributes"] for f in r.json().get("features", [])]
        if not pagina:
            break
        filas += pagina
        ultimo = pagina[-1]["OBJECTID"]
    d = pd.DataFrame(filas)
    d["direccion"] = d["DIR_NORMSC"].map(formatear_dane)
    d = d[d["direccion"].notna() & d["LONG_PLACA"].notna()]
    d = pd.DataFrame({"codigo_fuente": "DANE-" + d["OBJECTID"].astype(str), "ubicacion_id": municipio,
                      "zona": np.where(d["CLAS_CCDGO"] == "1", "CABECERA", "RESTO"), "direccion": d["direccion"],
                      "lon": d["LONG_PLACA"].astype(float), "lat": d["LATI_PLACA"].astype(float)})
    d.to_parquet(cache, index=False)
    return d


def main() -> None:
    asegurar_carpetas()
    CACHE.mkdir(parents=True, exist_ok=True)
    print("Bogotá: Catastro (placas) + SDP (estrato de la manzana, localidades)")
    for nombre in FUENTES:
        descargar(nombre)
    pl = placas_bogota()
    conteo = pl.groupby(["localidad", "estrato"]).size().rename("placas").reset_index()
    conteo.to_csv(DATA_RAW / "direcciones_conteo_bogota.csv", index=False)
    muestra = pl.sample(frac=1, random_state=SEMILLA).groupby(["localidad", "estrato"]).head(MUESTRA_BOGOTA)
    bog = muestra.rename(columns={"localidad": "ubicacion_id"})[
        ["codigo_fuente", "ubicacion_id", "estrato", "barrio", "direccion", "lon", "lat"]].reset_index(drop=True)
    bog.to_parquet(DATA_RAW / "direcciones_bogota.parquet", index=False)
    print(f"  muestra: {len(bog):,} placas en {conteo.shape[0]} celdas localidad × estrato")

    print("Sabana Centro: nivel de direcciones del MGN 2025 (DANE)")
    partes = []
    for m in cat.MUNICIPIOS:
        d = direcciones_dane(m["codigo"])
        partes.append(d.sample(min(len(d), MUESTRA_MUNICIPIO), random_state=SEMILLA))
        print(f"  {m['nombre']}: {len(d):,} direcciones con formato estándar")
    sab = pd.concat(partes, ignore_index=True)
    sab.to_parquet(DATA_RAW / "direcciones_sabana_centro.parquet", index=False)

    meta = {"descargado": datetime.now().isoformat(timespec="seconds"), "semilla_muestra": SEMILLA,
            "fuentes": {k: v[0] for k, v in FUENTES.items()} | {"dane_mgn_direcciones_2025": DANE},
            "licencias": "Datos Abiertos Bogotá: CC BY 4.0. DANE: información pública del MGN.",
            "bogota": {"placas_validas": int(len(pl)), "muestra": int(len(bog)), "celdas": int(conteo.shape[0])},
            "sabana_centro": {"muestra": int(len(sab)), "por_municipio": sab["ubicacion_id"].value_counts().to_dict()}}
    (DATA_RAW / "direcciones_metadatos.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2, default=str),
                                                         encoding="utf-8")
    print("Listo: data/raw/direcciones_*.parquet")


if __name__ == "__main__":
    main()
