# Sprint 2 — Ingeniería de características y regresión logística

**Proyecto:** Modelo Predictivo de Segmentación de Mercado y Propensión a la Matrícula · Unicervantes
**Entrega:** jueves 29 de octubre de 2026 · Homologación de Data Mining y Machine Learning

> **Pedido del docente (Semana 2):** entregar la misma tabla de datos con columnas nuevas y útiles (por ejemplo,
> "¿Aplica a Beca Mi Vocación? Sí/No" o `segmento_rendimiento_icfes`) y un primer cálculo que sirva de punto de
> comparación.

El proyecto predice **si el inscrito se matricula**. El modelo base es una **regresión logística**.

## Qué se entrega
| Entregable | Dónde |
|---|---|
| La tabla del Sprint 1 con **13 columnas nuevas** (2.991 inscritos) | Se construye al ejecutar el cuaderno o el script; se publica en Supabase como `dataset_caracteristicas` (solo lectura) · [`resultados/dataset_caracteristicas.xlsx`](sprints/sprint_2_caracteristicas/resultados/dataset_caracteristicas.xlsx) |
| La **entrevista de admisión convertida en números** con procesamiento de lenguaje natural (NLP): un puntaje vocacional de 1 a 5 desde las palabras del aspirante | Sección 2 del cuaderno · [`resultados/metricas_nlp_vocacion.json`](sprints/sprint_2_caracteristicas/resultados/metricas_nlp_vocacion.json) |
| Segmentación de mercado con **k-means** (4 segmentos con nombres en español sencillo) | Columna `segmento_mercado` · [`resultados/tabla_segmentos.csv`](sprints/sprint_2_caracteristicas/resultados/tabla_segmentos.csv) |
| **Regresión logística** (el modelo base) y su error | Sección 7 del cuaderno · [`resultados/metricas_logistica_sprint2.json`](sprints/sprint_2_caracteristicas/resultados/metricas_logistica_sprint2.json) |
| Cuaderno para Google Colab | [`sprint2_caracteristicas_colab.ipynb`](sprint2_caracteristicas_colab.ipynb) |
| Cuaderno local (ejecutado, con sus salidas) | [`sprint2_caracteristicas_local.ipynb`](sprint2_caracteristicas_local.ipynb) |
| Script que genera la tabla, el Excel, las gráficas y las métricas | [`sprints/sprint_2_caracteristicas/ejecutar_sprint2.py`](sprints/sprint_2_caracteristicas/ejecutar_sprint2.py) |
| Justificación conceptual | [`justificacion_conceptual.md`](sprints/sprint_2_caracteristicas/justificacion_conceptual.md) |
| Resultados de la última ejecución (tablas, métricas y figuras) | [`sprints/sprint_2_caracteristicas/resultados/`](sprints/sprint_2_caracteristicas/resultados) |

## La entrevista de admisión en números (NLP)
La entrevista tiene 13 preguntas abiertas en tres secciones. El modelo NLP lee las respuestas de cada sección y da un
**puntaje vocacional de 1 a 5** (`puntaje_vocacional_nlp`):

| Sección del formulario | Preguntas |
|---|---|
| Interés por el programa académico | 5 |
| Historia de vida (quién es, su familia, trabajo y financiación, cualidades, aspectos por mejorar, colegio, tiempo libre) | 7 |
| Interés por la universidad | 1 |

- **Cómo funciona:** TF-IDF por sección (palabras y pares de palabras; pesan más las que distinguen una respuesta de
  las demás) y una **regresión Ridge** que aprende a predecir el puntaje de 1 a 5 que dio el entrevistador. Se ajusta
  solo con las 1.097 entrevistas del entrenamiento.
- **Qué tan bien funciona (validación 2026-1, 429 entrevistas):** se equivoca en 0,66 puntos en promedio (frente a
  0,93 si se predijera siempre el promedio), ordena a los aspirantes como el entrevistador (Spearman 0,69) y acierta a
  menos de un punto en el 78%.
- **Sirve para la matrícula:** entre los entrevistados, se matricula el 47% del tercio con puntaje NLP más bajo, el 62%
  del tercio medio y el 72% del más alto. Sin entrevista, el 36%.
- La sección de **salud mental** no entra al modelo ni al NLP: es un dato sensible (Ley 1581 de 2012, art. 5) y nunca
  se usa para decidir la admisión.
- No hay respuestas reales de entrevistas: se simulan con un banco de frases en español (supuesto S-48), sin nombres
  ni datos que identifiquen.

## Las 13 columnas nuevas
| Columna | Qué es |
|---|---|
| `particion` | Conjunto temporal: entrenamiento (2024-1 a 2025-2), validación (2026-1), prueba (2026-2) y campaña (2027-1) |
| `aplica_beca_saber11` | Sí/No: puntaje global Saber 11 ≥ 310 |
| `aplica_beca_mi_vocacion` | Sí/No: presentó la entrevista y su puntaje vocacional es ≥ 3 |
| `puntaje_vocacional_nlp` | Puntaje de 1 a 5 que el modelo NLP lee en las respuestas de la entrevista (vacío si no hubo entrevista) |
| `segmento_rendimiento_icfes` | Bajo (< 250), medio (250-309), alto (310-349) o superior (≥ 350) |
| `ahorro_beca_primer_semestre` | Cuánto le ahorra la beca en el 1er semestre (tarifa plena − precio neto), en COP |
| `log_distancia` | Logaritmo de la distancia por vías desde la dirección hasta el campus |
| `zona_distancia` | Cerca (hasta 10 km), media (10 a 20 km) o lejos (más de 20 km) |
| `rezago_saber11` | Tiempo entre el Saber 11 y la inscripción |
| `canal_agrupado` | Eventos, relacional o digital |
| `estrato_grupo` | Estratos 1 y 2, estrato 3 o estratos 4 a 6 |
| `colegio_privado` | 1 si el colegio es privado |
| `segmento_mercado` | Perfil del aspirante según k-means |

