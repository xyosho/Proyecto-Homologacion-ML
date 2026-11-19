# Proyecto-Homologacion-ML

**Modelo Predictivo de Segmentación de Mercado y Propensión a la Matrícula — Unicervantes**

Proyecto de homologación de Data Mining y Machine Learning. El objetivo es predecir qué aspirantes a
**Ingeniería en Analítica de Datos (AD)** e **Ingeniería en Sistemas de Software e IA (SSIA)** pagarán la matrícula,
para que Admisiones y Mercadeo prioricen su esfuerzo. El trabajo se organiza en 6 sprints semanales; esta rama
contiene el **Sprint 1**.

## Sprint 1 — Conexión segura, dataset plano y EDA inicial
| # | Entregable | Dónde está |
|---|---|---|
| 1 | Conexión funcional entre Python y Supabase, con las credenciales fuera del código (`.env` o Secretos de Colab) | `src/conexion_supabase.py` · sección 1 de los cuadernos |
| 2 | Un único dataset plano (capa OLAP) con las variables para predecir la matrícula | Tabla `dataset_matricula` en Supabase · `sql/05_dataset_matricula.sql` · `docs/diccionario_dataset_matricula.md` |
| 3 | Inicio del EDA: estadística descriptiva, distribuciones y tratamiento preliminar de nulos | Secciones 2 y 3 de los cuadernos |

Además, la entrevista de admisión quedó en tablas relacionales y la matrícula se simuló como una variable de Bernoulli
con la tasa de una muestra de ejemplo (ver **Los datos**).

