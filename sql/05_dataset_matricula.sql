-- =============================================================================
-- 05_dataset_matricula.sql — Capa ANALÍTICA (OLAP): una sola tabla plana para Machine Learning
-- Modelo de propensión a la matrícula · Unicervantes
--
-- Las 25 tablas de 01_esquema.sql son la capa transaccional (OLTP): normalizada, buena para registrar
-- el proceso de admisión, pero incómoda para entrenar modelos. Esta tabla consolida todo en una fila por
-- INSCRITO y una columna por variable, con la distancia al campus y el promedio del colegio ya calculados.
-- Python la lee con un solo SELECT (API de Supabase de solo lectura), sin uniones entre tablas.
--
--   conjunto = ENTRENAMIENTO   periodos 2024-1 a 2026-2, con resultado de matrícula (objetivo 0/1)
--   conjunto = CAMPANA_2027_1  campaña abierta: matriculado vacío (aún no se conoce) -> se predice
--
-- Excluidas a propósito: datos personales (nombres, documento, contactos, aspirante_id), variables con
-- FUGA DE DATOS (documentos entregados, pronto pago, fecha de matrícula, beneficio, financiación) y las del
-- objetivo 2 (promedios universitarios). Los valores 0/1 se guardan como INTEGER en los dos motores.
-- Orden de ejecución: 01_esquema.sql -> 02_datos.sql -> 03_vistas.sql -> 05_dataset_matricula.sql
-- SQL portable: PostgreSQL / Supabase y SQLite.
-- =============================================================================

DROP TABLE IF EXISTS dataset_matricula;

CREATE TABLE dataset_matricula (
    -- Control (no son predictores)
    inscripcion_id                  INTEGER      PRIMARY KEY,
    periodo                         VARCHAR(6)   NOT NULL,
    programa                        VARCHAR(4)   NOT NULL CHECK (programa IN ('AD', 'SSIA')),
    conjunto                        VARCHAR(15)  NOT NULL CHECK (conjunto IN ('ENTRENAMIENTO', 'CAMPANA_2027_1')),
    -- Objetivo
    matriculado                     INTEGER      CHECK (matriculado IN (0, 1)),
    -- Aspirante y residencia
    genero                          CHAR(1)      NOT NULL,
    edad_al_inscribirse             INTEGER      NOT NULL,
    estrato                         INTEGER      NOT NULL CHECK (estrato BETWEEN 1 AND 6),
    nacionalidad                    VARCHAR(40)  NOT NULL,
    estado_civil                    VARCHAR(12)  NOT NULL,
    regimen_salud                   VARCHAR(12)  NOT NULL,
    tipo_ubicacion                  VARCHAR(10)  NOT NULL,
    ciudad                          VARCHAR(40)  NOT NULL,
    departamento                    VARCHAR(20)  NOT NULL,
    distancia_campus_km             NUMERIC(5,2) NOT NULL CHECK (distancia_campus_km > 0),
    distancia_vial_km               NUMERIC(5,2) NOT NULL CHECK (distancia_vial_km >= distancia_campus_km),
    -- Captación
    canal                           VARCHAR(20)  NOT NULL,
    captado_en_evento               INTEGER      NOT NULL CHECK (captado_en_evento IN (0, 1)),
    asesor_id                       INTEGER      NOT NULL,
    dias_registro_a_inscripcion     INTEGER      NOT NULL CHECK (dias_registro_a_inscripcion >= 0),
    contactos_antes_de_inscribirse  INTEGER      NOT NULL CHECK (contactos_antes_de_inscribirse >= 0),
    -- Colegio
    colegio_naturaleza              VARCHAR(10)  NOT NULL,
    colegio_caracter                VARCHAR(20),                                     -- nulo real del ICFES
    colegio_bilingue                VARCHAR(2)   CHECK (colegio_bilingue IN ('SI', 'NO')),   -- nulo real del ICFES
    tipo_colegio                    VARCHAR(10)  NOT NULL,
    colegio_nivel                   VARCHAR(5)   NOT NULL,
    colegio_promedio_saber11        NUMERIC(4,1) NOT NULL,
    colegio_en_convenio             INTEGER      NOT NULL CHECK (colegio_en_convenio IN (0, 1)),
    -- Académico
    anios_desde_saber11             INTEGER      NOT NULL CHECK (anios_desde_saber11 >= 0),
    punt_lectura_critica            INTEGER      NOT NULL,
    punt_matematicas                INTEGER      NOT NULL,
    punt_sociales                   INTEGER      NOT NULL,
    punt_ciencias                   INTEGER      NOT NULL,
    punt_ingles                     INTEGER      NOT NULL,
    punt_global                     INTEGER      NOT NULL CHECK (punt_global BETWEEN 0 AND 500),
    promedio_acumulado_colegio      NUMERIC(3,2) NOT NULL CHECK (promedio_acumulado_colegio BETWEEN 1.0 AND 5.0),
    promedio_matematicas_colegio    NUMERIC(3,2) NOT NULL CHECK (promedio_matematicas_colegio BETWEEN 1.0 AND 5.0),
    desempeno_bachillerato          VARCHAR(8)   NOT NULL,
    -- Comercial (se conoce antes de la decisión de matricularse)
    entrevista_realizada            INTEGER      NOT NULL CHECK (entrevista_realizada IN (0, 1)),
    puntaje_vocacional              INTEGER      CHECK (puntaje_vocacional BETWEEN 1 AND 5),  -- nulo si no hubo entrevista
    cumple_req_saber11              INTEGER      NOT NULL CHECK (cumple_req_saber11 IN (0, 1)),
    cumple_req_mi_vocacion          INTEGER      NOT NULL CHECK (cumple_req_mi_vocacion IN (0, 1)),
    beca                            VARCHAR(12)  NOT NULL,
    pct_descuento_inicial           NUMERIC(5,4) NOT NULL,
    valor_semestre_bruto            INTEGER      NOT NULL,
    valor_neto_primer_semestre      INTEGER      NOT NULL,
    elegible_foes                   INTEGER      NOT NULL CHECK (elegible_foes IN (0, 1)),
    apoyo_foes                      INTEGER      NOT NULL CHECK (apoyo_foes IN (0, 1)),
    CHECK ((conjunto = 'CAMPANA_2027_1') = (matriculado IS NULL))
);

