# Sprint 4 — Machine Learning explicable

**Proyecto:** Modelo Predictivo de Segmentación de Mercado y Propensión a la Matrícula · Unicervantes
**Entrega:** jueves 12 de noviembre de 2026 · Homologación de Data Mining y Machine Learning

> **Entregable de la Semana 4:** entregar un análisis que responda a la pregunta "¿Por qué el modelo toma sus
> decisiones?". Debe usar herramientas (como SHAP o LIME) para mostrar, por ejemplo, que el modelo le da más peso al
> puntaje ICFES que a la edad del aspirante, con una explicación en español sencillo de por qué eso tiene sentido para
> la Universidad.

Se explica el modelo de matrícula elegido en el Sprint 3 (regresión logística con el puntaje NLP de la entrevista) y,
para comparar, XGBoost.

## Respuesta corta
**Lo que más pesa en la probabilidad de matrícula:**

| Factor | Peso en las decisiones |
|---|---|
| Beca y precio | 20,5% |
| Entrevista vocacional (puntaje del entrevistador y puntaje NLP de sus palabras) | 17,2% |
| Canal de captación | 12,4% |
| Puntaje Saber 11 (en U invertida) | 8,8% |
| Distancia al campus (por vías, desde su dirección) | 7,7% |
| Colegio de procedencia | 7,2% |
| Descuento institucional (nuevo) | 4,0% |
| Crédito ICETEX (nuevo) | 3,8% |

- El modelo le da **6,7 veces más peso al Saber 11 que a la edad**.
- El género ocupa el último lugar (16 de 16) y no crea diferencias entre hombres y mujeres (brecha predicha 0,007
  frente a 0,007 real).
- Cumple **8 de 8** chequeos de coherencia (incluida la equidad por género).
- Recupera **9 de 10** efectos verdaderos del generador de datos. Falla en el orden del estrato: hay pocos casos en
  estratos 5 y 6, y el estrato va de la mano con el colegio, la distancia y el segmento.

**¿Por qué tiene sentido para la Universidad?**
- **Beca y precio:** lo que más decide es cuánto le cuesta el semestre; una beca baja el precio y sube la matrícula.
- **Entrevista vocacional:** quien muestra en sus palabras un interés claro por la carrera y por la Universidad se
  compromete más.
- **Saber 11 en U invertida:** los puntajes medios se matriculan más; los muy altos tienen otras opciones y se van.
- **Distancia:** vivir lejos cuesta tiempo y dinero.
- **Canal:** los referidos y la inmersión llegan más convencidos que quienes llegan por ferias o redes sociales.

La explicación completa para directivas está en
[`resultados/explicacion_para_directivas.md`](sprints/sprint_4_explicabilidad/resultados/explicacion_para_directivas.md).

## Qué se entrega
| Entregable | Dónde |
|---|---|
| Importancia SHAP por concepto (modelo elegido y XGBoost) | [`importancia_shap_conceptos.csv`](sprints/sprint_4_explicabilidad/resultados/importancia_shap_conceptos.csv) · [`figuras/shap_importancia_conceptos.png`](sprints/sprint_4_explicabilidad/resultados/figuras/shap_importancia_conceptos.png) |
| Contribución por variable y dependencias | [`figuras/shap_puntos_variables.png`](sprints/sprint_4_explicabilidad/resultados/figuras/shap_puntos_variables.png) · [`figuras/shap_dependencias.png`](sprints/sprint_4_explicabilidad/resultados/figuras/shap_dependencias.png) |
| Tres inscritos explicados con SHAP y LIME | [`casos_shap_vs_lime.csv`](sprints/sprint_4_explicabilidad/resultados/casos_shap_vs_lime.csv) · [`figuras/casos_shap_vs_lime.png`](sprints/sprint_4_explicabilidad/resultados/figuras/casos_shap_vs_lime.png) |
| Importancia por permutación (chequeo independiente) | [`importancia_permutacion.csv`](sprints/sprint_4_explicabilidad/resultados/importancia_permutacion.csv) |
| Chequeos de coherencia y equidad | [`coherencia_reglas_negocio.csv`](sprints/sprint_4_explicabilidad/resultados/coherencia_reglas_negocio.csv) |
| Comparación con los efectos verdaderos | [`comparacion_con_efectos_verdaderos.csv`](sprints/sprint_4_explicabilidad/resultados/comparacion_con_efectos_verdaderos.csv) |
| Top 3 factores por inscrito (bloque 4 del tablero) | [`explicacion_prediccion.csv`](sprints/sprint_4_explicabilidad/resultados/explicacion_prediccion.csv) · tabla `explicacion_prediccion` en Supabase |
| Cuaderno para Google Colab | [`sprint4_explicabilidad_colab.ipynb`](sprint4_explicabilidad_colab.ipynb) |
| Cuaderno local (ejecutado, con sus salidas) | [`sprint4_explicabilidad_local.ipynb`](sprint4_explicabilidad_local.ipynb) |
| Script que genera tablas, figuras y el texto para directivas | [`sprints/sprint_4_explicabilidad/ejecutar_sprint4.py`](sprints/sprint_4_explicabilidad/ejecutar_sprint4.py) |
| Justificación conceptual | [`justificacion_conceptual.md`](sprints/sprint_4_explicabilidad/justificacion_conceptual.md) |