**Cuadernos:**
- [`Sprint_01_conexion_dataset.ipynb`](Sprint_01_conexion_dataset.ipynb): versión para **Google Colab**.
  [![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/xyosho/Proyecto-Homologacion-ML/blob/Sprint-1/Sprint_01_conexion_dataset.ipynb)
- [`Sprint_01_conexion_dataset_local.ipynb`](Sprint_01_conexion_dataset_local.ipynb): versión para el computador
  (Jupyter o VS Code), ya ejecutada con sus resultados.

## Contenido de la rama
| Archivo | Qué es |
|---|---|
| `Sprint_01_conexion_dataset.ipynb` | Cuaderno de Colab: lee la URL y la clave desde los Secretos de Colab; sin clave, lee los datos de esta rama en GitHub |
| `Sprint_01_conexion_dataset_local.ipynb` | Cuaderno local: lee la URL y la clave desde el archivo `.env` |
| `src/conexion_supabase.py` | Conexión segura de solo lectura: valida las credenciales, lee la tabla por páginas de 1.000 filas, espera como máximo 30 s y comprueba que la clave no pueda escribir |
| `sql/05_dataset_matricula.sql` | Definición de la tabla plana: una fila por inscrito, 49 columnas, construida desde las 27 tablas normalizadas (OLTP) |
| `sql/09_dataset_entrevista.sql` | Tabla plana de la entrevista: las respuestas abiertas unidas por sección, una fila por inscrito |
| `sql/04_supabase_seguridad.sql` | Seguridad en Supabase: RLS en todas las tablas y políticas de **solo lectura** sobre las tablas planas anonimizadas |
| `docs/diccionario_dataset_matricula.md` | Qué significa cada columna de `dataset_matricula` y `dataset_entrevista`, su rol (control, objetivo o predictor) y qué indica un valor vacío |
| `src/s01*`, `s02`, `s03`, `src/textos_entrevista.py`, `config/`, `reports/`, `tests/` | Generación y validación de los datos sintéticos: descarga de fuentes, generador con semilla fija, 73 reglas de negocio y sus pruebas |
| `data/processed/dataset_matricula.csv` · `dataset_entrevista.csv` | Copias de respaldo de las tablas planas (solo para trabajar sin conexión) |
| `.env.example` · `.gitignore` · `requirements.txt` | Plantilla de credenciales, exclusión de `.env` y librerías necesarias |

## Los datos
La Universidad aún no entrega su histórico, así que la base es **sintética pero anclada a datos reales de Colombia**:
- Los puntajes Saber 11, el colegio, el estrato, el género y la edad de cada aspirante son registros **reales y
  anónimos** del ICFES (datos abiertos).
- Cada inscrito tiene una **dirección real** asignada al azar: una placa de Catastro Bogotá en una manzana de su mismo
  estrato (SDP) o una dirección del DANE en Sabana Centro. Desde ella se calcula la distancia al campus, en línea recta
  y por vías.
- Las tarifas y las becas (Saber 11 y Mi Vocación) son las oficiales de Unicervantes.
- Nombres, proceso comercial, notas del colegio, respuestas de la entrevista y resultado de matrícula son
  **simulados**, con supuestos documentados.

**La matrícula como variable de Bernoulli.** Cada inscrito se matricula (1) o no (0). La tasa se toma de una muestra de
ejemplo (supuesto S-15): 43 matriculados de 76 aspirantes, p = 43/76 = 0,566 y q = 0,434. El generador calibra su
intercepto para que la tasa esperada sea p, igual en todos los periodos (la prueba chi-cuadrado de la muestra no
rechaza la homogeneidad: p = 0,17).

**`dataset_matricula`** (2.991 inscritos de 2024-1 a 2027-1, 49 columnas):
- 2.575 con resultado (2024-1 a 2026-2): se matriculó el **56,7%** (1.460). Cada periodo queda dentro de la banda del
  95% de la binomial alrededor de p (|z| < 2): de 53,8% en 2026-1 a 60,2% en 2025-1.
- 416 de la campaña 2027-1, sin resultado todavía: son los que el modelo predecirá.
- No incluye datos personales (nombres, documentos, contactos, dirección) ni variables que se conocen al matricularse
  (fuga de datos).
- **Vacíos con significado:** `puntaje_vocacional` (467, no hubo entrevista), `colegio_bilingue` (534) y
  `colegio_caracter` (122), estos dos porque el ICFES no los reporta, y `tipo_descuento` (vacío = sin descuento
  institucional, la mayoría). Se tratan en la sección 3.4 del cuaderno.

**La entrevista de admisión en tablas relacionales:**
- `pregunta_entrevista`: el catálogo de 13 preguntas abiertas en 3 secciones (interés por el programa académico 5,
  historia de vida 7 e interés por la universidad 1).
- `entrevista_admision`: una entrevista por cada inscrito que la presentó (2.524).
- `respuesta_entrevista`: una respuesta por pregunta y entrevista.
- `dataset_entrevista`: la tabla plana con el texto de cada sección por inscrito; es la entrada del modelo de lenguaje
  natural del Sprint 2.
- La sección de **salud mental** no se simula ni se publica: es un dato sensible (Ley 1581 de 2012).

## Seguridad de las credenciales
- **Dónde viven:** la URL y la clave de Supabase están en `.env`, excluido por `.gitignore`, o en los **Secretos de
  Colab**. Nunca en el código ni en las salidas de los cuadernos.
- **Qué clave se usa:** la **publicable**, nunca la secreta (`service_role`). El código rechaza la clave secreta y la
  cadena de conexión del pooler.
- **Qué permite:** en Supabase, RLS cierra las tablas de origen y solo permite **leer** las tablas planas anonimizadas,
  como `dataset_matricula` y `dataset_entrevista`. Si la clave publicable se filtrara, solo serviría para leer esos
  datos sin información personal.

## Cómo ejecutarlo
**En Google Colab:**
1. Abra `Sprint_01_conexion_dataset.ipynb` con el botón de arriba.
2. En el panel **Secretos** cree `SUPABASE_URL` y `SUPABASE_KEY` (clave publicable) y active **Acceso del
   notebook** en los dos.
   **Sin clave** no hay que subir nada: el cuaderno lee `data/processed` de esta rama en GitHub y dice de dónde
   salieron los datos.
3. Ejecute todas las celdas.

**En el computador:**
```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
```
Luego copie `.env.example` como `.env`, complete `SUPABASE_URL` y `SUPABASE_KEY`, y abra
`Sprint_01_conexion_dataset_local.ipynb`. Sin conexión a Supabase, el cuaderno usa solo las copias de
`data/processed/`.

## Primeros hallazgos del EDA
- **Objetivo balanceado:** se matricula el 56,7%, con una tasa estable entre periodos (54% a 60%).
- **Beca:** con beca se matricula entre el 67% y el 69%; sin beca, el 44%.
- **Descuento institucional e ICETEX:** con descuento se matricula el 69% (sin él, el 55%): quien lo tiene ya conoce
  la Universidad. Con crédito ICETEX (lo pide y cumple el mérito), el 67% frente al 56%.
- **Canal:** inmersión (71%) y referidos (67%) convierten más que ExpoEstudiantes (41%), llamadas (49%) y redes
  sociales (47%).
- **Distancia por vías:** la tasa baja del 63% en el quintil más cercano al 48% en el más lejano.
- **Correlaciones bajas** (la mayor, la del precio neto y el descuento, ≈ 0,26): ninguna variable sola decide la
  matrícula. Por eso se necesita un modelo multivariado (sprints siguientes).

## Fuentes de datos
- ICFES, [Resultados únicos Saber 11](https://www.datos.gov.co/Educaci-n/Resultados-nicos-Saber-11/kgxf-xxbe) (CC BY-SA 4.0).
- Catastro Bogotá (UAECD), [Placa Domiciliaria](https://datosabiertos.bogota.gov.co/dataset/placa-domiciliaria), y SDP,
  [Estratificación por manzana](https://datosabiertos.bogota.gov.co/dataset/estratificacion-para-bogota) (CC BY 4.0).
- DANE, [Nivel de direcciones del MGN 2025](https://geoportal.dane.gov.co/mparcgis/rest/services/NIVEL_DE_DIRECCIONES/Serv_NivelDirecciones_2025/MapServer).
- Unicervantes, [Admisiones](https://unicervantes.edu.co/admisiones/) y
  [derechos pecuniarios 2026](https://unicervantes.edu.co/wp-content/uploads/2025/11/Derechos-Pecuniarios-1.pdf).

> Ningún dato identifica a una persona real (Ley 1581 de 2012).
