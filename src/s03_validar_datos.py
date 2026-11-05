"""PASO 3 — Validar los datos sintéticos en TRES capas (criterios fijados antes en el YAML).

CAPA 1  Integridad y reglas de negocio: ¿cada fila cumple las reglas de Unicervantes y del
        formulario? (rangos, fórmula ICFES, documento vs edad, becas, valores en pesos...)
CAPA 2  Trazabilidad con datos reales: cada dirección del formulario debe ser IDÉNTICA a una placa de Catastro
        Bogotá o a una dirección del DANE (coordenada, localidad y estrato de manzana). Cada resultado Saber 11 debe
        ser IDÉNTICO a un registro real y
        distinto del ICFES (kgxf-xxbe): mismas 5 pruebas, global, colegio, estrato y género; ningún
        registro repetido. Además se describe (sin criterio) qué tan distintos son los leads de la zona:
        la diferencia es intencional (perfil de la universidad, supuesto S-05).
CAPA 3  Plausibilidad: anclas institucionales, relaciones monótonas esperadas, relación imperfecta entre
        el ICFES y las notas simuladas del colegio, y RECUPERACIÓN de los parámetros verdaderos de los
        modelos de matrícula y de conversión (regresión logística).

Uso:  python src/s03_validar_datos.py   -> reports/validacion_semana1.md (+ figuras y JSON)
"""
from __future__ import annotations

import json
from datetime import date

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

import catalogos as cat
import reglas_negocio as rn
from comun import DATA_PROCESSED, FIGURAS, REPORTS, asegurar_carpetas, cargar_config

SIN = DATA_PROCESSED / "sintetico"
OCULTO = DATA_PROCESSED / "oculto"
AREAS = ["punt_lectura_critica", "punt_matematicas", "punt_sociales_ciudadanas", "punt_c_naturales", "punt_ingles"]


def cargar() -> dict[str, pd.DataFrame]:
    nombres = ["aspirante", "formulario_admision", "contacto_emergencia", "resultado_saber11", "historial_bachillerato",
               "nota_bachillerato", "colegio", "inscripcion", "evaluacion_beca", "documento_soporte",
               "seguimiento_academico", "asesor", "interaccion", "evento_captacion", "inversion_captacion",
               "icfes_zona_referencia"]
    return {n: pd.read_parquet(SIN / f"{n}.parquet") for n in nombres}


