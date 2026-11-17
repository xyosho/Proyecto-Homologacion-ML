# Guía del Sprint 5 — qué se hizo y cómo funciona

## 1. Resumen
El docente pidió probar el modelo con datos que nunca vio y traducirlo a dinero o estudiantes.
- **Prueba:** desde la Semana 1 se guardó **sellado** el resultado de la campaña 2027-1 (416 inscritos). Ningún sprint
  anterior lo leyó. Aquí se abrió: el modelo elegido (regresión logística con el puntaje NLP de la entrevista) se
  equivoca en 33,9%, cerca de la prueba del Sprint 3 (32,7%). La regresión logística del Sprint 2, el modelo base, se
  equivoca en 35,3%: la diferencia (−1,4 puntos, IC 95% de −4,1 a +1,2) todavía está dentro del margen del azar.
- **Impacto:** se calcularon dos escenarios en matrículas adicionales (y, en el primero, su ingreso del 1er semestre con
  las tarifas oficiales):
  1. A quién hacer seguimiento.
  2. Expo Estudiantes.
- **Supuestos:** son dos (capacidad de seguimiento y efecto de la llamada), están declarados en el YAML y se movieron
  ±50% para ver cuánto cambia el resultado.
- **Sin costos:** no se calcula el costo del seguimiento ni el de la Expo, porque el proyecto no tiene esos datos.
- **Para Mercadeo:** una tabla con la acción sugerida para cada segmento de mercado.
- El proyecto predice solo la matrícula: ya no hay escenario de tutoría a becados.

## 2. Mapa de archivos
| Archivo | Qué hace |
|---|---|
| `sprints/sprint_5_validacion_impacto/ejecutar_sprint5.py` | Abre el resultado sellado, evalúa, calcula los 2 escenarios, la sensibilidad y las acciones, y escribe figuras y el resumen |
| `src/impacto.py` | `efecto_seguimiento`, `escenario_seguimiento`, `sensibilidad`, `acciones_por_segmento` |
| `src/modelado.py` → `diferencia_error` | Intervalo bootstrap pareado de la diferencia de error entre el elegido y la logística del Sprint 2 |
| `src/datos.py` → `cargar("resultado_campana_2027_1")` | Lee el resultado sellado de Supabase o, sin conexión, de `data/processed/oculto/resultado_2027_1_sellado.parquet` (en Colab, de esa ruta en la rama Sprint-5 de GitHub) |
| `config/reglas_negocio.yaml` → `impacto` | Los dos supuestos: capacidad de seguimiento y efecto de la llamada |
| `resultados/` | Tablas CSV, `metricas_sprint5.json`, `resumen_impacto.md` y `figuras/` |
| `src/cuadernos/sprint5.py` | Celdas de los cuadernos local y Colab |

## 3. Cómo funciona, paso a paso
**a) El sobre sellado:**
- En la Semana 1, la tabla `dataset_matricula` dejó vacío `matriculado` para los 416 inscritos de 2027-1. El resultado
  real quedó aparte, en la tabla `resultado_campana_2027_1`.
- Solo este script la lee. Una prueba automática verifica que los scripts de los sprints 2 a 4 no la mencionan.
- **Por qué importa:** la prueba 2026-2 del Sprint 3 ya se había mirado una vez. La campaña 2027-1 es la
  validación verdaderamente independiente.

**b) Evaluación:**
- Se usan los modelos finales del Sprint 3, entrenados con 2024-1 a 2026-2: el elegido, XGBoost y la logística del
  Sprint 2 (C = 1), reentrenada en igualdad de condiciones.
- Error, AUC y Brier, con intervalos bootstrap (tabla del README). `diferencia_error` remuestrea los **mismos**
  inscritos para comparar el elegido con la logística del Sprint 2.
- **Matriz de confusión** del elegido con umbral 0,5:
  - 86 no matriculados bien clasificados;
  - 78 falsos positivos;
  - 65 matriculados que el modelo creyó que no;
  - 187 matriculados bien clasificados.

