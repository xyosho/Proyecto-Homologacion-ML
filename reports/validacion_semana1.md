# Reporte de validación — Semana 1

Generado: 2026-10-31 · Semilla: 20261022 · Criterios definidos antes de generar en `config/reglas_negocio.yaml`.

## Resumen

| Capa | Criterio | Resultado | Estado |
|---|---|---|---|
| 1 | Reglas de negocio e integridad (68 reglas, bloques 1, 2, 5 y seguimiento) | 0 reglas con violaciones | ✅ Cumple |
| 2 | Resultados Saber 11 idénticos a su registro real del ICFES (pruebas, global, colegio, estrato, género) = 100% | 100.0% | ✅ Cumple |
| 2 | Ningún registro real repetido | 0 | ✅ Cumple |
| 2 | Direcciones idénticas a una placa de Catastro o a una dirección del DANE, con manzana del mismo estrato = 100% | 100.0% | ✅ Cumple |
| 3 | Correlación ICFES vs. promedio del colegio entre 0.3 y 0.55 | 0.415 | ✅ Cumple |
| 3 | Quintil superior del ICFES con promedio bajo la mediana ≥ 0.1 | 0.286 | ✅ Cumple |
| 3 | Conversión lead → inscrito ≈ 0.4 ± 0.03 | 0.405 | ✅ Cumple |
| 3 | Tasa de matrícula de inscritos ≈ 0.45 ± 0.03 | 0.457 | ✅ Cumple |
| 3 | Becados activos ≈ 0.4 ± 0.1 | 0.383 | ✅ Cumple |
| 3 | Cobertura IC95% de parámetros verdaderos (2 modelos) ≥ 0.80 | 0.97 | ✅ Cumple |
| 3 | Promedio crece con el ICFES (monótono) | True | ✅ Cumple |

## Capa 1 — Reglas de negocio e integridad