# =============================================================================
# CAPA 1 — Integridad y reglas de negocio (bloques 1, 2 y 5 + seguimiento)
# =============================================================================
def capa1(t: dict[str, pd.DataFrame]) -> pd.DataFrame:
    a, f, r, h, i = t["aspirante"], t["formulario_admision"], t["resultado_saber11"], t["historial_bachillerato"], t["inscripcion"]
    s, ce, it, ev, eb = t["seguimiento_academico"], t["contacto_emergencia"], t["interaccion"], t["evento_captacion"], t["evaluacion_beca"]
    inv, col = t["inversion_captacion"], t["colegio"]
    corte = pd.Timestamp(cargar_config()["proyecto"]["fecha_corte"])
    D = pd.to_datetime
    fa = f.merge(a, on="aspirante_id")
    ai = i.merge(a, on="aspirante_id").merge(r, on="aspirante_id").merge(f, on="aspirante_id")
    areas_r = ["punt_lectura_critica", "punt_matematicas", "punt_sociales", "punt_ciencias", "punt_ingles"]
    chk = []

    def regla(bloque, nombre, violaciones, n):
        chk.append({"bloque": bloque, "regla": nombre, "filas_revisadas": int(n), "violaciones": int(violaciones),
                    "cumple": int(violaciones) == 0})

    # ---------------------------------------------------------------- BLOQUE 1
    ventanas = [rn.ventana_campana(p) for p in a["periodo_interes"]]
    ini = D(pd.Series([v[0] for v in ventanas]))
    fin = D(pd.Series([v[1] for v in ventanas])).clip(upper=corte)
    fr = D(a["fecha_registro"])
    regla("1", "Fecha de registro dentro de la campaña del periodo de interés y antes del corte", (~fr.between(ini, fin)).sum(), len(a))
    regla("1", "Edad al registro entre 14 y 70 años", (~a["edad_al_registro"].between(14, 70)).sum(), len(a))
    regla("1", "Programa de interés ofertado en el periodo (AD ≥ 2024-1, SSIA ≥ 2026-2)",
          (~pd.Series([rn.programa_disponible(p, per) for p, per in zip(a["programa_interes"], a["periodo_interes"])])).sum(), len(a))
    ae = a.dropna(subset=["evento_id"]).merge(ev, on="evento_id", suffixes=("", "_ev"))
    regla("1", "Evento coherente con el canal y la campaña; registro durante el evento",
          ((ae["canal"] != ae["canal_ev"]) | (ae["periodo_interes"] != ae["campana"])
           | ~D(ae["fecha_registro"]).between(D(ae["inicio"]), D(ae["fin"]))).sum(), len(ae))
    regla("1", "Leads de ExpoEstudiantes y Campus Day siempre asociados a un evento",
          (a["canal"].isin(["EXPOESTUDIANTES", "CAMPUS_DAY"]) & a["evento_id"].isna()).sum(), len(a))
    regla("1", "Ningún lead de eventos posteriores a la fecha de corte",
          a["evento_id"].isin(ev.loc[D(ev["inicio"]) > corte, "evento_id"]).sum(), len(a))
    conv = a.merge(col[["colegio_cod_dane", "en_convenio"]], on="colegio_cod_dane")
    regla("1", "Canal 'colegio en convenio' solo si el colegio tiene convenio",
          ((conv["canal"] == "COLEGIO_CONVENIO") & ~conv["en_convenio"]).sum(), len(a))
    regla("1", "Celular: 10 dígitos que inician en 3", (~a["celular"].map(rn.celular_valido)).sum(), len(a))
    regla("1", "Correo único con dominio reservado .test (RFC 2606)",
          (~a["correo"].map(rn.correo_valido)).sum() + a["correo"].duplicated().sum(), len(a))
    regla("1", "Estrato entre 1 y 6", (~a["estrato"].between(1, 6)).sum(), len(a))
    regla("1", "Solo los inscritos tienen formulario de admisión y contacto de emergencia",
          len(set(f["aspirante_id"]) ^ set(i["aspirante_id"])) + len(set(ce["aspirante_id"]) ^ set(i["aspirante_id"])), len(a))
    edad_calc = [rn.edad_en(fn, fi) for fn, fi in zip(ai["fecha_nacimiento"], ai["fecha_inscripcion"])]
    regla("1", "Edad = edad cumplida en la fecha de inscripción", (np.array(edad_calc) != ai["edad_al_inscribirse"]).sum(), len(ai))
    regla("1", "Edad al inscribirse ≥ edad al registro", (ai["edad_al_inscribirse"] < ai["edad_al_registro"]).sum(), len(ai))
    regla("1", "Orden de fechas: nacimiento < examen Saber 11 < inscripción",
          ((D(ai["fecha_nacimiento"]).dt.year >= ai["anio_examen"])
           | (ai["anio_examen"] > D(ai["fecha_inscripcion"]).dt.year)).sum(), len(ai))
    regla("1", "Tipo de documento coherente con edad y nacionalidad (T.I. <18, C.C. ≥18)",
          (~pd.Series([rn.documento_coherente(tp, e, n) for tp, e, n in
                       zip(f["tipo_documento"], f["edad_al_inscribirse"], f["nacionalidad"])])).sum(), len(f))
    regla("1", "Ningún PEP (vencido desde 28-feb-2023)", (f["tipo_documento"] == "PEP").sum(), len(f))
    regla("1", "Documento único por tipo", f.duplicated(["tipo_documento", "numero_documento"]).sum(), len(f))
    regla("1", "Teléfono fijo: 601 + 7 dígitos (o vacío)",
          (~f["telefono_fijo"].map(lambda x: rn.fijo_valido(None if pd.isna(x) else x))).sum(), len(f))
    regla("1", "Dirección con nomenclatura válida", (~f["direccion"].map(rn.direccion_valida)).sum(), len(f))
    regla("1", "Estado civil: menores de 18 solteros (Ley 2447 de 2025)",
          (~pd.Series([rn.estado_civil_coherente(ec, e) for ec, e in zip(f["estado_civil"], f["edad_al_inscribirse"])])).sum(), len(f))
    dirs = cat.direcciones()
    barrios_validos = set(zip(dirs["ubicacion_id"], dirs["barrio"])) | \
                      {(m["codigo"], b) for m in cat.MUNICIPIOS for b in m["barrios"]}
    regla("1", "Barrio pertenece a la localidad/municipio de residencia (Bogotá: sector catastral de la placa)",
          (~pd.Series(list(zip(fa["ubicacion_id"], fa["barrio"]))).isin(barrios_validos)).sum(), len(fa))
    regla("1", "Una vivienda (placa) por aspirante: ningún código de dirección repetido",
          f["codigo_direccion"].duplicated().sum(), len(f))
    regla("1", "Distancia por vías ≥ distancia en línea recta (S-44)",
          (f["distancia_vial_km"] < f["distancia_campus_km"]).sum(), len(f))
    cs = ce.merge(f[["aspirante_id", "estado_civil"]], on="aspirante_id")
    regla("1", "Contacto cónyuge solo si el aspirante no es soltero",
          ((cs["parentesco"] == "CONYUGE/COMPAÑERO/A") & (cs["estado_civil"] == "SOLTERO")).sum(), len(ce))

    # ---------------------------------------------------------------- BLOQUE 2
    regla("2", "Puntajes por prueba entre 0 y 100", (~r[areas_r].apply(lambda c: c.between(0, 100))).any(axis=1).sum(), len(r))
    regla("2", "Puntaje global entre 0 y 500", (~r["punt_global"].between(0, 500)).sum(), len(r))
    regla("2", "Puntaje global = fórmula ICFES 5·(3LC+3MAT+3SC+3CN+ING)/13",
          (r.apply(lambda x: rn.puntaje_global(*[x[c] for c in areas_r]), axis=1) != r["punt_global"]).sum(), len(r))
    regla("2", "Todo inscrito tiene resultado Saber 11 y promedio acumulado del colegio",
          (~i["aspirante_id"].isin(r["aspirante_id"]) | ~i["aspirante_id"].isin(h["aspirante_id"])).sum(), len(i))
    regla("2", "Promedio acumulado del colegio entre 3.0 y 5.0 (bachiller graduado)",
          (~h["promedio_acumulado_colegio"].between(3.0, 5.0)).sum(), len(h))
    regla("2", "Desempeño del promedio coherente con la escala (Decreto 1290 de 2009)",
          (h["desempeno_nacional"] != h["promedio_acumulado_colegio"].map(rn.desempeno_bachillerato)).sum(), len(h))
    nb = t["nota_bachillerato"]
    por_asp = nb.groupby("aspirante_id")
    completo = por_asp.size().reindex(h["aspirante_id"], fill_value=0)
    regla("2", "10 notas por aspirante (grados 10 y 11 × 5 áreas), sin repetir grado y área",
          (completo != 10).sum() + nb.duplicated(["aspirante_id", "grado", "area"]).sum(), len(h))
    regla("2", "Notas finales por área entre 3.0 y 5.0 (área aprobada)", (~nb["nota"].between(3.0, 5.0)).sum(), len(nb))
    media_notas = por_asp["nota"].mean().reindex(h["aspirante_id"]).to_numpy()
    regla("2", "Promedio acumulado del colegio = media de sus 10 notas",
          (np.abs(media_notas - h["promedio_acumulado_colegio"].to_numpy()) > 0.006).sum(), len(h))
    regla("2", "Desempeño de cada nota coherente con la escala (Decreto 1290 de 2009)",
          (nb["desempeno_nacional"] != nb["nota"].map(rn.desempeno_bachillerato)).sum(), len(nb))
    g11 = nb[nb["grado"] == 11].merge(r[["aspirante_id", "anio_examen"]], on="aspirante_id")
    g10 = nb[nb["grado"] == 10].set_index(["aspirante_id", "area"])["anio_lectivo"]
    regla("2", "Año lectivo del grado 11 = año del Saber 11; grado 10 un año antes",
          (g11["anio_lectivo"] != g11["anio_examen"]).sum()
          + (g10 != g11.set_index(["aspirante_id", "area"])["anio_lectivo"].reindex(g10.index) - 1).sum(), len(nb))
    regla("2", "Inscripción en el programa y periodo de interés del lead",
          ((ai["programa"] != ai["programa_interes"]) | (ai["periodo"] != ai["periodo_interes"])).sum(), len(ai))
    fm = D(ai["fecha_matricula"])
    regla("2", "Orden del embudo: registro ≤ inscripción < matrícula",
          ((D(ai["fecha_registro"]) > D(ai["fecha_inscripcion"])) | (fm.notna() & (fm <= D(ai["fecha_inscripcion"])))).sum(), len(ai))
    regla("2", "Programa ofertado en el periodo de ingreso",
          (~pd.Series([rn.programa_disponible(p, per) for p, per in zip(i["programa"], i["periodo"])])).sum(), len(i))
    regla("2", "Evaluación de requisitos de las dos becas para cada inscrito", abs(len(eb) - 2 * len(i)), len(i))
    ebm = eb.merge(ai[["inscripcion_id", "punt_global", "entrevista_realizada", "puntaje_vocacional", "beca"]],
                   on="inscripcion_id", suffixes=("", "_asignada"))
    s11, mv = ebm[ebm["beca"] == "SABER_11"], ebm[ebm["beca"] == "MI_VOCACION"]
    regla("2", "Cumple requisito Saber 11 ⇔ puntaje global ≥ 310",
          (s11["cumple_requisitos"] != s11["punt_global"].map(rn.beca_por_icfes)).sum(), len(s11))
    regla("2", "Cumple requisito Mi Vocación ⇔ entrevista y puntaje vocacional ≥ 3 (S-22)",
          (mv["cumple_requisitos"] != [rn.cumple_mi_vocacion(e, None if pd.isna(p) else p)
                                       for e, p in zip(mv["entrevista_realizada"], mv["puntaje_vocacional"])]).sum(), len(mv))
    asig = ebm[ebm["beca"] == ebm["beca_asignada"]]
    regla("2", "Beca asignada solo a quien cumple sus requisitos", (~asig["cumple_requisitos"]).sum(), len(asig))
    regla("2", "Becas no acumulables: con global ≥ 310 no se asigna Mi Vocación (S-02)",
          ((ai["beca"] == "MI_VOCACION") & (ai["punt_global"] >= 310)).sum(), len(ai))
    regla("2", "Valor de inversión = tarifa oficial del programa en el año",
          (i["valor_semestre_bruto"] != [rn.tarifa(p, rn.anio_periodo(per)) for p, per in zip(i["programa"], i["periodo"])]).sum(), len(i))
    regla("2", "Descuento inicial = % de la beca en el 1er semestre", (i["pct_descuento_inicial"] != [rn.pct_beca(b, 1) for b in i["beca"]]).sum(), len(i))
    regla("2", "Valor neto 1er semestre = bruto × (1 − descuento)",
          (i["valor_neto_primer_semestre"] != [rn.valor_neto(v, d) for v, d in zip(i["valor_semestre_bruto"], i["pct_descuento_inicial"])]).sum(), len(i))
    camp = i["periodo"] == "2027-1"
    regla("2", "Campaña 2027-1 sin resultado de matrícula (censura)", i.loc[camp, "matriculado"].notna().sum(), camp.sum())
    regla("2", "Periodos históricos con resultado de matrícula", i.loc[~camp, "matriculado"].isna().sum(), (~camp).sum())
    regla("2", "No admitido ⇒ no matriculado", ((~i["admitido"]) & (i["matriculado"] == 1)).sum(), len(i))
    es_mat = i["matriculado"] == 1
    regla("2", "Matriculado ⇔ tiene fecha de matrícula, beneficio y modalidad de financiación",
          sum((i[c].notna() != es_mat).sum() for c in ["fecha_matricula", "beneficio", "modalidad_financiacion"]), len(i))
    regla("2", "Entidad financiera solo (y siempre) con crédito educativo",
          (i["entidad_financiera"].notna() != (i["modalidad_financiacion"] == "CREDITO_EDUCATIVO")).sum(), len(i))
    regla("2", "Cambio de residencia solo informado para matriculados", (i["cambio_residencia_por_cercania"].notna() != es_mat).sum(), len(i))
    iu = i.merge(a[["aspirante_id", "ubicacion_id"]], on="aspirante_id")
    fondo_res = iu["ubicacion_id"].map(rn.fondo_municipal)
    regla("2", "Elegible FOES/FOEST ⇔ reside en un municipio con fondo de educación superior",
          (iu["elegible_foes"] != fondo_res.notna()).sum(), len(i))
    regla("2", "El fondo aprobado es el del municipio de residencia",
          (iu["fondo_id"].notna() & (iu["fondo_id"] != fondo_res)).sum(), len(i))

    # ---------------------------------------------------------------- BLOQUE 5
    ia = it.merge(a[["aspirante_id", "fecha_registro", "asesor_id"]], on="aspirante_id", suffixes=("", "_lead"))
    regla("5", "Contactos entre el registro del lead y la fecha de corte",
          (~D(ia["fecha"]).between(D(ia["fecha_registro"]), corte)).sum(), len(it))
    regla("5", "Cada contacto lo hace el asesor asignado al lead", (ia["asesor_id"] != ia["asesor_id_lead"]).sum(), len(it))
    regla("5", "'Confirma inscripción' y 'seguimiento de matrícula' solo en leads inscritos",
          (it["resultado"].isin(["CONFIRMA_INSCRIPCION", "SEGUIMIENTO_MATRICULA"]) & ~it["aspirante_id"].isin(i["aspirante_id"])).sum(), len(it))
    regla("5", "Inversión de captación no negativa y solo en eventos realizados",
          ((inv["valor_cop"] < 0) | inv["evento_id"].isin(ev.loc[D(ev["inicio"]) > corte, "evento_id"])).sum(), len(inv))

    # ------------------------------------------------------ SEGUIMIENTO ACADÉMICO
    si = s.merge(i[["inscripcion_id", "beca", "programa"]], on="inscripcion_id")
    regla("S", "Valor pagado = bruto × (1 − descuento aplicado)",
          (si["valor_pagado"] != [rn.valor_neto(v, d) for v, d in zip(si["valor_bruto"], si["pct_descuento_aplicado"])]).sum(), len(si))
    esperado = [rn.pct_descuento_total(b, k, bool(act) if pd.notna(act) else False)
                for b, k, act in zip(si["beca"], si["semestre_cursado"], si["beca_activa_inicio"])]
    regla("S", "Descuento aplicado sigue la regla (Saber 11 35%→30%; Mi Vocación 30%→20%)",
          (np.round(si["pct_descuento_aplicado"], 4) != np.round(esperado, 4)).sum(), len(si))
    cerr = si.dropna(subset=["promedio_semestre"]).sort_values(["inscripcion_id", "semestre_cursado"])
    regla("S", "Promedios entre 0.0 y 5.0", (~cerr["promedio_semestre"].between(0, 5) | ~cerr["promedio_acumulado"].between(0, 5)).sum(), len(cerr))
    acum = cerr.groupby("inscripcion_id")["promedio_semestre"].transform(lambda x: x.expanding().mean().round(2))
    regla("S", "Promedio acumulado = media de los semestres cursados", (np.abs(acum - cerr["promedio_acumulado"]) > 0.011).sum(), len(cerr))
    evb = cerr.dropna(subset=["conserva_beca"])
    regla("S", "Conserva beca ⇔ promedio acumulado ≥ 4.0 y sin sanción",
          (evb["conserva_beca"] != [rn.conserva_beca(p, sa) for p, sa in zip(evb["promedio_acumulado"], evb["sancion_disciplinaria"])]).sum(), len(evb))
    perdida = si.sort_values(["inscripcion_id", "semestre_cursado"]).groupby("inscripcion_id")["beca_activa_inicio"] \
        .apply(lambda x: any(not a_ and b_ for a_, b_ in zip(x.fillna(True).iloc[:-1], x.fillna(True).iloc[1:])) if len(x) > 1 else False)
    regla("S", "Una beca perdida no se recupera (S-21)", perdida.sum(), len(perdida))
    regla("S", "Semestre en curso (2026-2) sin notas", (si["estado"].eq("EN_CURSO") & si["promedio_semestre"].notna()).sum(), len(si))
    sf = s.merge(i[["inscripcion_id", "fondo_id"]], on="inscripcion_id").sort_values(["inscripcion_id", "semestre_cursado"])
    regla("S", "Apoyo FOES solo con fondo aprobado y nunca mayor al valor pagado",
          ((sf["apoyo_foes_cop"] > 0) & sf["fondo_id"].isna()).sum() + (sf["apoyo_foes_cop"] > sf["valor_pagado"]).sum(), len(sf))
    previo_apoyo = sf.groupby("inscripcion_id")["apoyo_foes_cop"].shift(1)
    previo_prom = sf.groupby("inscripcion_id")["promedio_semestre"].shift(1)
    sin_derecho = (sf["apoyo_foes_cop"] > 0) & (sf["semestre_cursado"] > 1) & \
                  ((previo_apoyo.fillna(0) == 0) | ~previo_prom.map(lambda x: pd.notna(x) and rn.foes_renueva(x)))
    regla("S", "Renovación FOES: exige apoyo previo y promedio del semestre anterior ≥ 3.5 (S-32)", sin_derecho.sum(), len(sf))
    tras = si.sort_values("semestre_cursado").groupby("inscripcion_id")["estado"].apply(lambda x: "DESERTA" in list(x)[:-1])
    regla("S", "Ningún semestre después de la deserción", tras.sum(), len(tras))
    return pd.DataFrame(chk)


