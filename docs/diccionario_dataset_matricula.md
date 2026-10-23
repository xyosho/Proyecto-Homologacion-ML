# Diccionario de datos — dataset_matricula (Sprint 1)

## dataset_matricula (tabla plana para Machine Learning)

Capa analítica (`sql/05_dataset_matricula.sql`): una fila por inscrito y una columna por variable. Es la tabla que Python lee desde Supabase. Las tablas de abajo son la capa transaccional de origen.

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
| `colegio_naturaleza` | VARCHAR(10) | predictor | OFICIAL o PRIVADO | - |
| `colegio_caracter` | VARCHAR(20) | predictor | ACADÉMICO, TÉCNICO, TÉCNICO/ACADÉMICO, NO APLICA | El ICFES no lo reporta para ese colegio (faltante real) |
| `colegio_bilingue` | VARCHAR(2) | predictor | SI/NO | El ICFES no lo reporta para ese colegio (faltante real) |
| `tipo_colegio` | VARCHAR(10) | predictor | OFICIAL / PRIVADO / TECNICO (clasificación del dashboard) | - |
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
| `promedio_acumulado_colegio` | NUMERIC(3,2) | predictor | Promedio de grados 10 y 11, escala 1.0-5.0 (YA CALCULADO; simulado) | - |
| `promedio_matematicas_colegio` | NUMERIC(3,2) | predictor | Promedio de matemáticas en grados 10 y 11 (simulado) | - |
| `desempeno_bachillerato` | VARCHAR(8) | predictor | Superior/Alto/Básico (Decreto 1290 de 2009) | - |
| `entrevista_realizada` | INTEGER | predictor | 1 si presentó la entrevista con psicología | - |
| `puntaje_vocacional` | INTEGER | predictor | Valoración vocacional 1-5 de la entrevista | No hubo entrevista (vacío estructural) |
| `cumple_req_saber11` | INTEGER | predictor | 1 si el puntaje global es ≥ 310 | - |
| `cumple_req_mi_vocacion` | INTEGER | predictor | 1 si cumple los requisitos de Mi Vocación | - |
| `beca` | VARCHAR(12) | predictor | Beca asignada en la admisión: SABER_11, MI_VOCACION o NINGUNA | - |
| `pct_descuento_inicial` | NUMERIC(5,4) | predictor | Descuento del primer semestre por beca | - |
| `valor_semestre_bruto` | INTEGER | predictor | Tarifa oficial del semestre (COP) | - |
| `valor_neto_primer_semestre` | INTEGER | predictor | Valor a pagar tras el descuento (COP) | - |
| `elegible_foes` | INTEGER | predictor | 1 si reside en un municipio con FOES/FOEST | - |
| `apoyo_foes` | INTEGER | predictor | 1 si obtuvo el apoyo del fondo municipal antes de matricularse | - |

