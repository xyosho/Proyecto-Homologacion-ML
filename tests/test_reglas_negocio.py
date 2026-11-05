"""Pruebas de las reglas de negocio contra casos REALES conocidos (no contra el propio generador).

Esto evita la circularidad "el generador cumple las reglas porque las reglas son las del
generador": cada regla se contrasta con una evidencia externa (registro real del ICFES,
recibos de matrícula, normas).
"""
from datetime import date

import pytest

import reglas_negocio as rn


# --- Saber 11 ---------------------------------------------------------------
def test_puntaje_global_registro_real_icfes():
    # Registro real del dataset ICFES (Colegio de La Salle, 2022-4): LC 78, MAT 80, SC 83, CN 71, ING 80 -> 391
    assert rn.puntaje_global(78, 80, 83, 71, 80) == 391


def test_puntaje_global_extremos():
    assert rn.puntaje_global(0, 0, 0, 0, 0) == 0
    assert rn.puntaje_global(100, 100, 100, 100, 100) == 500


def test_umbral_beca_saber11():
    assert rn.beca_por_icfes(310) is True
    assert rn.beca_por_icfes(309) is False


# --- Tarifas y valores pagados: caso conocido (recibos de pago) ------------------
def test_tarifas_oficiales_ad():
    assert rn.tarifa("AD", 2024) == 4_419_000      # orden de pago 2024-2
    assert rn.tarifa("AD", 2025) == 4_658_000      # recibos 2025
    assert rn.tarifa("AD", 2026) == 4_914_000      # Acuerdo 002 de 2025
    assert rn.tarifa("SSIA", 2026) == 4_950_000    # oferta académica


@pytest.mark.parametrize("anio, semestre, esperado", [
    (2024, 1, 2_872_350),   # 2024-2: 35% de la beca Saber 11 en el 1er semestre
    (2025, 2, 3_260_600),   # 2025-1: 30% desde el 2º semestre
    (2025, 3, 3_260_600),   # 2025-2
    (2026, 4, 3_439_800),   # 2026-1
    (2026, 5, 3_439_800),   # 2026-2
])
def test_caso_conocido_recibos_beca_saber11(anio, semestre, esperado):
    pct = rn.pct_descuento_total("SABER_11", semestre)
    assert rn.valor_neto(rn.tarifa("AD", anio), pct) == esperado


def test_mi_vocacion_30_luego_20():
    assert rn.pct_beca("MI_VOCACION", 1) == 0.30
    assert rn.pct_beca("MI_VOCACION", 2) == 0.20
    assert rn.pct_beca("MI_VOCACION", 8) == 0.20
    assert rn.pct_beca("SABER_11", 1) == 0.35
    assert rn.pct_beca("SABER_11", 8) == 0.30


def test_beca_perdida_no_descuenta_y_no_hay_pronto_pago():
    assert rn.pct_descuento_total("MI_VOCACION", 1, beca_activa=False) == 0.0
    assert rn.pct_descuento_total("SABER_11", 1) == 0.35          # el 35% es la beca, sin pronto pago
    assert "pronto_pago" not in rn.cargar_config()


def test_conservacion_beca():
    assert rn.conserva_beca(4.0, False) is True
    assert rn.conserva_beca(3.99, False) is False
    assert rn.conserva_beca(4.5, True) is False                  # sanción disciplinaria


# --- Programas y periodos -----------------------------------------------------
def test_registro_calificado_ssia():
    assert rn.programa_disponible("SSIA", "2026-1") is False     # registro: 30-abr-2026
    assert rn.programa_disponible("SSIA", "2026-2") is True
    assert rn.programa_disponible("AD", "2024-1") is True        # registro: 12-sep-2023


def test_periodo_siguiente():
    assert rn.periodo_siguiente("2024-2") == "2025-1"
    assert rn.periodo_siguiente("2025-1") == "2025-2"


# --- Formulario de admisión ---------------------------------------------------
def test_edad_cumplida():
    assert rn.edad_en(date(2008, 5, 23), date(2026, 5, 22)) == 17
    assert rn.edad_en(date(2008, 5, 23), date(2026, 5, 23)) == 18


def test_documento_por_edad():
    assert rn.tipo_documento_colombiano(17) == "TI"
    assert rn.tipo_documento_colombiano(18) == "CC"
    assert rn.documento_coherente("PEP", 20, "VENEZUELA") is False   # PEP vencido
    assert rn.documento_coherente("PPT", 20, "VENEZUELA") is True


def test_ley_2447_de_2025():
    assert rn.estado_civil_coherente("UNION_LIBRE", 17) is False
    assert rn.estado_civil_coherente("SOLTERO", 17) is True
    assert rn.estado_civil_coherente("CASADO", 25) is True


def test_formatos_contacto():
    assert rn.celular_valido("3223589816") is True and rn.celular_valido("6013223589") is False
    assert rn.fijo_valido("6014399855") is True and rn.fijo_valido("4399855") is False
    assert rn.correo_valido("ana.perez12@correo.test") is True
    assert rn.correo_valido("ana.perez12@gmail.com") is False
    assert rn.direccion_valida("Calle 147 # 12-35") is True
    assert rn.direccion_valida("Transversal 2A Este # 45-14 Sur") is True


# --- Bloques 1, 2 y 5 del dashboard -------------------------------------------
def test_tipo_colegio_dashboard():
    assert rn.tipo_colegio("OFICIAL", "TÉCNICO/ACADÉMICO") == "TECNICO"
    assert rn.tipo_colegio("PRIVADO", "TÉCNICO") == "TECNICO"
    assert rn.tipo_colegio("OFICIAL", "ACADÉMICO") == "OFICIAL"
    assert rn.tipo_colegio("PRIVADO", None) == "PRIVADO"


def test_desempeno_bachillerato_decreto_1290():
    assert rn.desempeno_bachillerato(4.6) == "SUPERIOR"
    assert rn.desempeno_bachillerato(4.59) == "ALTO"
    assert rn.desempeno_bachillerato(3.0) == "BASICO"
    assert rn.desempeno_bachillerato(2.9) == "BAJO"


def test_requisito_mi_vocacion():
    assert rn.cumple_mi_vocacion(True, 3) is True
    assert rn.cumple_mi_vocacion(True, 2) is False
    assert rn.cumple_mi_vocacion(False, None) is False


def test_ventana_de_campana():
    assert rn.ventana_campana("2026-1") == (date(2025, 3, 1), date(2026, 1, 25))
    assert rn.ventana_campana("2026-2") == (date(2026, 1, 10), date(2026, 7, 25))


# --- Fondos municipales (FOES / FOEST) -----------------------------------------
def test_fondo_municipal_por_residencia():
    assert rn.fondo_municipal(25175) == "FOES_CHIA"          # Chía
    assert rn.fondo_municipal(25758) == "FOES_SOPO"          # Sopó
    assert rn.fondo_municipal(25817) == "FOEST_TOCANCIPA"    # Tocancipá
    assert rn.fondo_municipal(11) is None                    # Suba (Bogotá): no aplica
    assert rn.fondo_municipal(25899) is None                 # Zipaquirá: sin fondo encontrado


def test_foes_chia_tiene_convenio_verificado_con_unicervantes():
    from comun import cargar_config
    f = cargar_config()["fondos_educacion_municipal"]["FOES_CHIA"]
    assert f["convenio_unicervantes"] == "VERIFICADO" and f["apoyo_semestral_cop"] == 1_000_000


def test_renovacion_foes():
    assert rn.foes_renueva(3.5) is True
    assert rn.foes_renueva(3.49) is False