# =============================================================================
# CAPA 2 — Trazabilidad con los registros reales del ICFES
# =============================================================================
def tvd(x: pd.Series, y: pd.Series) -> float:
    p, q = x.value_counts(normalize=True), y.value_counts(normalize=True)
    return 0.5 * p.subtract(q, fill_value=0).abs().sum()


def capa2(t: dict[str, pd.DataFrame]) -> dict:
    """Compara cada resultado Saber 11 con el registro real del que salió (llave: registro_icfes)."""
    ref, r, a = t["icfes_zona_referencia"], t["resultado_saber11"], t["aspirante"]
    real = ref.rename(columns={"punt_sociales_ciudadanas": "punt_sociales", "punt_c_naturales": "punt_ciencias"})
    pruebas = ["punt_lectura_critica", "punt_matematicas", "punt_sociales", "punt_ciencias", "punt_ingles", "punt_global"]
    cruce = (r.merge(a[["aspirante_id", "colegio_cod_dane", "estrato", "genero"]], on="aspirante_id")
              .merge(real, left_on="registro_icfes", right_on="estu_consecutivo", how="left", suffixes=("", "_real"),
                     indicator=True))
    encontrado = cruce["_merge"] == "both"
    iguales = np.logical_and.reduce([cruce[c] == cruce[f"{c}_real"] for c in pruebas]) & encontrado
    contexto = ((cruce["colegio_cod_dane"] == cruce["cole_cod_dane_establecimiento"]) & (cruce["estrato"] == cruce["estrato_real"])
                & (cruce["genero"] == cruce["estu_genero"]) & (cruce["periodo_icfes_origen"] == cruce["periodo_icfes"]) & encontrado)
    res = {"n_resultados": len(r), "n_registros_zona": len(ref),
           "registros_encontrados": float(encontrado.mean()), "puntajes_identicos": float(iguales.mean()),
           "contexto_identico": float(contexto.mean()), "registros_repetidos": int(r["registro_icfes"].duplicated().sum()),
           "periodos_origen": r["periodo_icfes_origen"].value_counts().to_dict()}
    # Representatividad (informativa): los leads NO deben ser idénticos a la zona (perfil S-05)
    leads = ref[ref["estu_consecutivo"].isin(r["registro_icfes"])]
    res["representatividad"] = {
        "media_global": {"zona": float(ref["punt_global"].mean()), "leads_con_resultado": float(r["punt_global"].mean()),
                         "referencia_publicada_bogota_2022": 273},
        "pct_global_310_o_mas": {"zona": float((ref["punt_global"] >= 310).mean()), "leads": float((r["punt_global"] >= 310).mean())},
        "ks_global_leads_vs_zona": float(stats.ks_2samp(ref["punt_global"], r["punt_global"]).statistic),
        "tvd_estrato": float(tvd(ref["estrato"], leads["estrato"])),
        "tvd_naturaleza_colegio": float(tvd(ref["cole_naturaleza"], leads["cole_naturaleza"])),
        "estrato_zona": ref["estrato"].value_counts(normalize=True).sort_index().round(3).to_dict(),
        "estrato_leads": leads["estrato"].value_counts(normalize=True).sort_index().round(3).to_dict()}
    res["direcciones"] = trazabilidad_direcciones(t)
    return res