El precio que se usa es el **precio neto del 1er semestre** (`valor_neto_primer_semestre`, ya en la tabla del
Sprint 1). Todo lo que se aprende de los datos (escalas, el modelo NLP y los segmentos) se ajusta **solo con el
entrenamiento**, para que la validación y la prueba no "vean" el futuro (sin fuga de datos).

## Resultados
**Segmentos de mercado** (k-means sobre 5 variables estandarizadas: estrato, distancia por vías, Saber 11, edad y
colegio privado; k = 4 elegido por la silueta, 0,238):

| Segmento | Inscritos | % que se matriculó | Rasgo real |
|---|---|---|---|
| S1: Colegio privado, estrato más alto | 1.121 | 61,4% | 100% colegio privado · estrato 3,2 · ICFES 294 |
| S2: Colegio público, viven cerca del campus | 903 | 55,6% | 98% colegio público · 10,1 km por vías |
| S3: Viven lejos del campus, estrato más bajo | 679 | 49,0% | 28,7 km por vías · estrato 2,3 |
| S4: Aspirantes mayores, puntaje ICFES bajo | 288 | 57,7% | 22,5 años · ICFES 260 |

Los nombres son relativos al promedio de todos los inscritos (ICFES 274, 15,6 km, 18,2 años, estrato 2,8). La silueta
es baja: los segmentos son perfiles útiles para Mercadeo, no grupos naturales.

**Regresión logística, el modelo base** (C = 1, sin ajuste de hiperparámetros, entrenada con 2024-1 a 2025-2):

| Periodo evaluado | Error | AUC |
|---|---|---|
| Validación (2026-1, 504 inscritos) | 35,5% | 0,703 |
| Prueba (2026-2, 761 inscritos) | 37,2% | 0,675 |

El AUC mide qué tan bien ordena a los inscritos (0,5 es azar). Este es el punto de comparación de los modelos del
Sprint 3.

## Cómo ejecutarlo
### En Google Colab
1. Abra [`sprint2_caracteristicas_colab.ipynb`](sprint2_caracteristicas_colab.ipynb) con el botón **Open in Colab**.
2. En el panel **Secretos** (icono de llave) cree `SUPABASE_URL` y `SUPABASE_KEY` (la clave **publicable**, nunca la
   secreta) y active el acceso del cuaderno.
   **Sin clave** no hay que subir nada: el cuaderno lee `data/processed` de esta rama en GitHub y dice de dónde
   salieron los datos.
3. *Entorno de ejecución → Ejecutar todas.* El cuaderno instala las librerías y escribe en Colab una copia de los
   módulos de `src/`, así que no necesita nada más del repositorio. Lee `dataset_matricula` y `dataset_entrevista`.

### En el computador
```bash
python -m venv .venv
.venv\Scripts\activate            # Windows (en Linux o Mac: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env             # y escriba ahí SUPABASE_URL y SUPABASE_KEY (clave publicable)
python sprints/sprint_2_caracteristicas/ejecutar_sprint2.py
```
- Sin `.env`, o con `--local`, los datos se leen de `data/processed/` (las mismas tablas planas que están en Supabase).
- El script guarda la tabla, el Excel, las gráficas y las métricas en `sprints/sprint_2_caracteristicas/resultados/`.
- También puede abrir [`sprint2_caracteristicas_local.ipynb`](sprint2_caracteristicas_local.ipynb) en Jupyter o VS Code.

## Estructura
```
README.md
sprint2_caracteristicas_colab.ipynb      cuaderno para Google Colab
sprint2_caracteristicas_local.ipynb      cuaderno local (ejecutado)
sprints/sprint_2_caracteristicas/
  ejecutar_sprint2.py                    genera tabla, Excel, gráficas y métricas
  justificacion_conceptual.md            la lógica de las columnas, el NLP, k-means y la regresión logística
  resultados/                            tabla, métricas y figuras de la última ejecución
src/
  comun.py                               rutas y lectura de la configuración
  conexion_supabase.py                   conexión segura (clave publicable, solo lectura)
  datos.py                               lee las tablas planas de Supabase o de data/processed
  nlp_vocacion.py                        modelo NLP de la entrevista (TF-IDF + Ridge)
  caracteristicas.py                     las 13 columnas nuevas y k-means
  modelado.py                            regresión logística y métricas
  flujo.py                               paso común: cargar y construir las características
  graficas_sprint2.py                    gráficas del sprint en español sencillo
config/reglas_negocio.yaml               tarifas, becas, particiones, NLP y parámetros
data/processed/                          dataset_matricula.csv y dataset_entrevista.csv (respaldo local)
requirements.txt · .env.example · .gitignore
```

## Seguridad y datos
- Las credenciales nunca se escriben en el código: viven en `.env` (excluido por `.gitignore`) o en los Secretos de
  Colab. La clave publicable solo puede **leer** las tablas planas (políticas RLS de Supabase).
- La base es **sintética anclada a datos reales de Colombia**: registros anónimos del Saber 11 (ICFES), direcciones
  de Catastro Bogotá y del DANE, y tarifas y becas oficiales de Unicervantes. La matrícula (Bernoulli con p = 43/76,
  supuesto S-15), las notas del colegio y la entrevista se simulan con supuestos documentados. Ningún dato identifica
  a una persona real (Ley 1581 de 2012).