| Bloque | Regla | Filas | Violaciones | Estado |
|---|---|---|---|---|
| 1 | Fecha de registro dentro de la campaña del periodo de interés y antes del corte | 7,500 | 0 | ✅ Cumple |
| 1 | Edad al registro entre 14 y 70 años | 7,500 | 0 | ✅ Cumple |
| 1 | Programa de interés ofertado en el periodo (AD ≥ 2024-1, SSIA ≥ 2026-2) | 7,500 | 0 | ✅ Cumple |
| 1 | Evento coherente con el canal y la campaña; registro durante el evento | 1,514 | 0 | ✅ Cumple |
| 1 | Leads de ExpoEstudiantes y Campus Day siempre asociados a un evento | 7,500 | 0 | ✅ Cumple |
| 1 | Ningún lead de eventos posteriores a la fecha de corte | 7,500 | 0 | ✅ Cumple |
| 1 | Canal 'colegio en convenio' solo si el colegio tiene convenio | 7,500 | 0 | ✅ Cumple |
| 1 | Celular: 10 dígitos que inician en 3 | 7,500 | 0 | ✅ Cumple |
| 1 | Correo único con dominio reservado .test (RFC 2606) | 7,500 | 0 | ✅ Cumple |
| 1 | Estrato entre 1 y 6 | 7,500 | 0 | ✅ Cumple |
| 1 | Solo los inscritos tienen formulario de admisión y contacto de emergencia | 7,500 | 0 | ✅ Cumple |
| 1 | Edad = edad cumplida en la fecha de inscripción | 2,991 | 0 | ✅ Cumple |
| 1 | Edad al inscribirse ≥ edad al registro | 2,991 | 0 | ✅ Cumple |
| 1 | Orden de fechas: nacimiento < examen Saber 11 < inscripción | 2,991 | 0 | ✅ Cumple |
| 1 | Tipo de documento coherente con edad y nacionalidad (T.I. <18, C.C. ≥18) | 2,991 | 0 | ✅ Cumple |
| 1 | Ningún PEP (vencido desde 28-feb-2023) | 2,991 | 0 | ✅ Cumple |
| 1 | Documento único por tipo | 2,991 | 0 | ✅ Cumple |
| 1 | Teléfono fijo: 601 + 7 dígitos (o vacío) | 2,991 | 0 | ✅ Cumple |
| 1 | Dirección con nomenclatura válida | 2,991 | 0 | ✅ Cumple |
| 1 | Estado civil: menores de 18 solteros (Ley 2447 de 2025) | 2,991 | 0 | ✅ Cumple |
| 1 | Barrio pertenece a la localidad/municipio de residencia (Bogotá: sector catastral de la placa) | 2,991 | 0 | ✅ Cumple |
| 1 | Una vivienda (placa) por aspirante: ningún código de dirección repetido | 2,991 | 0 | ✅ Cumple |
| 1 | Distancia por vías ≥ distancia en línea recta (S-44) | 2,991 | 0 | ✅ Cumple |
| 1 | Contacto cónyuge solo si el aspirante no es soltero | 2,991 | 0 | ✅ Cumple |
| 2 | Puntajes por prueba entre 0 y 100 | 4,263 | 0 | ✅ Cumple |
| 2 | Puntaje global entre 0 y 500 | 4,263 | 0 | ✅ Cumple |
| 2 | Puntaje global = fórmula ICFES 5·(3LC+3MAT+3SC+3CN+ING)/13 | 4,263 | 0 | ✅ Cumple |
| 2 | Todo inscrito tiene resultado Saber 11 y promedio acumulado del colegio | 2,991 | 0 | ✅ Cumple |
| 2 | Promedio acumulado del colegio entre 3.0 y 5.0 (bachiller graduado) | 4,263 | 0 | ✅ Cumple |
| 2 | Desempeño del promedio coherente con la escala (Decreto 1290 de 2009) | 4,263 | 0 | ✅ Cumple |
| 2 | 10 notas por aspirante (grados 10 y 11 × 5 áreas), sin repetir grado y área | 4,263 | 0 | ✅ Cumple |
| 2 | Notas finales por área entre 3.0 y 5.0 (área aprobada) | 42,630 | 0 | ✅ Cumple |
| 2 | Promedio acumulado del colegio = media de sus 10 notas | 4,263 | 0 | ✅ Cumple |
| 2 | Desempeño de cada nota coherente con la escala (Decreto 1290 de 2009) | 42,630 | 0 | ✅ Cumple |
| 2 | Año lectivo del grado 11 = año del Saber 11; grado 10 un año antes | 42,630 | 0 | ✅ Cumple |
| 2 | Inscripción en el programa y periodo de interés del lead | 2,991 | 0 | ✅ Cumple |
| 2 | Orden del embudo: registro ≤ inscripción < matrícula | 2,991 | 0 | ✅ Cumple |
| 2 | Programa ofertado en el periodo de ingreso | 2,991 | 0 | ✅ Cumple |
| 2 | Evaluación de requisitos de las dos becas para cada inscrito | 2,991 | 0 | ✅ Cumple |
| 2 | Cumple requisito Saber 11 ⇔ puntaje global ≥ 310 | 2,991 | 0 | ✅ Cumple |
| 2 | Cumple requisito Mi Vocación ⇔ entrevista y puntaje vocacional ≥ 3 (S-22) | 2,991 | 0 | ✅ Cumple |
| 2 | Beca asignada solo a quien cumple sus requisitos | 1,582 | 0 | ✅ Cumple |
| 2 | Becas no acumulables: con global ≥ 310 no se asigna Mi Vocación (S-02) | 2,991 | 0 | ✅ Cumple |
| 2 | Valor de inversión = tarifa oficial del programa en el año | 2,991 | 0 | ✅ Cumple |
| 2 | Descuento inicial = % de la beca en el 1er semestre | 2,991 | 0 | ✅ Cumple |
| 2 | Valor neto 1er semestre = bruto × (1 − descuento) | 2,991 | 0 | ✅ Cumple |
| 2 | Campaña 2027-1 sin resultado de matrícula (censura) | 416 | 0 | ✅ Cumple |
| 2 | Periodos históricos con resultado de matrícula | 2,575 | 0 | ✅ Cumple |
| 2 | No admitido ⇒ no matriculado | 2,991 | 0 | ✅ Cumple |
| 2 | Matriculado ⇔ tiene fecha de matrícula, beneficio y modalidad de financiación | 2,991 | 0 | ✅ Cumple |
| 2 | Entidad financiera solo (y siempre) con crédito educativo | 2,991 | 0 | ✅ Cumple |
| 2 | Cambio de residencia solo informado para matriculados | 2,991 | 0 | ✅ Cumple |
| 2 | Elegible FOES/FOEST ⇔ reside en un municipio con fondo de educación superior | 2,991 | 0 | ✅ Cumple |
| 2 | El fondo aprobado es el del municipio de residencia | 2,991 | 0 | ✅ Cumple |
| 5 | Contactos entre el registro del lead y la fecha de corte | 18,304 | 0 | ✅ Cumple |
| 5 | Cada contacto lo hace el asesor asignado al lead | 18,304 | 0 | ✅ Cumple |
| 5 | 'Confirma inscripción' y 'seguimiento de matrícula' solo en leads inscritos | 18,304 | 0 | ✅ Cumple |
| 5 | Inversión de captación no negativa y solo en eventos realizados | 52 | 0 | ✅ Cumple |
| S | Valor pagado = bruto × (1 − descuento aplicado) | 3,041 | 0 | ✅ Cumple |
| S | Descuento aplicado sigue la regla (Saber 11 35%→30%; Mi Vocación 30%→20%) | 3,041 | 0 | ✅ Cumple |
| S | Promedios entre 0.0 y 5.0 | 2,072 | 0 | ✅ Cumple |
| S | Promedio acumulado = media de los semestres cursados | 2,072 | 0 | ✅ Cumple |
| S | Conserva beca ⇔ promedio acumulado ≥ 4.0 y sin sanción | 839 | 0 | ✅ Cumple |
| S | Una beca perdida no se recupera (S-21) | 1,176 | 0 | ✅ Cumple |
| S | Semestre en curso (2026-2) sin notas | 3,041 | 0 | ✅ Cumple |
| S | Apoyo FOES solo con fondo aprobado y nunca mayor al valor pagado | 3,041 | 0 | ✅ Cumple |
| S | Renovación FOES: exige apoyo previo y promedio del semestre anterior ≥ 3.5 (S-32) | 3,041 | 0 | ✅ Cumple |
| S | Ningún semestre después de la deserción | 1,176 | 0 | ✅ Cumple |