def trazabilidad_direcciones(t: dict[str, pd.DataFrame]) -> dict:
    """Cada dirección del formulario es una placa real (Catastro Bogotá) o una dirección real del DANE (llave:
    codigo_direccion): misma dirección, coordenada y localidad; en Bogotá, manzana del mismo estrato del aspirante;
    y las distancias se recalculan igual desde la coordenada."""
    f = t["formulario_admision"].merge(t["aspirante"][["aspirante_id", "ubicacion_id", "estrato"]], on="aspirante_id")
    dirs = cat.direcciones()
    cruce = f.merge(dirs, left_on="codigo_direccion", right_on="codigo_fuente", how="left", suffixes=("", "_real"),
                    indicator=True)
    encontrada = cruce["_merge"] == "both"
    bogota = cruce["ubicacion_id"] < 100
    recta, vial = cat.distancias_campus(cruce["direccion_lat"], cruce["direccion_lon"])
    return {"n": len(f), "bogota": int(bogota.sum()), "sabana_centro": int((~bogota).sum()),
            "encontradas": float(encontrada.mean()),
            "identicas": float((encontrada & (cruce["direccion"] == cruce["direccion_real"])
                                & ((cruce["direccion_lat"] - cruce["lat"]).abs() < 1e-6)
                                & ((cruce["direccion_lon"] - cruce["lon"]).abs() < 1e-6)
                                & (cruce["ubicacion_id"] == cruce["ubicacion_id_real"])).mean()),
            "estrato_manzana_igual_bogota": float((cruce.loc[bogota, "estrato"] == cruce.loc[bogota, "estrato_real"]).mean()),
            "distancias_recalculadas": float(((np.abs(recta - cruce["distancia_campus_km"]) < 0.006)
                                              & (np.abs(vial - cruce["distancia_vial_km"]) < 0.006)).mean()),
            "razon_vial_recta": float((cruce["distancia_vial_km"] / cruce["distancia_campus_km"]).mean()),
            "distancias_distintas": int(cruce["distancia_vial_km"].nunique())}


