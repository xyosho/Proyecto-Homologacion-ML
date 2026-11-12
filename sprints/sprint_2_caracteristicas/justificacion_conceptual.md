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

## 3. De variable cualitativa a cuantitativa: la entrevista de admisión
- La entrevista tiene **preguntas abiertas** ("¿Por qué quiere estudiar esta carrera?", "¿Por qué Unicervantes?"). Un
  modelo no puede leer esas respuestas tal cual.
- **Rúbrica:** el entrevistador califica cada sección de 1 (muy débil) a 5 (sobresaliente). Así una variable
  cualitativa se vuelve **ordinal** y comparable entre aspirantes:
  1. interés por el programa;
  2. historia de vida (cualidades, aspectos por mejorar, colegio, tiempo libre);
  3. interés por la universidad;
  4. conciencia social;
  5. expresión y actitud.
- **Índice vocacional = 25 × (promedio − 1)**, de 0 a 100. Calificar 1 en todo da 0; 3 en todo da 50; 5 en todo da 100.
  - Es una regla fija, no se aprende de los datos: no puede producir fuga.
  - Si no hubo entrevista queda vacío. En el modelo se pone 0 y la variable `entrevista_realizada` indica que no hubo
    entrevista.
- **Salud mental:** se pregunta en la entrevista, pero es un **dato sensible** (Ley 1581 de 2012, art. 5).
  - Usarla para predecir la matrícula podría discriminar, y exige autorización expresa.
  - Queda solo para Bienestar, en `entrevista_admision`, cerrada por RLS: la API no la deja leer.
  - No entra a ningún modelo.
- **Limitación:** no hay respuestas reales. Las calificaciones se simulan (supuesto S-46), coherentes con el puntaje
  vocacional que ya existía: su promedio redondeado es ese puntaje, el mismo que exige Mi Vocación (≥ 3).

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
  - Se probó k = 3 a 7. Las siluetas casi no cambian (0,18 a 0,19).
  - Regla: el menor k a menos de 0,01 de la mejor silueta, porque menos segmentos son más fáciles de usar. Dio
    **k = 5**, que además fue la mejor (0,193).
- La silueta baja indica que los aspirantes no forman grupos muy separados. Los segmentos son una forma útil de
  resumir perfiles, no "tipos" naturales.

## 5. La regresión logística, primer modelo del proyecto
- Modela el logaritmo de las odds de matricularse como una suma ponderada:
  log(p/(1 − p)) = β₀ + β₁x₁ + … + βₖxₖ. Despejando, p = 1/(1 + e^−(β₀ + Σβx)), siempre entre 0 y 1.
- Los β se eligen por **máxima verosimilitud**: los que hacen más probables los resultados observados.
- **e^β** es cuánto se multiplican las odds cuando la variable (estandarizada) sube una unidad. Por ejemplo, el
  descuento tiene β = 0,51: más beca, más probabilidad de matricularse.
- Las variables categóricas (canal, beca, programa…) se codifican con **one-hot**: una columna 0/1 por categoría. Así
  no se inventa un orden que no existe.
- En el Sprint 2 se usa **sin ajustar hiperparámetros** (C = 1, fijado antes de ver resultados). El ajuste y la
  comparación con Random Forest y XGBoost se hacen en el Sprint 3.
- **Error %:** inscritos mal clasificados al predecir "sí" cuando la probabilidad es ≥ 50%.
  - Validación 2026-1: 35,7%. Prueba 2026-2: 38,1%.
  - Decir siempre "no se matricula", la clase más frecuente, se equivoca en 42,5% y 44,5%.
- **AUC:** probabilidad de que un matriculado al azar reciba mayor probabilidad que un no matriculado al azar (0,676 en
  la prueba; 0,5 sería azar).
- **Brier:** promedio de (probabilidad − resultado)².

## Preguntas de control
1. Explique con un ejemplo qué es la fuga de datos y cómo la evita `ajustar_referencias`.
2. ¿Cómo se convierte la entrevista en el índice vocacional? ¿Por qué es una regla fija y no algo aprendido?
3. ¿Por qué la salud mental no entra al modelo?
4. Describa el algoritmo de k-means y explique por qué hay que estandarizar.
5. ¿Qué mide la silueta y por qué se eligió k = 5?
6. Escriba la fórmula de la regresión logística. ¿Qué significa un β positivo?
7. ¿Por qué se compara con decir siempre "no se matricula"?