## Capa 2 — Trazabilidad con los registros reales del ICFES

Los 4,263 resultados Saber 11 de la base salen de 161,431 registros válidos de estudiantes de Bogotá y Sabana Centro (ICFES, datos abiertos kgxf-xxbe, periodos 2019-2 y 2022-2).

| Verificación | Resultado |
|---|---|
| Registro real encontrado con `registro_icfes` | 100.0% |
| 5 pruebas y puntaje global idénticos al registro real | 100.0% |
| Colegio, estrato, género y periodo idénticos al registro real | 100.0% |
| Registros reales repetidos | 0 |
| Periodo de origen | {'20194': 2194, '20224': 2069} |

### Direcciones (Catastro Bogotá y DANE)

Los 2,991 formularios tienen una dirección real asignada al azar: 2,732 placas de Catastro Bogotá y 259 direcciones del MGN del DANE (Sabana Centro).

| Verificación | Resultado |
|---|---|
| Dirección encontrada con `codigo_direccion` | 100.0% |
| Dirección, coordenada y localidad idénticas a la fuente | 100.0% |
| Bogotá: manzana del mismo estrato del aspirante (SDP) | 100.0% |
| Distancias recalculadas desde la coordenada | 100.0% |
| Distancias distintas (antes: 28, una por localidad o municipio) | 1,693 |
| Distancia por vías / en línea recta (promedio) | 1.29 |

Representatividad (informativa): los leads no tienen que parecerse a toda la zona porque se eligieron con el perfil de la universidad (S-05).

- Media del puntaje global: zona 270.8 · leads 273.4 · referencia publicada Bogotá 2022: 273 (Agencia Atenea, 2023).
- Proporción con global ≥ 310: zona 0.226 · leads 0.209.
- KS del puntaje global leads vs. zona: 0.049 · TVD del estrato: 0.146 · TVD de la naturaleza del colegio: 0.032.
- Estratos en la zona: {1: 0.096, 2: 0.439, 3: 0.362, 4: 0.08, 5: 0.017, 6: 0.005} · en los leads: {1: 0.022, 2: 0.376, 3: 0.46, 4: 0.129, 5: 0.012, 6: 0.002}.

![figuras/trazabilidad_puntaje_global.png](figuras/trazabilidad_puntaje_global.png)
![figuras/promedio_colegio_vs_icfes.png](figuras/promedio_colegio_vs_icfes.png)

## Capa 3 — Plausibilidad y recuperación de parámetros

- Conversión lead → inscrito por canal: {'CAMPUS_DAY': 0.502, 'COLEGIO_CONVENIO': 0.457, 'EXPOESTUDIANTES': 0.24, 'INMERSION': 0.64, 'LLAMADA_WHATSAPP': 0.344, 'REDES_SOCIALES': 0.325, 'REFERIDO': 0.562, 'SITIO_WEB': 0.357}.
- FOES/FOEST: 134 inscritos elegibles, 70 con apoyo; matrícula 0.567 con apoyo vs. 0.519 elegibles sin apoyo.
- Notas del colegio (simuladas, S-34 y S-35): promedio 4.05 (DE 0.32); correlación con el ICFES r = 0.415 en general y 0.486 entre compañeros del mismo colegio; 204 de 889 aspirantes con ICFES ≥ 310 tienen promedio básico (< 4.0); 6 del quintil inferior del ICFES tienen promedio superior (≥ 4.6).
- Promedio del colegio por quintil de ICFES: {0: 3.864, 1: 3.982, 2: 4.056, 3: 4.148, 4: 4.225}.
- Correlación ICFES global vs. promedio del 1er semestre: r = 0.321 (literatura colombiana: relación positiva y moderada).
- Promedio del 1er semestre por quintil de ICFES: {0: 3.688, 1: 3.788, 2: 3.808, 3: 3.978, 4: 4.039}.
- Tasa de matrícula por quintil de distancia por vías desde la dirección (1 = más cerca): {0: 0.528, 1: 0.447, 2: 0.482, 3: 0.47, 4: 0.357} (Spearman = -0.70).
- Conservación de beca al cierre del 1er semestre: {'MI_VOCACION': 0.3, 'SABER_11': 0.543}.