# =============================================================================
# CAPA 3 — Plausibilidad y recuperación de parámetros
# =============================================================================
def logit_mle(y: np.ndarray, x: np.ndarray, iteraciones: int = 100) -> tuple[np.ndarray, np.ndarray]:
    """Regresión logística por máxima verosimilitud (Newton-Raphson).

    En cada paso: p = σ(Xβ), gradiente g = Xᵀ(y − p), información de Fisher I = Xᵀ W X con W = p(1 − p),
    y se actualiza β ← β + I⁻¹ g. Al converger, la covarianza de β̂ es I⁻¹ y su raíz da los errores estándar.
    """
    beta = np.zeros(x.shape[1])
    for _ in range(iteraciones):
        p = 1 / (1 + np.exp(-(x @ beta)))
        info = x.T @ (x * (p * (1 - p))[:, None])
        paso = np.linalg.solve(info, x.T @ (y - p))
        beta += paso
        if np.max(np.abs(paso)) < 1e-10:
            break
    p = 1 / (1 + np.exp(-(x @ beta)))
    cov = np.linalg.inv(x.T @ (x * (p * (1 - p))[:, None]))
    return beta, np.sqrt(np.diag(cov))


def recuperar(y: pd.Series, x: pd.DataFrame, verdaderos: dict) -> pd.DataFrame:
    """Ajusta una regresión logística con el MISMO diseño del modelo verdadero y compara coeficientes."""
    beta, ee = logit_mle(y.astype(float).to_numpy(), x.astype(float).to_numpy())
    z = stats.norm.ppf(0.975)                                  # 1.96 para un IC del 95%
    tabla = pd.DataFrame({"verdadero": pd.Series(verdaderos), "estimado": pd.Series(beta, index=x.columns),
                          "ic95_inf": pd.Series(beta - z * ee, index=x.columns), "ic95_sup": pd.Series(beta + z * ee, index=x.columns)})
    tabla["dentro_ic95"] = (tabla["verdadero"] >= tabla["ic95_inf"]) & (tabla["verdadero"] <= tabla["ic95_sup"])
    return tabla