## Cómo funciona
- **SHAP** reparte la predicción de cada inscrito entre sus variables, como un reparto justo entre jugadores (valores
  de Shapley). Para un inscrito: log-odds predicho = valor base + suma de las contribuciones de sus variables. En la
  regresión logística es exacto.
- Las 28 variables se agrupan en **16 conceptos de negocio** (por ejemplo, la beca, el descuento y el valor neto forman
  "Beca y precio"; la entrevista realizada, el puntaje del entrevistador y el puntaje NLP forman "Entrevista
  vocacional"), porque las contribuciones SHAP se pueden sumar.
- **LIME** ajusta un modelo lineal sencillo alrededor de un solo inscrito. Si SHAP y LIME señalan los mismos factores,
  la explicación es más confiable.
- La **importancia por permutación** desordena cada concepto en los inscritos de 2026-2 y mide cuánto cae el AUC: no
  usa SHAP, por eso sirve de chequeo independiente.

## Cómo ejecutarlo
### En Google Colab
1. Abra [`sprint4_explicabilidad_colab.ipynb`](sprint4_explicabilidad_colab.ipynb) con el botón **Open in Colab**.
2. En el panel **Secretos** (icono de llave) cree `SUPABASE_URL` y `SUPABASE_KEY` (la clave **publicable**, nunca la
   secreta) y active el acceso del cuaderno.
   **Sin clave** no hay que subir nada: el cuaderno lee `data/processed` de esta rama en GitHub y dice de dónde
   salieron los datos.
3. *Entorno de ejecución → Ejecutar todas.* El cuaderno instala las librerías, escribe en Colab una copia de los
   módulos de `src/` y reentrena los modelos del Sprint 3 con sus hiperparámetros (mismo resultado que los guardados).

### En el computador
```bash
python -m venv .venv
.venv\Scripts\activate            # Windows (en Linux o Mac: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env             # y escriba ahí SUPABASE_URL y SUPABASE_KEY (clave publicable)
python sprints/sprint_4_explicabilidad/ejecutar_sprint4.py
```
- Sin `.env`, o con `--local`, los datos se leen de `data/processed/` (las mismas tablas planas que están en Supabase).
- Usa los modelos del Sprint 3 de `sprints/sprint_3_modelado/modelos/` y guarda todo en
  `sprints/sprint_4_explicabilidad/resultados/`.
- También puede abrir [`sprint4_explicabilidad_local.ipynb`](sprint4_explicabilidad_local.ipynb) en Jupyter o VS Code.

## Estructura
```
README.md
sprint4_explicabilidad_colab.ipynb       cuaderno para Google Colab
sprint4_explicabilidad_local.ipynb       cuaderno local (ejecutado)
sprints/sprint_4_explicabilidad/
  ejecutar_sprint4.py                    SHAP, LIME, permutación, coherencia y texto para directivas
  justificacion_conceptual.md            la teoría de SHAP y LIME
  resultados/                            tablas, figuras y explicaciones de la última ejecución
sprints/sprint_3_modelado/modelos/       modelos del Sprint 3 que se explican
src/
  comun.py                               rutas y lectura de la configuración
  conexion_supabase.py                   conexión segura (clave publicable, solo lectura)
  datos.py                               lee las tablas planas de Supabase o de data/processed
  nlp_vocacion.py                        modelo NLP de la entrevista (TF-IDF + Ridge)
  caracteristicas.py                     las columnas nuevas del Sprint 2 y k-means
  modelado.py                            modelos y métricas
  flujo.py                               paso común: cargar y construir las características
  explicabilidad.py                      SHAP, LIME, conceptos de negocio y chequeos
config/reglas_negocio.yaml               tarifas, becas, particiones, NLP y parámetros
data/processed/                          dataset_matricula.csv y dataset_entrevista.csv (respaldo local)
requirements.txt · .env.example · .gitignore
```

## Preguntas de control para practicar
1. ¿Qué es un valor de Shapley? ¿Por qué se dice que reparte la predicción de forma "justa"?
2. ¿Por qué se pueden sumar las contribuciones de la beca, el descuento y el valor neto en un solo concepto?
3. ¿En qué se diferencia LIME de SHAP?
4. ¿Por qué el puntaje Saber 11 tiene forma de U invertida? ¿Tiene sentido para la Universidad?
5. ¿Cómo se comprobó que el género no domina las decisiones?
6. Si SHAP muestra que una variable pesa, ¿significa que la causa? Use el caso del estrato.

## Seguridad y datos
- Las credenciales nunca se escriben en el código: viven en `.env` (excluido por `.gitignore`) o en los Secretos de
  Colab. La clave publicable solo puede **leer** las tablas planas (políticas RLS de Supabase).
- La base es **sintética anclada a datos reales de Colombia**: registros anónimos del Saber 11 (ICFES), direcciones
  de Catastro Bogotá y del DANE, y tarifas y becas oficiales de Unicervantes. La matrícula (Bernoulli con p = 43/76,
  supuesto S-15), las notas del colegio y la entrevista se simulan con supuestos documentados. Ningún dato identifica
  a una persona real (Ley 1581 de 2012). La salud mental no se publica ni entra al modelo.
