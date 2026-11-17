# Diccionario de datos — dataset_matricula y dataset_entrevista (Sprint 1)

## dataset_matricula (tabla plana para Machine Learning)

Capa analítica (`sql/05_dataset_matricula.sql`): una fila por inscrito y una columna por variable. Es la tabla que Python lee desde Supabase. Se construye desde las tablas normalizadas de origen (capa transaccional).

| Columna | Tipo | Rol | Descripción | Si está vacío |
|---|---|---|---|---|
| `inscripcion_id` | INTEGER | control | Llave de la inscripción (no es predictor) | - |
| `periodo` | VARCHAR(6) | control | Periodo de ingreso (2024-1 a 2027-1) | - |
| `programa` | VARCHAR(4) | control/predictor | AD o SSIA | - |
| `conjunto` | VARCHAR(15) | control | ENTRENAMIENTO (2024-1 a 2026-2) o CAMPANA_2027_1 (se predice) | - |
| `matriculado` | INTEGER | OBJETIVO | 1 si pagó la matrícula del primer semestre | Campaña 2027-1: aún no se conoce (censura) |
| `genero` | CHAR(1) | predictor | F/M (registro real del ICFES) | - |
| `edad_al_inscribirse` | INTEGER | predictor | Edad cumplida al inscribirse | - |
| `estrato` | INTEGER | predictor | Estrato 1-6 (registro real del ICFES) | - |
| `nacionalidad` | VARCHAR(40) | predictor | País de nacionalidad | - |
| `estado_civil` | VARCHAR(12) | predictor | SOLTERO, UNION_LIBRE, CASADO | - |
| `regimen_salud` | VARCHAR(12) | predictor | CONTRIBUTIVO, SUBSIDIADO, ESPECIAL | - |
| `tipo_ubicacion` | VARCHAR(10) | predictor | LOCALIDAD (Bogotá) o MUNICIPIO (Sabana Centro) | - |
| `ciudad` | VARCHAR(40) | predictor | Ciudad de residencia | - |
| `departamento` | VARCHAR(20) | predictor | Departamento de residencia | - |
| `distancia_campus_km` | NUMERIC(5,2) | predictor | Distancia en línea recta desde la dirección de residencia al campus (YA CALCULADA) | - |
| `distancia_vial_km` | NUMERIC(5,2) | predictor | Distancia por vías estimada desde la dirección al campus: tramo norte-sur + oriente-occidente (S-44) | - |
| `canal` | VARCHAR(20) | predictor | Canal de captación del lead | - |
| `captado_en_evento` | INTEGER | predictor | 1 si llegó por ExpoEstudiantes o Campus Day | - |
| `asesor_id` | INTEGER | predictor | Asesor asignado al registrarse (categórica) | - |
| `dias_registro_a_inscripcion` | INTEGER | predictor | Días entre el registro del lead y la inscripción | - |
| `contactos_antes_de_inscribirse` | INTEGER | predictor | Contactos del asesor hasta la inscripción (los posteriores serían fuga) | - |
| `colegio_naturaleza` | VARCHAR(10) | predictor | OFICIAL (colegio público, nombre del ICFES) o PRIVADO | - |
| `colegio_caracter` | VARCHAR(20) | predictor | ACADÉMICO, TÉCNICO, TÉCNICO/ACADÉMICO, NO APLICA | El ICFES no lo reporta para ese colegio (faltante real) |
| `colegio_bilingue` | VARCHAR(2) | predictor | SI/NO | El ICFES no lo reporta para ese colegio (faltante real) |
| `tipo_colegio` | VARCHAR(10) | predictor | OFICIAL (público) / PRIVADO / TECNICO (clasificación del dashboard) | - |
| `colegio_nivel` | VARCHAR(5) | predictor | Tercil del promedio Saber 11 del colegio en la zona | - |
| `colegio_promedio_saber11` | NUMERIC(4,1) | predictor | Promedio real del Saber 11 de los estudiantes del colegio | - |
| `colegio_en_convenio` | INTEGER | predictor | 1 si el colegio tiene convenio con la universidad | - |
| `anios_desde_saber11` | INTEGER | predictor | Años entre el Saber 11 y el ingreso | - |
| `punt_lectura_critica` | INTEGER | predictor | Saber 11, 0-100 (registro real) | - |
| `punt_matematicas` | INTEGER | predictor | Saber 11, 0-100 (registro real) | - |
| `punt_sociales` | INTEGER | predictor | Saber 11, 0-100 (registro real) | - |
| `punt_ciencias` | INTEGER | predictor | Saber 11, 0-100 (registro real) | - |
| `punt_ingles` | INTEGER | predictor | Saber 11, 0-100 (registro real) | - |
| `punt_global` | INTEGER | predictor | Saber 11, 0-500 (registro real) | - |
| `entrevista_realizada` | INTEGER | predictor | 1 si presentó la entrevista con psicología | - |
| `puntaje_vocacional` | INTEGER | predictor | Valoración vocacional 1-5 de la entrevista | No hubo entrevista (vacío estructural) |
| `cumple_req_saber11` | INTEGER | predictor | 1 si el puntaje global es ≥ 310 | - |
| `cumple_req_mi_vocacion` | INTEGER | predictor | 1 si cumple los requisitos de Mi Vocación | - |
| `beca` | VARCHAR(12) | predictor | Beca asignada en la admisión: SABER_11, MI_VOCACION o NINGUNA | - |
| `pct_descuento_inicial` | NUMERIC(5,4) | predictor | Descuento del primer semestre: beca + descuento, con tope del 50% | - |
| `valor_semestre_bruto` | INTEGER | predictor | Tarifa oficial del semestre (COP) | - |
| `valor_neto_primer_semestre` | INTEGER | predictor | Valor a pagar tras el descuento (COP) | - |
| `elegible_foes` | INTEGER | predictor | 1 si reside en un municipio con FOES/FOEST | - |
| `apoyo_foes` | INTEGER | predictor | 1 si obtuvo el apoyo del fondo municipal antes de matricularse | - |
| `tipo_descuento` | VARCHAR(20) | predictor | Descuento institucional: FAMILIAR_ESTUDIANTE, EGRESADO o PERSONAL | No tiene descuento (la mayoría) |
| `pct_descuento_adicional` | NUMERIC(5,4) | predictor | Porcentaje del descuento institucional (0 si no tiene) | - |
| `elegible_icetex` | INTEGER | predictor | 1 si su Saber 11 cumple el mérito mínimo de ICETEX del municipio de su colegio | - |
| `aplica_icetex` | INTEGER | predictor | 1 si decidió pedir el crédito ICETEX y cumple el Plan Talento STEM | - |

## dataset_entrevista (respuestas de la entrevista de admisión)

Capa analítica (`sql/09_dataset_entrevista.sql`): una fila por inscrito con sus respuestas abiertas unidas por sección (Interés por el programa académico, Historia de vida e Interés por la universidad). La lee el modelo NLP del Sprint 2. Sin nombres ni documentos; la salud mental no se registra (Ley 1581 de 2012, art. 5).

| Columna | Tipo | Rol | Descripción | Si está vacío |
|---|---|---|---|---|
| `inscripcion_id` | INTEGER | control | Llave de la inscripción (se une con dataset_matricula) | - |
| `texto_interes_programa` | TEXT | predictor (NLP) | Respuestas de Interés por el programa académico (5 preguntas), en orden | No hubo entrevista |
| `texto_historia_vida` | TEXT | predictor (NLP) | Respuestas de Historia de vida (7 preguntas), en orden | No hubo entrevista |
| `texto_interes_universidad` | TEXT | predictor (NLP) | Respuesta a ¿Por qué quiere estudiar en Unicervantes? | No hubo entrevista |
