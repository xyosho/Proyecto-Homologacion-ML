# Sprint 3 — Modelado

**Proyecto:** Modelo Predictivo de Segmentación de Mercado y Propensión a la Matrícula · Unicervantes
**Entrega:** jueves 5 de noviembre de 2026 · Homologación de Data Mining y Machine Learning

> **Entregable de la Semana 3:** entregar un modelo de Machine Learning que ya haga predicciones (no tiene que ser
> perfecto, pero debe funcionar) y una tabla comparativa sencilla: "El cálculo de la Semana 2 tenía un error del X%,
> mientras que este modelo de la Semana 3 tiene un error del Y%".

El proyecto predice **si el inscrito se matricula**. La regresión logística del Sprint 2 se mejora con el **puntaje NLP
de la entrevista** (Sprint 2) y la búsqueda de hiperparámetros, y se compara con dos regresiones de conteo (**Poisson** y
**binomial negativa**) y con Random Forest y XGBoost.

## La frase pedida
**La regresión logística de la Semana 2 tenía un error del 36,7%, mientras que el modelo de la Semana 3 (regresión
logística con el puntaje NLP) tiene un error del 32,7%** en los 761 inscritos de 2026-2, que ningún modelo vio al
entrenar ni al elegirse. **Mejora 3,9 puntos, unos 30 inscritos** (IC 95% de la diferencia: −6,0 a −1,7 puntos): no se
explica por el azar.

| Modelo (prueba 2026-2) | Error % | AUC-ROC (IC 95%) | Brier | Log-loss |
|---|---|---|---|---|
| Regresión logística del Sprint 2 (C = 1) | 36,7% | 0,677 (0,638–0,714) | 0,227 | 0,647 |
| Logística ajustada sin NLP (fila de control) | 35,2% | 0,678 (0,641–0,716) | 0,225 | 0,644 |
| **Logística con NLP (elegida, C = 0,1)** | **32,7%** | **0,711 (0,675–0,746)** | **0,216** | **0,623** |
| XGBoost con NLP | 35,5% | 0,699 (0,662–0,733) | 0,219 | 0,628 |
| Random Forest con NLP | 37,3% | 0,680 (0,644–0,714) | 0,225 | 0,640 |
| Regresión de Poisson con NLP | 35,3% | 0,696 (0,659–0,732) | 0,221 | 0,651 |
| Regresión binomial negativa con NLP | 35,3% | 0,696 (0,659–0,732) | 0,221 | 0,651 |

**Las tres regresiones** usan la misma combinación lineal η = β₀ + xᵀβ:
- Logística: p = 1 / (1 + e^(−η)); la matrícula es Bernoulli.
- Poisson: μ = e^η y p = mín(μ, 1); varianza = μ.
- Binomial negativa (NB2): varianza = μ + αμ². Estimó α ≈ 6 × 10⁻⁶ (con datos de 0 o 1 no hay sobredispersión), así que
  coincide con Poisson.

- **Cómo se eligió:** con la log-loss de la validación 2026-1 (logística 0,6175; XGBoost 0,6227; Random Forest 0,6268;
  Poisson y binomial negativa 0,6353).
- **La fila de control** usa la misma búsqueda sin el puntaje NLP: ajustar los hiperparámetros solo mejora poco. Lo que
  más baja el error es el NLP (de 35,2% a 32,7%; IC 95% de la diferencia: −4,5 a −0,4 puntos).
- **Variables nuevas** (actualización de Admisiones): `tiene_descuento` (descuento institucional, tope del 50% con la
  beca) y `aplica_icetex` (pide el crédito ICETEX y cumple el mérito mínimo del municipio del colegio).

## Qué se entrega
| Entregable | Dónde |
|---|---|
| Regresión logística (del Sprint 2, de control y con NLP), Poisson, binomial negativa, Random Forest y XGBoost | Secciones 2 y 3 de los cuadernos |
| Modelos entrenados | [`sprints/sprint_3_modelado/modelos/`](sprints/sprint_3_modelado/modelos) |
| Tabla comparativa, búsqueda de hiperparámetros, métricas, figuras y predicciones | [`sprints/sprint_3_modelado/resultados/`](sprints/sprint_3_modelado/resultados) |
| Cuaderno para Google Colab | [`sprint3_modelado_colab.ipynb`](sprint3_modelado_colab.ipynb) |
| Cuaderno local (ejecutado, con sus salidas) | [`sprint3_modelado_local.ipynb`](sprint3_modelado_local.ipynb) |
| Script que entrena, compara y guarda modelos, tablas, figuras y predicciones | [`sprints/sprint_3_modelado/ejecutar_sprint3.py`](sprints/sprint_3_modelado/ejecutar_sprint3.py) |
| Justificación conceptual | [`sprints/sprint_3_modelado/justificacion_conceptual.md`](sprints/sprint_3_modelado/justificacion_conceptual.md) |

## Cómo se eligió el modelo (sin hacerse trampa)
| Conjunto | Periodos | Para qué |
|---|---|---|
| Entrenamiento | 2024-1 a 2025-2 | Aprender |
| Validación | 2026-1 (504 inscritos) | Elegir hiperparámetros y modelo, por **log-loss** |
| Prueba | 2026-2 (761 inscritos) | Medir **una sola vez** |