def capa3(t: dict[str, pd.DataFrame], cfg: dict) -> dict:
    a, r, i, s, h = t["aspirante"], t["resultado_saber11"], t["inscripcion"], t["seguimiento_academico"], t["historial_bachillerato"]
    ubic = cat.tabla_ubicaciones().set_index("ubicacion_id")["distancia_campus_km"]
    a = a.assign(distancia_localidad_km=a["ubicacion_id"].map(ubic))      # del lead solo se conoce su localidad
    d = i.merge(a[["aspirante_id", "estrato", "canal"]], on="aspirante_id") \
         .merge(t["formulario_admision"][["aspirante_id", "distancia_vial_km"]], on="aspirante_id") \
         .merge(r[["aspirante_id", "punt_global"]], on="aspirante_id")
    hist = d[d["periodo"] != "2027-1"].copy()
    leads_hist = a[a["periodo_interes"] != "2027-1"].copy()
    leads_hist["inscrito"] = leads_hist["aspirante_id"].isin(i["aspirante_id"]).astype(int)
    res = {"tasa_conversion_lead": float(leads_hist["inscrito"].mean()),
           "tasa_matricula_historica": float(hist["matriculado"].mean())}
    activos = s[s["periodo"] == "2026-2"]
    res["pct_becados_activos_2026_2"] = float(activos["beca_activa_inicio"].fillna(False).astype(bool).mean())
    sem1 = s[(s["semestre_cursado"] == 1) & s["promedio_semestre"].notna()].merge(d[["inscripcion_id", "punt_global", "beca"]], on="inscripcion_id")
    res["corr_icfes_promedio_sem1"] = float(np.corrcoef(sem1["punt_global"], sem1["promedio_semestre"])[0, 1])
    # Notas del colegio (simuladas): relación positiva pero IMPERFECTA con el ICFES real
    rh = r.merge(h, on="aspirante_id").merge(a[["aspirante_id", "colegio_cod_dane"]], on="aspirante_id")
    p_col, med = rh["promedio_acumulado_colegio"], rh["promedio_acumulado_colegio"].median()
    q_sup = rh["punt_global"] >= rh["punt_global"].quantile(0.8)
    beca = rh["punt_global"] >= 310
    grandes = rh[rh.groupby("colegio_cod_dane")["punt_global"].transform("size") >= 5].copy()
    for c in ["punt_global", "promedio_acumulado_colegio"]:
        grandes[c] = grandes[c] - grandes.groupby("colegio_cod_dane")[c].transform("mean")
    res["promedio_colegio"] = {
        "media": float(p_col.mean()), "de": float(p_col.std()),
        "corr_icfes": float(np.corrcoef(rh["punt_global"], p_col)[0, 1]),
        "corr_dentro_colegio": float(np.corrcoef(grandes["punt_global"], grandes["promedio_acumulado_colegio"])[0, 1]),
        "discordancia_quintil_superior": float((p_col[q_sup] < med).mean()),
        "icfes_310_o_mas": int(beca.sum()), "icfes_310_con_promedio_basico": int((p_col[beca] < 4.0).sum()),
        "quintil_inferior_con_promedio_superior": int((p_col[rh["punt_global"] < rh["punt_global"].quantile(0.2)] >= 4.6).sum()),
        "promedio_por_quintil_icfes": rh.groupby(pd.qcut(rh["punt_global"], 5, labels=False))["promedio_acumulado_colegio"]
                                       .mean().round(3).to_dict(),
        "desempeno": h["desempeno_nacional"].value_counts(normalize=True).round(3).to_dict()}
    q = pd.qcut(sem1["punt_global"], 5, labels=False)
    prom_q = sem1.groupby(q)["promedio_semestre"].mean()
    res["promedio_por_quintil_icfes"] = prom_q.round(3).to_dict()
    res["promedio_monotono_creciente"] = bool(prom_q.is_monotonic_increasing)
    qd = pd.qcut(hist["distancia_vial_km"].rank(method="first"), 5, labels=False)
    tasa_d = hist.groupby(qd)["matriculado"].mean()
    res["matricula_por_quintil_distancia"] = tasa_d.round(3).to_dict()
    res["spearman_distancia_matricula"] = float(stats.spearmanr(tasa_d.index, tasa_d.values).statistic)
    res["conversion_por_canal"] = leads_hist.groupby("canal")["inscrito"].mean().round(3).to_dict()
    hist["con_foes"] = hist["fondo_id"].notna()
    res["foes"] = {"inscritos_elegibles": int(d["elegible_foes"].sum()), "con_apoyo": int(d["fondo_id"].notna().sum()),
                   "matricula_con_apoyo": float(hist.loc[hist["con_foes"], "matriculado"].mean()),
                   "matricula_elegibles_sin_apoyo": float(hist.loc[hist["elegible_foes"] & ~hist["con_foes"], "matriculado"].mean())}
    ev = sem1.dropna(subset=["conserva_beca"])
    res["conserva_beca_sem1_por_beca"] = ev.groupby("beca")["conserva_beca"].mean().round(3).to_dict()

    verd = json.loads((OCULTO / "parametros_verdaderos.json").read_text(encoding="utf-8"))
    # --- (a) modelo verdadero de MATRÍCULA (inscritos admitidos de periodos históricos)
    b = cfg["generador"]["matricula"]
    adm = hist[hist["admitido"]].copy()
    x = pd.DataFrame({"intercepto": 1.0, "pct_descuento": adm["pct_descuento_inicial"],
                      "log_distancia": np.log(np.maximum(adm["distancia_vial_km"], 2.0) / 10),
                      "icfes_cuadratico": ((adm["punt_global"] - 280) / 50) ** 2,
                      "entrevista": adm["entrevista_realizada"].astype(float),
                      "programa_SSIA": (adm["programa"] == "SSIA").astype(float),
                      "periodo_2": adm["periodo"].str.endswith("-2").astype(float),
                      "apoyo_foes": adm["fondo_id"].notna().astype(float)})
    for e in [1, 2, 4]:
        x[f"estrato_{e}"] = (adm["estrato"] == e).astype(float)
    x["estrato_5_6"] = (adm["estrato"] >= 5).astype(float)             # estratos escasos: se agrupan
    for c in [c for c in b["beta_canal"] if c != "SITIO_WEB"]:
        x[f"canal_{c}"] = (adm["canal"] == c).astype(float)
    verdaderos = {"intercepto": verd["intercepto_calibrado"], "pct_descuento": b["beta_descuento"],
                  "log_distancia": b["beta_log_distancia"], "icfes_cuadratico": b["beta_icfes_cuadratico"],
                  "entrevista": b["beta_entrevista"], "programa_SSIA": b["beta_programa_ssia"], "periodo_2": b["beta_periodo_2"],
                  "apoyo_foes": b["beta_foes"],
                  **{f"estrato_{e}": b["beta_estrato"][e] for e in [1, 2, 4]}, "estrato_5_6": b["beta_estrato"][5],
                  **{f"canal_{c}": b["beta_canal"][c] for c in b["beta_canal"] if c != "SITIO_WEB"}}
    tm = recuperar(adm["matriculado"], x, verdaderos)
    # --- (b) modelo verdadero de CONVERSIÓN lead -> inscripción (leads de periodos históricos)
    ac = cfg["generador"]["captacion"]["conversion_lead"]
    efe = verd["efecto_asesor"]
    L = leads_hist
    x2 = pd.DataFrame({"intercepto": 1.0,
                       "log_distancia": np.log(np.maximum(L["distancia_localidad_km"], 2.0) / 10),
                       "programa_SSIA": (L["programa_interes"] == "SSIA").astype(float)})
    for e in [1, 2, 4]:
        x2[f"estrato_{e}"] = (L["estrato"] == e).astype(float)
    x2["estrato_5_6"] = (L["estrato"] >= 5).astype(float)
    for c in [c for c in ac["alpha_canal"] if c != "SITIO_WEB"]:
        x2[f"canal_{c}"] = (L["canal"] == c).astype(float)
    for k in range(2, len(efe) + 1):
        x2[f"asesor_{k}"] = (L["asesor_id"] == k).astype(float)
    verdaderos2 = {"intercepto": verd["conversion_intercepto"] + efe[0],
                   "log_distancia": ac["alpha_log_distancia"], "programa_SSIA": ac["alpha_programa_ssia"],
                   **{f"estrato_{e}": ac["alpha_estrato"][e] for e in [1, 2, 4]}, "estrato_5_6": ac["alpha_estrato"][5],
                   **{f"canal_{c}": ac["alpha_canal"][c] for c in ac["alpha_canal"] if c != "SITIO_WEB"},
                   **{f"asesor_{k}": efe[k - 1] - efe[0] for k in range(2, len(efe) + 1)}}
    tc = recuperar(L["inscrito"], x2, verdaderos2)
    res["recuperacion_parametros"] = tm.round(3).reset_index(names="parametro").to_dict(orient="records")
    res["recuperacion_conversion"] = tc.round(3).reset_index(names="parametro").to_dict(orient="records")
    res["cobertura_ic95"] = float(pd.concat([tm["dentro_ic95"], tc["dentro_ic95"]]).mean())
    return res


