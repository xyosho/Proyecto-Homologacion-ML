# Proyecto-Homologacion-ML

**Modelo Predictivo de Segmentación de Mercado y Propensión a la Matrícula — Unicervantes**

Proyecto de homologación de Data Mining y Machine Learning. El objetivo es predecir qué aspirantes a
**Ingeniería en Analítica de Datos (AD)** e **Ingeniería en Sistemas de Software e IA (SSIA)** pagarán la matrícula,
para que Admisiones y Mercadeo prioricen su esfuerzo. El trabajo se organiza en 6 sprints semanales; esta rama
contiene el **Sprint 1**.

## Sprint 1 — Conexión segura, dataset plano y EDA inicial
| # | Pedido del docente | Dónde está |
|---|---|---|
| 1 | Conexión funcional entre Python y Supabase, con las credenciales fuera del código (`.env` o Secretos de Colab) | `src/conexion_supabase.py` · sección 1 de los cuadernos |
| 2 | Un único dataset plano (capa OLAP) con las variables para predecir la matrícula | Tabla `dataset_matricula` en Supabase · `sql/05_dataset_matricula.sql` · `docs/diccionario_dataset_matricula.md` |
| 3 | Inicio del EDA: estadística descriptiva, distribuciones y tratamiento preliminar de nulos | Secciones 2 y 3 de los cuadernos |

**Cuadernos:**
- [`Sprint_01_conexion_dataset.ipynb`](Sprint_01_conexion_dataset.ipynb): versión para **Google Colab**.
  [![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/xyosho/Proyecto-Homologacion-ML/blob/Sprint-1/Sprint_01_conexion_dataset.ipynb)
- [`Sprint_01_conexion_dataset_local.ipynb`](Sprint_01_conexion_dataset_local.ipynb): versión para el computador
  (Jupyter o VS Code), ya ejecutada con sus resultados.

## Contenido de la rama
| Archivo | Qué es |
|---|---|
| `Sprint_01_conexion_dataset.ipynb` | Cuaderno de Colab: lee la URL y la clave desde los Secretos de Colab |
| `Sprint_01_conexion_dataset_local.ipynb` | Cuaderno local: lee la URL y la clave desde el archivo `.env` |
| `src/conexion_supabase.py` | Conexión segura de solo lectura: valida las credenciales, lee la tabla por páginas de 1.000 filas, espera como máximo 30 s y comprueba que la clave no pueda escribir |
| `sql/05_dataset_matricula.sql` | Definición de la tabla plana: una fila por inscrito, 48 columnas, construida desde las 25 tablas normalizadas (OLTP) |
| `sql/04_supabase_seguridad.sql` | Seguridad en Supabase: RLS en todas las tablas y una sola política de **solo lectura** sobre `dataset_matricula` |
| `docs/diccionario_dataset_matricula.md` | Qué significa cada columna, su rol (control, objetivo o predictor) y qué indica un valor vacío |
| `data/processed/dataset_matricula.csv` | Copia de respaldo del dataset (solo para trabajar sin conexión) |
| `.env.example` · `.gitignore` · `requirements.txt` | Plantilla de credenciales, exclusión de `.env` y librerías necesarias |

## Los datos
La Universidad aún no entrega su histórico, así que la base es **sintética pero anclada a datos reales de Colombia**:
- Los puntajes Saber 11, el colegio, el estrato, el género y la edad de cada aspirante son registros **reales y
  anónimos** del ICFES (datos abiertos).
- Cada inscrito tiene una **dirección real** asignada al azar: una placa de Catastro Bogotá en una manzana de su mismo
  estrato (SDP) o una dirección del DANE en Sabana Centro. Desde ella se calcula la distancia al campus, en línea recta
  y por vías.
- Las tarifas y las becas (Saber 11 y Mi Vocación) son las oficiales de Unicervantes.
- Nombres, proceso comercial, notas del colegio y resultado de matrícula son **simulados**, con supuestos documentados.

**`dataset_matricula`** (2.991 inscritos de 2024-1 a 2027-1):
- 2.575 con resultado (2024-1 a 2026-2): se matriculó el **45,6%** (1.173).
- 416 de la campaña 2027-1, sin resultado todavía: son los que el modelo predecirá.
- No incluye datos personales (nombres, documentos, contactos, dirección) ni variables que se conocen al matricularse
  (fuga de datos).
- **Vacíos con significado:** `puntaje_vocacional` (467, no hubo entrevista), `colegio_bilingue` (534) y
  `colegio_caracter` (122), estos dos porque el ICFES no los reporta. Se tratan en la sección 3.4 del cuaderno.

## Seguridad de las credenciales
- **Dónde viven:** la URL y la clave de Supabase están en `.env`, excluido por `.gitignore`, o en los **Secretos de
  Colab**. Nunca en el código ni en las salidas de los cuadernos.
- **Qué clave se usa:** la **publicable**, nunca la secreta (`service_role`). El código rechaza la clave secreta y la
  cadena de conexión del pooler.
- **Qué permite:** en Supabase, RLS cierra las 25 tablas de origen y solo permite **leer** `dataset_matricula`. Si la
  clave publicable se filtrara, solo serviría para leer este dataset anonimizado.

## Cómo ejecutarlo
**En Google Colab:**
1. Abra `Sprint_01_conexion_dataset.ipynb` con el botón de arriba.
2. En el panel **Secretos** (🔑) cree `SUPABASE_URL` y `SUPABASE_KEY` (clave publicable) y active **Acceso del
   notebook** en los dos.
3. Ejecute todas las celdas.

**En el computador:**
```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
```
Luego copie `.env.example` como `.env`, complete `SUPABASE_URL` y `SUPABASE_KEY`, y abra
`Sprint_01_conexion_dataset_local.ipynb`. Sin conexión, ponga `USAR_CSV_DE_RESPALDO = True` en la sección 1 para
usar la copia de `data/processed/`.

## Primeros hallazgos del EDA
- **Objetivo balanceado:** cerca de la mitad de los inscritos se matricula, con una tasa estable entre periodos.
- **Beca:** con beca se matricula entre el 53% y el 59%; sin beca, cerca del 33%.
- **Canal:** inmersión (≈ 61%) y referidos convierten más que ExpoEstudiantes, llamadas y redes sociales (≈ 32-39%).
- **Distancia por vías:** la tasa baja del 53% en el quintil más cercano al 36% en el más lejano.
- **Correlaciones bajas** (la mayor, la del descuento, ≈ 0,24): ninguna variable sola decide la matrícula. Por eso se
  necesita un modelo multivariado (sprints siguientes).

## Fuentes de datos
- ICFES, [Resultados únicos Saber 11](https://www.datos.gov.co/Educaci-n/Resultados-nicos-Saber-11/kgxf-xxbe) (CC BY-SA 4.0).
- Catastro Bogotá (UAECD), [Placa Domiciliaria](https://datosabiertos.bogota.gov.co/dataset/placa-domiciliaria), y SDP,
  [Estratificación por manzana](https://datosabiertos.bogota.gov.co/dataset/estratificacion-para-bogota) (CC BY 4.0).
- DANE, [Nivel de direcciones del MGN 2025](https://geoportal.dane.gov.co/mparcgis/rest/services/NIVEL_DE_DIRECCIONES/Serv_NivelDirecciones_2025/MapServer).
- Unicervantes, [Admisiones](https://unicervantes.edu.co/admisiones/) y
  [derechos pecuniarios 2026](https://unicervantes.edu.co/wp-content/uploads/2025/11/Derechos-Pecuniarios-1.pdf).

> Ningún dato identifica a una persona real (Ley 1581 de 2012).
