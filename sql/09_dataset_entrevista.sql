-- =============================================================================
-- 09_dataset_entrevista.sql — Tabla plana (capa analítica): RESPUESTAS DE LA ENTREVISTA DE ADMISIÓN en texto
--
-- Una fila por INSCRITO con sus respuestas abiertas unidas por sección, en el orden de las preguntas:
--   texto_interes_programa      Interés por el programa académico (5 preguntas)
--   texto_historia_vida         Historia de vida (7 preguntas)
--   texto_interes_universidad   Interés por la universidad (1 pregunta)
-- Vacías si no hubo entrevista. El Sprint 2 las lee para el modelo NLP del puntaje vocacional. El puntaje vocacional
-- del entrevistador está en dataset_matricula. Sin nombres ni documentos; no hay sección de salud mental.
-- Orden: 05_dataset_matricula.sql -> 09_dataset_entrevista.sql. SQL de PostgreSQL / Supabase; para SQLite,
-- src/s04_exportar.py cambia string_agg por group_concat (SQLite >= 3.44 admite ORDER BY dentro del agregado).
-- =============================================================================

DROP TABLE IF EXISTS dataset_entrevista;

CREATE TABLE dataset_entrevista (
    inscripcion_id              INTEGER  PRIMARY KEY,
    texto_interes_programa      TEXT,
    texto_historia_vida         TEXT,
    texto_interes_universidad   TEXT
);

INSERT INTO dataset_entrevista
SELECT
    i.inscripcion_id,
    (SELECT string_agg(r.respuesta, ' ' ORDER BY p.orden) FROM respuesta_entrevista r
       JOIN pregunta_entrevista p ON p.pregunta_id = r.pregunta_id
      WHERE r.inscripcion_id = i.inscripcion_id AND p.seccion = 'INTERES_PROGRAMA'),
    (SELECT string_agg(r.respuesta, ' ' ORDER BY p.orden) FROM respuesta_entrevista r
       JOIN pregunta_entrevista p ON p.pregunta_id = r.pregunta_id
      WHERE r.inscripcion_id = i.inscripcion_id AND p.seccion = 'HISTORIA_VIDA'),
    (SELECT string_agg(r.respuesta, ' ' ORDER BY p.orden) FROM respuesta_entrevista r
       JOIN pregunta_entrevista p ON p.pregunta_id = r.pregunta_id
      WHERE r.inscripcion_id = i.inscripcion_id AND p.seccion = 'INTERES_UNIVERSIDAD')
FROM inscripcion i;