def figuras(t: dict[str, pd.DataFrame]) -> list[str]:
    ref, r, h = t["icfes_zona_referencia"], t["resultado_saber11"], t["historial_bachillerato"]
    archivos = []
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bins = np.linspace(100, 450, 36)
    ax.hist(ref["punt_global"], bins=bins, density=True, alpha=0.55, label="Zona: Bogotá y Sabana Centro (ICFES real)", color="#1B365D")
    ax.hist(r["punt_global"], bins=bins, density=True, alpha=0.55, label="Leads de la base (registros reales elegidos)", color="#E07B39")
    ax.axvline(310, color="#333333", ls="--", lw=1)
    ax.text(312, ax.get_ylim()[1] * 0.9, "Beca Saber 11 (≥ 310)", fontsize=8)
    ax.set_xlabel("Puntaje global Saber 11")
    ax.legend(fontsize=8)
    ax.set_title("Puntaje global: zona de influencia vs. leads")
    fig.tight_layout()
    fig.savefig(FIGURAS / "trazabilidad_puntaje_global.png", dpi=120)
    plt.close(fig)
    archivos.append("figuras/trazabilidad_puntaje_global.png")

    d = r.merge(h, on="aspirante_id")
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(d["punt_global"], d["promedio_acumulado_colegio"], s=6, alpha=0.35, color="#1B365D")
    ax.axvline(310, color="#E07B39", ls="--", lw=1)
    ax.axhline(4.0, color="#E07B39", ls="--", lw=1)
    n_caso = int(((d["punt_global"] >= 310) & (d["promedio_acumulado_colegio"] < 4.0)).sum())
    ax.text(315, 3.1, f"Buen ICFES y promedio básico: {n_caso}", fontsize=8, color="#E07B39")
    ax.set_xlabel("Puntaje global Saber 11 (real)")
    ax.set_ylabel("Promedio acumulado del colegio (simulado)")
    ax.set_title(f"ICFES vs. promedio del colegio (r = {np.corrcoef(d['punt_global'], d['promedio_acumulado_colegio'])[0, 1]:.2f})")
    fig.tight_layout()
    fig.savefig(FIGURAS / "promedio_colegio_vs_icfes.png", dpi=120)
    plt.close(fig)
    archivos.append("figuras/promedio_colegio_vs_icfes.png")
    return archivos