### Recuperación de los parámetros del modelo verdadero de matrícula (inscritos admitidos)

| Parámetro | Verdadero | Estimado | IC95% | ¿Contiene el verdadero? |
|---|---|---|---|---|
| intercepto | -1.015 | -0.95 | [-1.29, -0.61] | Sí |
| pct_descuento | 3.0 | 3.025 | [2.475, 3.575] | Sí |
| log_distancia | -0.35 | -0.37 | [-0.53, -0.21] | Sí |
| icfes_cuadratico | -0.25 | -0.279 | [-0.371, -0.188] | Sí |
| entrevista | 0.6 | 0.68 | [0.425, 0.934] | Sí |
| programa_SSIA | 0.1 | 0.022 | [-0.229, 0.273] | Sí |
| periodo_2 | -0.1 | -0.104 | [-0.3, 0.091] | Sí |
| apoyo_foes | 0.5 | 0.512 | [-0.06, 1.084] | Sí |
| estrato_1 | -0.5 | -0.621 | [-1.329, 0.087] | Sí |
| estrato_2 | -0.15 | -0.13 | [-0.317, 0.057] | Sí |
| estrato_4 | 0.1 | 0.117 | [-0.15, 0.383] | Sí |
| estrato_5_6 | 0.0 | -0.489 | [-1.21, 0.233] | Sí |
| canal_EXPOESTUDIANTES | -0.3 | -0.546 | [-0.952, -0.14] | Sí |
| canal_REDES_SOCIALES | -0.1 | -0.223 | [-0.522, 0.077] | Sí |
| canal_REFERIDO | 0.5 | 0.556 | [0.274, 0.837] | Sí |
| canal_CAMPUS_DAY | 0.3 | 0.156 | [-0.16, 0.472] | Sí |
| canal_LLAMADA_WHATSAPP | -0.2 | -0.21 | [-0.543, 0.122] | Sí |
| canal_INMERSION | 0.8 | 0.654 | [0.31, 0.998] | Sí |
| canal_COLEGIO_CONVENIO | 0.3 | 0.196 | [-0.155, 0.547] | Sí |

### Recuperación de los parámetros del modelo verdadero de conversión lead → inscripción

| Parámetro | Verdadero | Estimado | IC95% | ¿Contiene el verdadero? |
|---|---|---|---|---|
| intercepto | -0.841 | -0.841 | [-1.028, -0.654] | Sí |
| log_distancia | -0.4 | -0.404 | [-0.496, -0.312] | Sí |
| programa_SSIA | 0.15 | 0.251 | [0.103, 0.399] | Sí |
| estrato_1 | -0.4 | -0.416 | [-0.789, -0.043] | Sí |
| estrato_2 | -0.1 | -0.106 | [-0.222, 0.01] | Sí |
| estrato_4 | 0.0 | -0.041 | [-0.21, 0.128] | Sí |
| estrato_5_6 | -0.2 | -0.556 | [-0.972, -0.139] | Sí |
| canal_EXPOESTUDIANTES | -0.6 | -0.53 | [-0.743, -0.316] | Sí |
| canal_REDES_SOCIALES | -0.3 | -0.125 | [-0.299, 0.048] | No |
| canal_REFERIDO | 0.8 | 0.881 | [0.7, 1.063] | Sí |
| canal_CAMPUS_DAY | 0.6 | 0.59 | [0.387, 0.792] | Sí |
| canal_LLAMADA_WHATSAPP | -0.2 | -0.064 | [-0.258, 0.13] | Sí |
| canal_INMERSION | 1.2 | 1.2 | [0.952, 1.447] | Sí |
| canal_COLEGIO_CONVENIO | 0.5 | 0.448 | [0.228, 0.669] | Sí |
| asesor_2 | 0.225 | 0.184 | [-0.001, 0.368] | Sí |
| asesor_3 | 0.197 | 0.18 | [-0.005, 0.365] | Sí |
| asesor_4 | 0.585 | 0.587 | [0.405, 0.77] | Sí |
| asesor_5 | 0.858 | 0.827 | [0.644, 1.01] | Sí |
| asesor_6 | 0.139 | -0.036 | [-0.221, 0.149] | Sí |

Cobertura total: 97% de los parámetros verdaderos dentro de su IC95%. Con muestras finitas se espera que alrededor de 1 de cada 20 quede por fuera por azar.
