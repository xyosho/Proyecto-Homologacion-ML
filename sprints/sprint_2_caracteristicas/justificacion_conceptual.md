# Justificación conceptual — Sprint 2 (BORRADOR)

> ⚠️ **Borrador de apoyo.** La evaluación exige que la justificación esté **escrita con sus propias palabras**. Úselo
> para estudiar, reproduzca los números con el código y reescríbalo.

## 1. ¿Por qué crear columnas nuevas?
Un modelo solo aprende de lo que ve. Si la información está escondida en reglas o combinaciones, conviene hacerla
explícita. Por ejemplo, saber si alguien "aplica a Mi Vocación" requiere combinar entrevista y puntaje vocacional. Las
columnas nuevas convierten el conocimiento del negocio (reglas de becas, tarifas, distancia, canales, entrevista) en
variables que el modelo puede usar y que una persona puede leer.

## 2. Partición temporal y fuga de datos
- El modelo se usará para predecir la próxima campaña con lo aprendido de las anteriores. Por eso los datos se parten
  **por tiempo**: entrenamiento (2024-1 a 2025-2), validación (2026-1), prueba (2026-2) y campaña (2027-1).
- **Fuga de datos:** usar, al aprender, información que no estaría disponible al predecir. Si las medias para
  estandarizar o los centros de k-means se calcularan con 2026-2, la prueba de 2026-2 dejaría de ser "futuro
  desconocido" y el error medido sería más bajo que el real.
- Por eso todo lo que se estima con datos se ajusta **solo** con el entrenamiento y luego se aplica igual a los demás
  conjuntos.

## 3. De variable cualitativa a cuantitativa: la entrevista con procesamiento de lenguaje natural (NLP)
- La entrevista tiene **13 preguntas abiertas** en tres secciones: interés por el programa académico (5), historia de
  vida (7) e interés por la universidad (1). Un modelo no puede leer esas respuestas tal cual.
- **El modelo NLP** (`src/nlp_vocacion.py`) convierte las palabras del aspirante en un **puntaje vocacional de 1 a 5**
  (`puntaje_vocacional_nlp`):
  1. **TF-IDF** por sección: cada palabra y cada par de palabras seguidas pesa más si aparece mucho en esa respuesta y
     poco en las demás (frecuencia sublineal y norma L2 por sección). Se aprendieron 1.817 términos.
  2. **Regresión Ridge** (α = 10, elegido con validación cruzada): aprende a predecir el puntaje de 1 a 5 que dio el
     entrevistador a partir de esos pesos. El resultado se recorta al rango de 1 a 5.
- **Sin fuga de datos:** se ajusta solo con las 1.097 entrevistas del entrenamiento; en esas filas el puntaje se predice
  fuera de pliegue (5 pliegues), para que el modelo de matrícula no herede sobreajuste.
- **Cómo le fue en validación (2026-1, 429 entrevistas):**
  - Se equivoca en 0,66 puntos en promedio, frente a 0,93 si se predijera siempre el promedio.
  - Ordena a los aspirantes como el entrevistador (Spearman 0,69) y acierta a menos de un punto en el 78%.
  - Solo con el puntaje NLP se ordena la matrícula con AUC 0,650, más que con el puntaje del entrevistador (0,596).
- Si no hubo entrevista queda vacío. En el modelo se pone 0 y la variable `entrevista_realizada` indica que no hubo
  entrevista.
- **Salud mental:** es un **dato sensible** (Ley 1581 de 2012, art. 5; Ley 1616 de 2013). No se simula, no entra al
  NLP ni a ningún modelo y nunca se usa para decidir la admisión.
- **Limitación:** no hay respuestas reales. Las respuestas se simulan con un banco de frases en español de tres niveles
  (supuesto S-48), sin nombres ni datos que identifiquen.

## 4. k-means y la segmentación de mercado
- **Algoritmo (Lloyd):**
  1. Elegir k centros iniciales.
  2. Asignar cada aspirante al centro más cercano (distancia euclidiana).
  3. Mover cada centro al promedio de sus aspirantes.
  4. Repetir los pasos 2 y 3 hasta que nada cambie.
- Minimiza la **inercia** (suma de distancias al cuadrado). Como el resultado depende del inicio, se repite 20 veces
  y se queda la mejor.
- **Estandarizar** es obligatorio: sin hacerlo, el Saber 11 (cientos de puntos) dominaría la distancia frente al
  estrato (1 a 6).
- **Silueta:** para cada punto, (b − a)/máx(a, b), donde a es la distancia media a su grupo y b la distancia al grupo
  vecino.
  - Se usan 5 variables estandarizadas: estrato, logaritmo de la distancia por vías, Saber 11, edad y colegio privado.
  - Se probó k = 3 a 7. Las siluetas casi no cambian (0,228 a 0,238).
  - Regla: el menor k a menos de 0,01 de la mejor silueta, porque menos segmentos son más fáciles de usar. Dio
    **k = 4**, que además fue la mejor (0,238); k = 3 quedó a 0,0103.
- La silueta baja indica que los aspirantes no forman grupos muy separados. Los segmentos son una forma útil de
  resumir perfiles, no "tipos" naturales.

## 5. La regresión logística, modelo base del proyecto
- Modela el logaritmo de las odds de matricularse como una suma ponderada:
  log(p/(1 − p)) = β₀ + β₁x₁ + … + βₖxₖ. Despejando, p = 1/(1 + e^−(β₀ + Σβx)), siempre entre 0 y 1.
- Los β se eligen por **máxima verosimilitud**: los que hacen más probables los resultados observados.
- **e^β** es cuánto se multiplican las odds cuando la variable (estandarizada) sube una unidad. Por ejemplo, el
  descuento tiene β positivo: más beca, más probabilidad de matricularse.
- Las variables categóricas (canal, beca, programa…) se codifican con **one-hot**: una columna 0/1 por categoría. Así
  no se inventa un orden que no existe.
- En el Sprint 2 se usa **sin ajustar hiperparámetros** (C = 1, fijado antes de ver resultados). El ajuste y la
  comparación con Random Forest y XGBoost se hacen en el Sprint 3.
- **Error %:** inscritos mal clasificados al predecir "sí" cuando la probabilidad es ≥ 50%. Validación 2026-1: 35,5%;
  prueba 2026-2: 37,2%.
- **AUC:** probabilidad de que un matriculado al azar reciba mayor probabilidad que un no matriculado al azar (0,675 en
  la prueba; 0,5 sería azar). Es la mejor señal de que el modelo aprendió algo: ordena a los inscritos.
- **Brier:** promedio de (probabilidad − resultado)².

## Preguntas de control
1. Explique con un ejemplo qué es la fuga de datos y cómo la evita `ajustar_referencias`.
2. ¿Cómo convierte el modelo NLP las respuestas en un puntaje de 1 a 5? ¿Por qué se ajusta solo con el entrenamiento?
3. ¿Por qué la salud mental no entra al modelo?
4. Describa el algoritmo de k-means y explique por qué hay que estandarizar.
5. ¿Qué mide la silueta y por qué se eligió k = 4?
6. Escriba la fórmula de la regresión logística. ¿Qué significa un β positivo?
7. ¿Qué significa un AUC de 0,675?