def escribir_reporte(c1: pd.DataFrame, c2: dict, c3: dict, cfg: dict, figs: list[str]) -> str:
    v = cfg["validacion"]
    ok_traz = min(c2["registros_encontrados"], c2["puntajes_identicos"], c2["contexto_identico"]) >= v["trazabilidad_min"]
    ok_rep = c2["registros_repetidos"] == 0
    dr = c2["direcciones"]
    ok_dir = min(dr["encontradas"], dr["identicas"], dr["estrato_manzana_igual_bogota"], dr["distancias_recalculadas"]) >= 1.0
    pc, vp = c3["promedio_colegio"], v["promedio_colegio"]
    ok_pcorr = vp["corr_icfes"]["min"] <= pc["corr_icfes"] <= vp["corr_icfes"]["max"]
    ok_disc = pc["discordancia_quintil_superior"] >= vp["discordancia_min"]
    an = v["anclas"]
    ok_conv = abs(c3["tasa_conversion_lead"] - an["conversion_lead"]["objetivo"]) <= an["conversion_lead"]["tolerancia"]
    ok_tasa = abs(c3["tasa_matricula_historica"] - an["tasa_matricula"]["objetivo"]) <= an["tasa_matricula"]["tolerancia"]
    ok_beca = abs(c3["pct_becados_activos_2026_2"] - an["pct_becados_activos"]["objetivo"]) <= an["pct_becados_activos"]["tolerancia"]
    ok_cob = c3["cobertura_ic95"] >= 0.80
    sem = lambda ok: "✅ Cumple" if ok else "❌ No cumple"
    L = ["# Reporte de validación — Semana 1", "",
         f"Generado: {date.today().isoformat()} · Semilla: {cfg['proyecto']['semilla']} · "
         f"Criterios definidos antes de generar en `config/reglas_negocio.yaml`.", "",
         "## Resumen", "", "| Capa | Criterio | Resultado | Estado |", "|---|---|---|---|",
         f"| 1 | Reglas de negocio e integridad ({len(c1)} reglas, bloques 1, 2, 5 y seguimiento) | {int((~c1['cumple']).sum())} reglas con violaciones | {sem(c1['cumple'].all())} |",
         f"| 2 | Resultados Saber 11 idénticos a su registro real del ICFES (pruebas, global, colegio, estrato, género) = 100% | "
         f"{min(c2['registros_encontrados'], c2['puntajes_identicos'], c2['contexto_identico']):.1%} | {sem(ok_traz)} |",
         f"| 2 | Ningún registro real repetido | {c2['registros_repetidos']} | {sem(ok_rep)} |",
         f"| 2 | Direcciones idénticas a una placa de Catastro o a una dirección del DANE, con manzana del mismo estrato = 100% | "
         f"{min(dr['encontradas'], dr['identicas'], dr['estrato_manzana_igual_bogota'], dr['distancias_recalculadas']):.1%} | {sem(ok_dir)} |",
         f"| 3 | Correlación ICFES vs. promedio del colegio entre {vp['corr_icfes']['min']} y {vp['corr_icfes']['max']} | {pc['corr_icfes']:.3f} | {sem(ok_pcorr)} |",
         f"| 3 | Quintil superior del ICFES con promedio bajo la mediana ≥ {vp['discordancia_min']} | {pc['discordancia_quintil_superior']:.3f} | {sem(ok_disc)} |",
         f"| 3 | Conversión lead → inscrito ≈ {an['conversion_lead']['objetivo']} ± {an['conversion_lead']['tolerancia']} | {c3['tasa_conversion_lead']:.3f} | {sem(ok_conv)} |",
         f"| 3 | Tasa de matrícula de inscritos ≈ {an['tasa_matricula']['objetivo']} ± {an['tasa_matricula']['tolerancia']} | {c3['tasa_matricula_historica']:.3f} | {sem(ok_tasa)} |",
         f"| 3 | Becados activos ≈ {an['pct_becados_activos']['objetivo']} ± {an['pct_becados_activos']['tolerancia']} | {c3['pct_becados_activos_2026_2']:.3f} | {sem(ok_beca)} |",
         f"| 3 | Cobertura IC95% de parámetros verdaderos (2 modelos) ≥ 0.80 | {c3['cobertura_ic95']:.2f} | {sem(ok_cob)} |",
         f"| 3 | Promedio crece con el ICFES (monótono) | {c3['promedio_monotono_creciente']} | {sem(c3['promedio_monotono_creciente'])} |",
         "", "## Capa 1 — Reglas de negocio e integridad", "", "| Bloque | Regla | Filas | Violaciones | Estado |", "|---|---|---|---|---|"]
    L += [f"| {x.bloque} | {x.regla} | {x.filas_revisadas:,} | {x.violaciones} | {sem(x.cumple)} |" for x in c1.itertuples()]
    rp = c2["representatividad"]
    L += ["", "## Capa 2 — Trazabilidad con los registros reales del ICFES", "",
          f"Los {c2['n_resultados']:,} resultados Saber 11 de la base salen de {c2['n_registros_zona']:,} registros válidos de "
          "estudiantes de Bogotá y Sabana Centro (ICFES, datos abiertos kgxf-xxbe, periodos 2019-2 y 2022-2).", "",
          "| Verificación | Resultado |", "|---|---|",
          f"| Registro real encontrado con `registro_icfes` | {c2['registros_encontrados']:.1%} |",
          f"| 5 pruebas y puntaje global idénticos al registro real | {c2['puntajes_identicos']:.1%} |",
          f"| Colegio, estrato, género y periodo idénticos al registro real | {c2['contexto_identico']:.1%} |",
          f"| Registros reales repetidos | {c2['registros_repetidos']} |",
          f"| Periodo de origen | {c2['periodos_origen']} |", "",
          "### Direcciones (Catastro Bogotá y DANE)", "",
          f"Los {dr['n']:,} formularios tienen una dirección real asignada al azar: {dr['bogota']:,} placas de Catastro Bogotá y "
          f"{dr['sabana_centro']:,} direcciones del MGN del DANE (Sabana Centro).", "",
          "| Verificación | Resultado |", "|---|---|",
          f"| Dirección encontrada con `codigo_direccion` | {dr['encontradas']:.1%} |",
          f"| Dirección, coordenada y localidad idénticas a la fuente | {dr['identicas']:.1%} |",
          f"| Bogotá: manzana del mismo estrato del aspirante (SDP) | {dr['estrato_manzana_igual_bogota']:.1%} |",
          f"| Distancias recalculadas desde la coordenada | {dr['distancias_recalculadas']:.1%} |",
          f"| Distancias distintas (antes: 28, una por localidad o municipio) | {dr['distancias_distintas']:,} |",
          f"| Distancia por vías / en línea recta (promedio) | {dr['razon_vial_recta']:.2f} |", "",
          "Representatividad (informativa): los leads no tienen que parecerse a toda la zona porque se eligieron con el perfil de "
          "la universidad (S-05).", "",
          f"- Media del puntaje global: zona {rp['media_global']['zona']:.1f} · leads {rp['media_global']['leads_con_resultado']:.1f} "
          f"· referencia publicada Bogotá 2022: {rp['media_global']['referencia_publicada_bogota_2022']} (Agencia Atenea, 2023).",
          f"- Proporción con global ≥ 310: zona {rp['pct_global_310_o_mas']['zona']:.3f} · leads {rp['pct_global_310_o_mas']['leads']:.3f}.",
          f"- KS del puntaje global leads vs. zona: {rp['ks_global_leads_vs_zona']:.3f} · TVD del estrato: {rp['tvd_estrato']:.3f} · "
          f"TVD de la naturaleza del colegio: {rp['tvd_naturaleza_colegio']:.3f}.",
          f"- Estratos en la zona: {rp['estrato_zona']} · en los leads: {rp['estrato_leads']}.", ""]
    L += [f"![{f}]({f})" for f in figs]
    L += ["", "## Capa 3 — Plausibilidad y recuperación de parámetros", "",
          f"- Conversión lead → inscrito por canal: {c3['conversion_por_canal']}.",
          f"- FOES/FOEST: {c3['foes']['inscritos_elegibles']} inscritos elegibles, {c3['foes']['con_apoyo']} con apoyo; matrícula "
          f"{c3['foes']['matricula_con_apoyo']:.3f} con apoyo vs. {c3['foes']['matricula_elegibles_sin_apoyo']:.3f} elegibles sin apoyo.",
          "- Notas del colegio (simuladas, S-34 y S-35): "
          f"promedio {pc['media']:.2f} (DE {pc['de']:.2f}); correlación con el ICFES r = {pc['corr_icfes']:.3f} en general y "
          f"{pc['corr_dentro_colegio']:.3f} entre compañeros del mismo colegio; {pc['icfes_310_con_promedio_basico']} de "
          f"{pc['icfes_310_o_mas']} aspirantes con ICFES ≥ 310 tienen promedio básico (< 4.0); "
          f"{pc['quintil_inferior_con_promedio_superior']} del quintil inferior del ICFES tienen promedio superior (≥ 4.6).",
          f"- Promedio del colegio por quintil de ICFES: {pc['promedio_por_quintil_icfes']}.",
          f"- Correlación ICFES global vs. promedio del 1er semestre: r = {c3['corr_icfes_promedio_sem1']:.3f} (literatura colombiana: relación positiva y moderada).",
          f"- Promedio del 1er semestre por quintil de ICFES: {c3['promedio_por_quintil_icfes']}.",
          f"- Tasa de matrícula por quintil de distancia por vías desde la dirección (1 = más cerca): {c3['matricula_por_quintil_distancia']} (Spearman = {c3['spearman_distancia_matricula']:.2f}).",
          f"- Conservación de beca al cierre del 1er semestre: {c3['conserva_beca_sem1_por_beca']}.", ""]
    for titulo, clave in [("modelo verdadero de matrícula (inscritos admitidos)", "recuperacion_parametros"),
                          ("modelo verdadero de conversión lead → inscripción", "recuperacion_conversion")]:
        L += [f"### Recuperación de los parámetros del {titulo}", "",
              "| Parámetro | Verdadero | Estimado | IC95% | ¿Contiene el verdadero? |", "|---|---|---|---|---|"]
        L += [f"| {p['parametro']} | {p['verdadero']} | {p['estimado']} | [{p['ic95_inf']}, {p['ic95_sup']}] | {'Sí' if p['dentro_ic95'] else 'No'} |"
              for p in c3[clave]]
        L.append("")
    L += [f"Cobertura total: {c3['cobertura_ic95']:.0%} de los parámetros verdaderos dentro de su IC95%. "
          "Con muestras finitas se espera que alrededor de 1 de cada 20 quede por fuera por azar.", ""]
    return "\n".join(L)


def main() -> None:
    asegurar_carpetas()
    cfg = cargar_config()
    t = cargar()
    print("Capa 1: reglas de negocio ...")
    c1 = capa1(t)
    print(c1.to_string(index=False))
    print("Capa 2: trazabilidad con los registros reales del ICFES ...")
    c2 = capa2(t)
    print(json.dumps(c2, indent=1, default=str))
    print("Capa 3: plausibilidad y recuperación de parámetros ...")
    c3 = capa3(t, cfg)
    print(json.dumps({k: v for k, v in c3.items() if not k.startswith("recuperacion")}, indent=1, default=str))
    figs = figuras(t)
    (REPORTS / "validacion_semana1.md").write_text(escribir_reporte(c1, c2, c3, cfg, figs), encoding="utf-8")
    c1.to_csv(REPORTS / "validacion_capa1_reglas.csv", index=False, encoding="utf-8-sig")
    (REPORTS / "validacion_resultados.json").write_text(
        json.dumps({"capa1": c1.to_dict(orient="records"), "capa2": c2, "capa3": c3}, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8")
    print(f"\nReporte: {REPORTS / 'validacion_semana1.md'}")


if __name__ == "__main__":
    main()