**c) Quintiles** (`prueba_campana_por_quintil.csv`): se ordenan los 416 inscritos por probabilidad y se parten en 5
grupos.

| Grupo | Probabilidad media | Tasa real |
|---|---|---|
| Q1 (menor) | 31% | 29% |
| Q2 | 48% | 60% |
| Q3 | 62% | 59% |
| Q4 | 72% | 69% |
| Q5 (mayor) | 85% | 80% |

- El orden se respeta: a mayor probabilidad, mayor matrícula.
- La calibración es razonable: lo predicho y lo real quedan a unos 10 puntos o menos en cada grupo (en 2027-1 se
  matriculó el 60,6%, algo más que el promedio histórico).

**d) Escenario 1, seguimiento priorizado** (`escenario_seguimiento`):
- **Supuestos:** los asesores alcanzan a hacer seguimiento intensivo al 30% (125 inscritos).
- **Efecto de la llamada** (supuesto): efecto(p) = 0,10·4p(1−p).
  - Con p = 0,5 sube 10 puntos.
  - Con p = 0,9, solo 3,6 puntos: quien ya decidió casi no cambia.
- **Valor de cada matrícula adicional:** su precio neto del 1er semestre (tarifa oficial menos su beca).
- **Tres estrategias:**
  - **Al azar:** el valor esperado de elegir 125 al azar es 125 × el promedio: 10,1 matrículas, $42,1 M.
  - **Mayor probabilidad primero:** menos matrículas que al azar (7,5) y menos ingreso ($26,7 M). Ya se iban a
    matricular, y suelen tener beca, así que cada matrícula vale menos.
  - **Indecisos primero (modelo):** 12,3 matrículas y $53,6 M, es decir, 2,2 matrículas y $11,5 M más que al azar.
- **Por qué la ventaja creció:** con la tasa de 56,6% y el puntaje NLP, las probabilidades de 2027-1 se separan
  más (de 0,28 a 0,84 en promedio por quintil). Hay más "seguros" a los que no conviene llamar, y elegir bien a los
  indecisos gana más.
- **Sensibilidad:** con ±50%, el efecto de la llamada lleva las matrículas adicionales de 6,1 a 18,4, y la capacidad de
  seguimiento, de 6,2 a 18,0.
- **Sin costos:** no hay datos de cuánto cuesta el seguimiento, así que no se calcula un beneficio neto.

**e) Escenario 2, Expo Estudiantes:**
- En 2026-1 llegaron 74 inscritos por la Expo y se matricularon 29.
- **Con seguimiento priorizado** al 30% de los inscritos de la feria (22): se suman 2,2 matrículas esperadas (1,3 en
  2024-1 y 1,8 en 2025-1).
- No se calcula el costo por matriculado porque no hay datos de la inversión en el evento.
- **Por segmento** (`escenario2_segmentos_expo.csv`): el S1 (colegio privado, estrato más alto) convierte 51,6% en la
  Expo y el S3 (viven lejos del campus, estrato más bajo), 26,2%. Esa es la guía para elegir a qué colegios ir y qué
  ofrecer (transporte y FOES a los que viven lejos).

**f) Acciones por segmento** (`acciones_por_segmento`): para los 416 inscritos de 2027-1, por segmento:
- propensión media;
- % de indecisos (probabilidad entre 0,35 y 0,60);
- % lejos;
- % con beca;
- valor esperado por inscrito.

Reglas simples asignan la acción:
- muchos indecisos → prioridad de seguimiento;
- mayoría lejos → beneficio de transporte y FOES municipal;
- pocos con beca → informar requisitos (Saber 11 y la entrevista de Mi Vocación).

