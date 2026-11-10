"""Reglas de negocio de Unicervantes expresadas como funciones puras.

Estas funciones son la "única fuente de verdad": las usa el generador para CREAR los
datos, el validador para REVISARLOS y las pruebas (tests/) para comprobar que la regla
está bien escrita. Si una regla cambia, solo se cambia aquí o en el YAML.
"""
from __future__ import annotations

import math
import re
from datetime import date

from comun import cargar_config

# ---------------------------------------------------------------------------
# Saber 11
# ---------------------------------------------------------------------------
PESOS_SABER11 = {"lectura_critica": 3, "matematicas": 3, "sociales": 3, "ciencias": 3, "ingles": 1}


def puntaje_global(lectura_critica: int, matematicas: int, sociales: int, ciencias: int, ingles: int) -> int:
    """Puntaje global ICFES = 5 x promedio ponderado de las 5 pruebas (pesos 3,3,3,3,1).

    Global = 5 * (3*LC + 3*MAT + 3*SC + 3*CN + 1*ING) / 13, redondeado al entero.
    Se usa redondeo "hacia arriba en .5" (no el redondeo bancario de Python). Con
    puntajes enteros nunca aparece un .5 exacto, pero así queda igual a ROUND() en SQL.
    Verificado con un registro real del ICFES: LC=78, MAT=80, SC=83, CN=71, ING=80 -> 391.
    """
    suma = 3 * (lectura_critica + matematicas + sociales + ciencias) + ingles
    return int(math.floor(5 * suma / 13 + 0.5))


# ---------------------------------------------------------------------------
# Programas, periodos y tarifas
# ---------------------------------------------------------------------------
def anio_periodo(periodo: str) -> int:
    return int(periodo.split("-")[0])


def periodo_siguiente(periodo: str) -> str:
    anio, sem = periodo.split("-")
    return f"{anio}-2" if sem == "1" else f"{int(anio) + 1}-1"


def periodo_a_numero(periodo: str) -> int:
    """'2024-1' -> 20241, para comparar periodos en orden."""
    anio, sem = periodo.split("-")
    return int(anio) * 10 + int(sem)


def programa_disponible(programa: str, periodo: str) -> bool:
    """Un programa solo recibe aspirantes desde su primer periodo con registro calificado."""
    primero = cargar_config()["programas"][programa]["primer_periodo"]
    return periodo_a_numero(periodo) >= periodo_a_numero(primero)


def tarifa(programa: str, anio: int) -> int:
    return int(cargar_config()["tarifas"][programa][anio]["valor"])


# ---------------------------------------------------------------------------
# Becas y valor a pagar
# ---------------------------------------------------------------------------
def beca_por_icfes(punt_global: int) -> bool:
    """Elegible a Beca Saber 11 si el puntaje global es >= 310."""
    return punt_global >= cargar_config()["becas"]["SABER_11"]["umbral_icfes"]


def pct_beca(beca: str, semestre_cursado: int) -> float:
    """Porcentaje de la beca en el semestre n de la carrera (1 = primer semestre).

    Saber 11: 35% el primer semestre y 30% del segundo en adelante.
    Mi Vocación: 30% el primer semestre y 20% del segundo en adelante.
    """
    b = cargar_config()["becas"][beca]
    return float(b["pct_primer_periodo"] if semestre_cursado == 1 else b["pct_siguientes"])


def pct_descuento_total(beca: str, semestre_cursado: int, beca_activa: bool = True) -> float:
    """Descuento del semestre = la beca, si sigue activa (el pronto pago no es un descuento de la Universidad)."""
    return round(pct_beca(beca, semestre_cursado) if beca_activa else 0.0, 4)


def valor_neto(valor_bruto: int, pct_descuento: float) -> int:
    """Valor a pagar en pesos enteros: bruto x (1 - descuento)."""
    return int(round(valor_bruto * (1 - pct_descuento)))


def conserva_beca(promedio_acumulado: float, sancion: bool) -> bool:
    """La beca se conserva con promedio acumulado >= 4.0 y sin sanciones disciplinarias."""
    return (promedio_acumulado >= cargar_config()["becas"]["SABER_11"]["promedio_minimo"]) and not sancion


# ---------------------------------------------------------------------------
# Datos personales: reglas de coherencia del formulario de admisión
# ---------------------------------------------------------------------------
def edad_en(fecha_nacimiento: date, fecha: date) -> int:
    """Edad cumplida (años) en una fecha dada."""
    return fecha.year - fecha_nacimiento.year - ((fecha.month, fecha.day) < (fecha_nacimiento.month, fecha_nacimiento.day))


def tipo_documento_colombiano(edad: int) -> str:
    """Tarjeta de Identidad para menores de 18 años; Cédula de Ciudadanía desde los 18."""
    return "TI" if edad < 18 else "CC"


