# Justificación conceptual — Sprint 3 (BORRADOR)

> ⚠️ **Borrador de apoyo.** Reescríbalo con sus propias palabras: en la sustentación le pueden preguntar "¿cómo funciona
> este algoritmo por dentro?".

## 1. Regresión logística
- Modela el logaritmo de las odds de matricularse como una suma ponderada: log(p/(1−p)) = β₀ + β₁x₁ + … + βₖxₖ.
  Despejando, p = 1/(1 + e^−(β₀ + Σβx)), una curva en forma de S que siempre da valores entre 0 y 1.
- Los β se eligen por **máxima verosimilitud**, es decir, los que hacen más probables los resultados observados. No
  hay fórmula cerrada: se resuelve con un método iterativo (Newton-Raphson o variantes).
- **Regularización** (parámetro C y tipo): **L2** penaliza Σβ² y encoge todos los coeficientes; **L1** penaliza Σ|β| y
  puede dejar algunos en 0, es decir, elige variables. Un C pequeño regulariza más. Se probaron 8 combinaciones y la
  validación eligió **C = 1 con L1**.
- **El puntaje NLP del Sprint 2** entra como una variable más (`puntaje_vocacional_nlp`). Para saber cuánto aporta, la
  misma búsqueda se repite **sin** esa variable (fila de control).
- **Interpretación:** e^β es cuánto se multiplican las odds cuando la variable sube una unidad (estandarizada).

## 2. Árboles, Random Forest y XGBoost
- **Árbol de decisión:** hace la pregunta (variable y corte) que mejor separa matriculados de no matriculados, según
  la impureza de Gini 1 − Σp². Repite en cada rama.
  - Un árbol solo es inestable: con pocos datos distintos cambia mucho.
- **Random Forest (Breiman, 2001):**
  - Entrena 500 árboles. Cada uno ve una muestra **bootstrap** (con reemplazo) de los datos y, en cada corte, solo un
    subconjunto de variables.
  - La predicción es el promedio de los árboles. Promediar árboles poco correlacionados **reduce la varianza**.
- **XGBoost (Chen y Guestrin, 2016):**
  - Entrena árboles pequeños **en secuencia**. Cada árbol nuevo se ajusta al error (gradiente) que dejaron los
    anteriores, multiplicado por una tasa de aprendizaje (0,03).
  - Incluye regularización de los árboles. Reduce sobre todo el **sesgo**.

## 3. ¿Por qué ganó la regresión logística?
- Los árboles brillan cuando hay interacciones complejas y no linealidades. Aquí el resultado depende de pocos factores
  que se suman en la escala log-odds: beca, distancia, U invertida del ICFES, canal y entrevista.
- La logística, con el término `icfes_al_cuadrado`, captura casi todo. Los árboles, con cerca de 1.800 datos, pagan su
  flexibilidad con más varianza: en validación la logística con NLP tuvo la menor log-loss (0,6175, frente a 0,6227 de
  XGBoost, 0,6268 de Random Forest y 0,6353 de Poisson y binomial negativa). En la prueba, XGBoost quedó en 35,5% y
  Random Forest en 37,3%, frente a 32,7% de la logística con NLP.
- **Poisson y binomial negativa** usan μ = e^η y p = mín(μ, 1): ordenan bien (AUC 0,696 en la prueba), pero la probabilidad
  no tiene techo y hay que cortarla en 1, lo que las descalibra (log-loss 0,651 en la prueba). La binomial negativa
  estimó α ≈ 6 × 10⁻⁶ (Var = μ + αμ²): con una matrícula de 0 o 1 no hay sobredispersión y coincide con Poisson.
- Además, la matrícula de estos datos se **simuló con un modelo logístico** (supuesto S-15): la logística tiene ventaja
  por construcción. Con datos reales podría ganar un árbol.
- No es un fracaso: el modelo avanzado se construyó, se comparó con evidencia y perdió. Elegir el simple cuando rinde
  igual es la **navaja de Occam**.

## 4. ¿El Sprint 3 mejora al Sprint 2?
- La logística del Sprint 2 y la logística con NLP se reentrenan con los mismos datos y se miden en los mismos 761
  inscritos: 36,7% y 32,7% de error.
- La diferencia es de 3,9 puntos, unos **30 inscritos**. Para saber si es real se remuestrean los **mismos** inscritos
  1.000 veces y se recalcula la diferencia: el IC 95% va de −6,0 a −1,7 puntos. Como no incluye el 0, **la mejora no
  se explica por el azar**.
- **La fila de control** (logística ajustada sin NLP) da 35,2%: ajustar los hiperparámetros solo mejora poco. Lo que
  más baja el error es el puntaje NLP (de 35,2% a 32,7%; IC 95% de la diferencia: −4,5 a −0,4 puntos).
- ¿Por qué no cambiar de modelo al ver la prueba? Porque la prueba dejaría de ser una medición independiente: elegir
  mirándola infla el resultado. El modelo se eligió con la validación, antes.

## 5. Elegir y evaluar sin hacerse trampa
- **Tres conjuntos con funciones distintas:**
  - Entrenamiento: aprender.
  - Validación: elegir hiperparámetros y modelo.
  - Prueba: medir **una vez**.
  - Si se elige mirando la prueba, el error medido es optimista.
- **Partición temporal:** se respeta el orden del tiempo porque así se usará el modelo.
- **Log-loss** para elegir: −(1/n)Σ[y log p + (1−y) log(1−p)]. Premia probabilidades bien calibradas y castiga mucho
  equivocarse con seguridad. El error % solo mira si p ≥ 0,5.
- **AUC-ROC:** área bajo la curva de verdaderos positivos contra falsos positivos al mover el umbral. Equivale a la
  probabilidad de que un matriculado al azar tenga mayor puntaje que un no matriculado al azar.
- **Bootstrap:** se remuestrean los 761 inscritos de prueba 1.000 veces con reemplazo y se recalcula el AUC. Los
  percentiles 2,5 y 97,5 dan el IC 95% (0,661 a 0,736 para la logística con NLP).

## Preguntas de control
1. Escriba la fórmula de la regresión logística y explique qué significa un β positivo.
2. ¿En qué se diferencian las regularizaciones L1 y L2? ¿Qué hace el parámetro C?
3. Explique el bootstrap y el submuestreo de variables en Random Forest. ¿Qué problema resuelven?
4. ¿En qué se diferencia el boosting de XGBoost del bagging de Random Forest?
5. ¿Por qué la log-loss es mejor criterio de elección que el error %?
6. ¿Qué significa un AUC de 0,699 y su IC de 0,661 a 0,736?
7. ¿Para qué sirve la fila de control sin NLP? ¿Cómo se comprueba si una diferencia de error es azar?