## 4. Decisiones y por qué
| Decisión | Por qué | Alternativa descartada |
|---|---|---|
| Sellar 2027-1 desde la Semana 1 | Es la única prueba que ninguna decisión pudo contaminar | Usar solo la prueba 2026-2 (ya se había mirado) |
| No cambiar el modelo tras ver 2027-1 | Cambiar después de ver la prueba sería elegir mirándola (aquí XGBoost quedó a la par: 34,1% frente a 33,9%, con menor AUC) | Cambiar de modelo según el resultado |
| Comparar contra la logística del Sprint 2 con su intervalo | Es el único modelo base del proyecto; una diferencia de 2 inscritos no prueba que un modelo sea mejor | Afirmar "mejora" sin intervalo |
| Valor esperado (probabilidad × valor) | Es la forma honesta de convertir probabilidades en matrículas y en ingreso | Contar solo "aciertos" |
| No calcular costos | El proyecto no tiene datos del costo del seguimiento ni de la inversión en eventos; inventarlos no es verificable | Suponer un costo por inscrito o por evento |
| Efecto de la llamada 4p(1−p) | Refleja que el seguimiento cambia la decisión de los indecisos, no la de quien ya decidió | Efecto constante (haría ganar a "mayor probabilidad primero", lo cual no es realista) |
| Comparar contra "al azar" | Es lo que hace la Universidad hoy sin modelo | Comparar contra "no hacer nada" (exagera el valor del modelo) |
| Sensibilidad ±50% | Los supuestos no están validados; hay que mostrar cuánto dependen las cifras de ellos | Presentar una sola cifra |

## 5. Qué es esencial y qué es opcional
| Componente | ¿Lo pidió el docente? | ¿Se puede quitar? | Qué se rompe si se quita | Recomendación |
|---|---|---|---|---|
| Prueba con la campaña 2027-1 sellada | Sí ("datos que nunca ha visto") | No | El entregable central | Conservar |
| Tabla por quintiles | No, pero muestra para qué sirve | Sí | Nada | Conservar: es el mejor argumento ante directivas |
| Escenario 1 (seguimiento) | Sí ("dinero o estudiantes") | No | El informe del Sprint 6 lo cita | Conservar |
| Escenario 2 (Expo Estudiantes) | Sí (ejemplo del docente) | No | El ejemplo pedido | Conservar |
| Sensibilidad (tornado) | No | Sí | Nada | Muy recomendado: protege ante "¿y si el supuesto está mal?" |
| Acciones por segmento | No | Sí | Nada (el informe la resume) | Conservar: une el k-means del Sprint 2 con el negocio |
| Comparación con XGBoost | No | Sí | Nada | Opcional |

## 6. Cómo comprobar que funciona
```bash
python sprints/sprint_5_validacion_impacto/ejecutar_sprint5.py
python -m pytest tests/test_sprint5_impacto.py -q
```
- **Salida esperada:** 33,9% de error en 2027-1 (35,3% la logística del Sprint 2, dentro del margen del azar); E1 de
  12,3 matrículas y $53,3 M de ingreso del 1er semestre (al azar, 10,2 y $42,1 M).
- **Las pruebas verifican:**
  - Que los cálculos son reproducibles.
  - Que no se calculan costos.
  - Que 4p(1−p) es máximo en 0,5.
  - Que ya no queda el escenario de beca.
  - Que el resultado sellado no se usa en los sprints 2 a 4.

## 7. Glosario
- **Datos no vistos (hold-out):** datos que no participaron en ninguna decisión del modelo.
- **Valor esperado:** probabilidad × valor, sumado sobre los casos; es el promedio que se obtendría si se repitiera
  muchas veces.
- **Quintil:** cada uno de 5 grupos del mismo tamaño ordenados por una variable.
- **Matriz de confusión:** tabla de aciertos y errores (falsos positivos y falsos negativos).
- **Bootstrap pareado:** se remuestrean los mismos inscritos para los dos modelos; así la diferencia de error no depende
  de qué inscritos cayeron en cada muestra.
- **Análisis de sensibilidad (tornado):** se mueve un supuesto a la vez y se ve cuánto cambia el resultado.
