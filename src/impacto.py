"""SPRINT 5 — Impacto en matrículas e ingreso del primer semestre (COP, con las tarifas oficiales).

Todas las cifras son VALOR ESPERADO: probabilidad × valor. Los dos supuestos (capacidad de seguimiento y efecto de la
llamada) están en config/reglas_negocio.yaml -> impacto, y cada uno se mueve ±50% en el análisis de sensibilidad.
No se usan costos: el proyecto no tiene datos de cuánto cuesta el seguimiento ni la inversión en los eventos.

Escenario 1 · Seguimiento priorizado. Los asesores no alcanzan a hacer seguimiento intensivo a todos los inscritos.
  El seguimiento ayuda poco a quien ya decidió (p cerca de 0 o de 1) y más al indeciso (p cerca de 0,5):
      efecto(p) = efecto_máximo · 4 · p · (1 − p)
  Se comparan tres formas de elegir a quién llamar: al azar, a los de mayor probabilidad y a los indecisos (modelo).
Escenario 2 · Expo Estudiantes. El mismo seguimiento aplicado a los inscritos que llegan de la feria: cuántas
  matrículas más se esperan; además, qué segmentos de mercado priorizar.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def efecto_seguimiento(p, efecto_maximo: float) -> np.ndarray:
    p = np.asarray(p, dtype=float)
    return efecto_maximo * 4 * p * (1 - p)


def escenario_seguimiento(prob: pd.Series, valor_anio: pd.Series, capacidad_pct: float, efecto_maximo: float) -> pd.DataFrame:
    """Matrículas adicionales esperadas y su valor (precio neto del 1er semestre) según a quién se le hace seguimiento."""
    p, v = np.asarray(prob, dtype=float), np.asarray(valor_anio, dtype=float)
    k = int(round(capacidad_pct * len(p)))
    efecto = efecto_seguimiento(p, efecto_maximo)
    estrategias = {
        "Al azar (sin modelo)": None,
        "Mayor probabilidad primero": np.argsort(-p)[:k],
        "Indecisos primero (modelo)": np.argsort(-efecto)[:k],
    }
    filas = []
    for nombre, idx in estrategias.items():
        if idx is None:      # valor esperado de elegir k al azar = k × promedio
            extra, ingreso = k * efecto.mean(), k * (efecto * v).mean()
        else:
            extra, ingreso = efecto[idx].sum(), (efecto[idx] * v[idx]).sum()
        filas.append({"estrategia": nombre, "inscritos_con_seguimiento": k, "matriculas_adicionales": extra,
                      "ingreso_primer_semestre_cop": ingreso})
    return pd.DataFrame(filas)


def sensibilidad(funcion, parametros: dict, variar: list[str], salida: str, factor: float = 0.5) -> pd.DataFrame:
    """Gráfico de tornado: se mueve cada supuesto -50% y +50% (los demás fijos) y se mide el resultado."""
    base = funcion(**parametros)[salida]
    filas = []
    for nombre in variar:
        bajo = funcion(**(parametros | {nombre: parametros[nombre] * (1 - factor)}))[salida]
        alto = funcion(**(parametros | {nombre: parametros[nombre] * (1 + factor)}))[salida]
        filas.append({"supuesto": nombre, "valor_base": parametros[nombre], "resultado_bajo": bajo,
                      "resultado_base": base, "resultado_alto": alto, "rango": abs(alto - bajo)})
    return pd.DataFrame(filas).sort_values("rango", ascending=False).reset_index(drop=True)


def acciones_por_segmento(d: pd.DataFrame, prob: pd.Series, cortes: dict) -> pd.DataFrame:
    """Tabla para Mercadeo: cada segmento de mercado con su propensión, valor esperado y acción sugerida."""
    t = d.assign(prob=np.asarray(prob, dtype=float), valor_esperado=np.asarray(prob, dtype=float) * d["valor_neto_primer_semestre"],
                 lejos=(d["zona_distancia"] == "LEJOS").astype(float), con_beca=(d["beca"] != "NINGUNA").astype(float),
                 indeciso=((np.asarray(prob) >= cortes["BAJA"]) & (np.asarray(prob) < cortes["ALTA"])).astype(float))
    g = t.groupby("segmento_mercado").agg(inscritos=("inscripcion_id", "size"), propension_media=("prob", "mean"),
                                         pct_indecisos=("indeciso", "mean"), pct_lejos=("lejos", "mean"),
                                         pct_con_beca=("con_beca", "mean"), valor_esperado_por_inscrito=("valor_esperado", "mean"))

    def accion(r) -> str:
        partes = []
        if r["propension_media"] >= cortes["ALTA"] - 0.1:
            partes.append("asegurar: proceso de matrícula ágil y recordatorio de las fechas de pago")
        if r["pct_indecisos"] >= 0.5:
            partes.append("prioridad de seguimiento del asesor (muchos indecisos)")
        if r["pct_lejos"] >= 0.4:
            partes.append("ofrecer el beneficio de transporte y revisar FOES de su municipio")
        if r["pct_con_beca"] < 0.4:
            partes.append("informar requisitos de Beca Saber 11 y Mi Vocación (entrevista)")
        return "; ".join(partes) or "contacto estándar"

    g["accion_sugerida"] = g.apply(accion, axis=1)
    return g.sort_values("valor_esperado_por_inscrito", ascending=False)