INSERT INTO dataset_matricula
SELECT
    v.inscripcion_id,
    v.periodo,
    v.programa,
    CASE WHEN v.periodo = '2027-1' THEN 'CAMPANA_2027_1' ELSE 'ENTRENAMIENTO' END,
    v.matriculado,
    v.genero,
    v.edad_al_inscribirse,
    v.estrato,
    v.nacionalidad,
    v.estado_civil,
    v.regimen_salud,
    v.tipo_ubicacion,
    v.ciudad,
    v.departamento,
    v.distancia_campus_km,
    v.distancia_vial_km,
    v.canal,
    v.captado_en_evento,
    v.asesor_id,
    v.dias_registro_a_inscripcion,
    v.contactos_antes_de_inscribirse,
    v.colegio_naturaleza,
    v.colegio_caracter,
    CASE WHEN c.bilingue IS NULL THEN NULL WHEN c.bilingue THEN 'SI' ELSE 'NO' END,
    v.tipo_colegio,
    v.colegio_nivel,
    v.colegio_promedio_saber11,
    CASE WHEN v.colegio_en_convenio THEN 1 ELSE 0 END,
    v.anios_desde_saber11,
    v.punt_lectura_critica,
    v.punt_matematicas,
    v.punt_sociales,
    v.punt_ciencias,
    v.punt_ingles,
    v.punt_global,
    v.promedio_acumulado_colegio,
    v.promedio_matematicas_colegio,
    v.desempeno_bachillerato,
    CASE WHEN v.entrevista_realizada THEN 1 ELSE 0 END,
    v.puntaje_vocacional,
    CASE WHEN v.cumple_req_saber11 THEN 1 ELSE 0 END,
    CASE WHEN v.cumple_req_mi_vocacion THEN 1 ELSE 0 END,
    v.beca,
    v.pct_descuento_inicial,
    v.valor_semestre_bruto,
    v.valor_neto_primer_semestre,
    CASE WHEN v.elegible_foes THEN 1 ELSE 0 END,
    v.apoyo_foes
FROM vw_dataset_modelado v
JOIN inscripcion i ON i.inscripcion_id = v.inscripcion_id
JOIN aspirante a   ON a.aspirante_id = i.aspirante_id
JOIN colegio c     ON c.colegio_cod_dane = a.colegio_cod_dane;