def documento_coherente(tipo: str, edad: int, nacionalidad: str) -> bool:
    if nacionalidad == "COLOMBIA":
        return tipo == tipo_documento_colombiano(edad)
    # Extranjeros: C.E. o PPT. El PEP venció el 28-feb-2023 y no es válido en 2024+.
    return tipo in ("CE", "PPT")


def estado_civil_coherente(estado_civil: str, edad: int) -> bool:
    """Ley 2447 de 2025: los menores de 18 no pueden contraer matrimonio ni unión marital."""
    return edad >= 18 or estado_civil == "SOLTERO"


RE_CELULAR = re.compile(r"^3\d{9}$")             # móviles: 10 dígitos que empiezan por 3
RE_FIJO = re.compile(r"^601\d{7}$")              # fijos Bogotá/Cundinamarca: 601 + 7 dígitos (CRC 5826/2019)
RE_CORREO = re.compile(r"^[a-z0-9._]+@[a-z0-9-]+\.test$")   # dominio reservado RFC 2606
# Nomenclatura urbana de Bogotá y Sabana Centro (Catastro / DANE): vía [letra] [Bis [letra]] [Sur|Este] # cruce-placa
RE_DIRECCION = re.compile(r"^(Calle|Carrera|Diagonal|Transversal|Avenida Calle|Avenida Carrera) \d{1,3}[A-Z]?( Bis)?( [A-Z])?"
                          r"( Sur| Este)? # \d{1,3}[A-Z]?( Bis)?( [A-Z])?-\d{1,3}( Sur| Este)?$")


def celular_valido(numero: str) -> bool:
    return bool(RE_CELULAR.match(numero or ""))


def fijo_valido(numero: str | None) -> bool:
    return numero is None or bool(RE_FIJO.match(numero))


def correo_valido(correo: str) -> bool:
    return bool(RE_CORREO.match(correo or ""))


def direccion_valida(direccion: str) -> bool:
    return bool(RE_DIRECCION.match(direccion or ""))


# ---------------------------------------------------------------------------
# Bloques 1, 2 y 5 del dashboard: colegio, bachillerato, becas y campañas
# ---------------------------------------------------------------------------
def tipo_colegio(naturaleza: str, caracter: str | None) -> str:
    """Tipo de colegio pedido en el dashboard (oficial, privado o técnico).

    Mezcla dos atributos del ICFES: si el carácter es técnico (o técnico/académico) el colegio
    se clasifica TECNICO; si no, OFICIAL o PRIVADO según su naturaleza.
    """
    if caracter and "TÉCNICO" in caracter.upper():
        return "TECNICO"
    return "OFICIAL" if naturaleza == "OFICIAL" else "PRIVADO"


def desempeno_bachillerato(promedio: float) -> str:
    """Equivalencia con la escala nacional del Decreto 1290 de 2009 (cortes en el YAML)."""
    cortes = cargar_config()["escala_desempeno_bachillerato"]
    if promedio >= cortes["SUPERIOR"]:
        return "SUPERIOR"
    if promedio >= cortes["ALTO"]:
        return "ALTO"
    if promedio >= cortes["BASICO"]:
        return "BASICO"
    return "BAJO"


def cumple_mi_vocacion(entrevista_realizada: bool, puntaje_vocacional) -> bool:
    """Mi Vocación exige entrevista con psicología y un interés vocacional claro (puntaje >= 3, S-22)."""
    return bool(entrevista_realizada) and puntaje_vocacional is not None and puntaje_vocacional >= 3


def ventana_campana(periodo: str) -> tuple[date, date]:
    """Fechas en que se captan leads para un periodo.

    Periodo -1: de marzo del año anterior a enero; periodo -2: de enero a julio del mismo año.
    """
    v = cargar_config()["inversion_captacion"]["ventana_campana"]
    anio, sem = anio_periodo(periodo), periodo.split("-")[1]
    (mi, di), (mf, df) = [tuple(map(int, x.split("-"))) for x in v[sem]]
    inicio = date(anio - 1 if sem == "1" else anio, mi, di)
    return inicio, date(anio, mf, df)


# ---------------------------------------------------------------------------
# Fondos municipales de educación superior (FOES de Chía y Sopó, FOEST de Tocancipá)
# ---------------------------------------------------------------------------
def fondo_municipal(ubicacion_id: int) -> str | None:
    """Fondo de educación superior del municipio de residencia (None si el municipio no tiene uno)."""
    for fondo_id, f in cargar_config()["fondos_educacion_municipal"].items():
        if int(f["ubicacion_id"]) == int(ubicacion_id):
            return fondo_id
    return None


def foes_renueva(promedio_semestre_anterior: float) -> bool:
    """El apoyo se renueva con el promedio del semestre anterior fijado en el convenio (S-32: >= 3.5)."""
    return promedio_semestre_anterior >= cargar_config()["generador"]["foes"]["promedio_minimo_renovacion"]