| Modelo | Combinaciones probadas | Log-loss en validación | AUC en validación |
|---|---|---|---|
| **Logística con NLP** | 8 (C y L1 o L2) | **0,6150** (C = 1, L1) | 0,729 |
| XGBoost con NLP | 12 | 0,6243 | 0,716 |
| Logística sin NLP (control) | 8 | 0,6310 | 0,703 |
| Random Forest con NLP | 16 | 0,6337 | 0,703 |

- Ganó la regresión logística con NLP: el resultado depende de pocos factores que se suman (beca, entrevista,
  distancia, la U invertida del ICFES y canal), y los árboles, con cerca de 1.800 datos, pagan su flexibilidad con más
  varianza.
- **XGBoost queda cerca** (a menos de un punto en la prueba) y todos los intervalos de confianza se cruzan. Se mantiene
  la logística porque se eligió con la validación, antes de ver la prueba, y porque su explicación con SHAP es exacta.
- La matrícula de estos datos se simuló con un modelo logístico (supuesto S-15), así que la logística tiene ventaja por
  construcción. Con el histórico real de Admisiones la comparación se repite sin cambios.
- El elegido se reentrena con todo el histórico (2.575 inscritos de 2024-1 a 2026-2) y es el que predice la campaña
  2027-1.

## Cómo ejecutarlo
### En Google Colab
1. Abra [`sprint3_modelado_colab.ipynb`](sprint3_modelado_colab.ipynb) con el botón **Open in Colab**.
2. En el panel **Secretos** (icono de llave) cree `SUPABASE_URL` y `SUPABASE_KEY` (la clave **publicable**, nunca la
   secreta) y active el acceso del cuaderno.
   **Sin clave** no hay que subir nada: el cuaderno lee `data/processed` de esta rama en GitHub y dice de dónde
   salieron los datos.
3. *Entorno de ejecución → Ejecutar todas.* El cuaderno instala las librerías y escribe en Colab una copia de los
   módulos de `src/`, así que no necesita nada más del repositorio. Entrena todo dentro (tarda unos minutos).

### En el computador
```bash
python -m venv .venv
.venv\Scripts\activate            # Windows (en Linux o Mac: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env             # y escriba ahí SUPABASE_URL y SUPABASE_KEY (clave publicable)
python sprints/sprint_3_modelado/ejecutar_sprint3.py
```
- Sin `.env`, o con `--local`, los datos se leen de `data/processed/` (las mismas tablas planas que están en Supabase).
- Guarda tablas, métricas, figuras y predicciones en `sprints/sprint_3_modelado/resultados/` y los modelos en
  `sprints/sprint_3_modelado/modelos/`.
- También puede abrir [`sprint3_modelado_local.ipynb`](sprint3_modelado_local.ipynb) en Jupyter o VS Code.

## Estructura
```
README.md
sprint3_modelado_colab.ipynb             cuaderno para Google Colab
sprint3_modelado_local.ipynb             cuaderno local (ejecutado)
sprints/sprint_3_modelado/
  ejecutar_sprint3.py                    entrena, compara y guarda modelos, tablas, figuras y predicciones
  justificacion_conceptual.md            la lógica matemática y estadística de los modelos
  modelos/                               modelos entrenados (.joblib) y su ficha (.json)
  resultados/                            tablas, métricas, figuras y predicciones de la última ejecución
src/
  comun.py                               rutas y lectura de la configuración
  conexion_supabase.py                   conexión segura (clave publicable, solo lectura)
  datos.py                               lee las tablas planas de Supabase o de data/processed
  nlp_vocacion.py                        modelo NLP de la entrevista (TF-IDF + Ridge)
  caracteristicas.py                     las columnas nuevas del Sprint 2 y k-means
  modelado.py                            regresión logística, Random Forest, XGBoost y métricas
  flujo.py                               paso común: cargar y construir las características
config/reglas_negocio.yaml               tarifas, becas, particiones, NLP y parámetros
data/processed/                          dataset_matricula.csv y dataset_entrevista.csv (respaldo local)
requirements.txt · .env.example · .gitignore
```

## Preguntas de control para practicar
1. ¿Por qué la regresión logística le ganó a Random Forest y a XGBoost? ¿Es un fracaso del "modelo avanzado"?
2. ¿Cómo funciona un Random Forest por dentro (bootstrap, árboles, votación)? ¿Y XGBoost (residuos, tasa de
   aprendizaje)?
3. ¿Qué es la log-loss y por qué se usó para elegir modelos en vez del error %?
4. ¿Por qué la prueba 2026-2 se usa una sola vez y no se cambia el modelo elegido al verla?
5. ¿Para qué sirve la fila de control sin NLP? ¿Qué dice sobre el aporte del puntaje NLP?
6. Si el modelo se equivoca en el 34% de los casos, ¿para qué le sirve a la Universidad?

## Seguridad y datos
- Las credenciales nunca se escriben en el código: viven en `.env` (excluido por `.gitignore`) o en los Secretos de
  Colab. La clave publicable solo puede **leer** las tablas planas (políticas RLS de Supabase).
- La base es **sintética anclada a datos reales de Colombia**: registros anónimos del Saber 11 (ICFES), direcciones
  de Catastro Bogotá y del DANE, y tarifas y becas oficiales de Unicervantes. La matrícula (Bernoulli con p = 43/76,
  supuesto S-15), las notas del colegio y la entrevista se simulan con supuestos documentados. Ningún dato identifica
  a una persona real (Ley 1581 de 2012).
