# Justificación conceptual — Sprint 3 (BORRADOR)

> ⚠️ **Borrador de apoyo.** Reescríbalo con sus propias palabras: en la sustentación le pueden preguntar "¿cómo funciona
> este algoritmo por dentro?".

## 1. Regresión logística
- Modela el logaritmo de las odds de matricularse como una suma ponderada: log(p/(1−p)) = β₀ + β₁x₁ + … + βₖxₖ.
  Despejando, p = 1/(1 + e^−(β₀ + Σβx)), una curva en forma de S que siempre da valores entre 0 y 1.
- Los β se eligen por **máxima verosimilitud**, es decir, los que hacen más probables los resultados observados. No
  hay fórmula cerrada: se resuelve con un método iterativo (Newton-Raphson o variantes).
- **Regularización L2** (parámetro C): se penaliza Σβ². Un C pequeño (0,01, el elegido) encoge los coeficientes y
  reduce el sobreajuste.
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
- La logística, con el término `icfes_al_cuadrado`, captura casi todo. Los árboles, con 1.800 datos, pagan su
  flexibilidad con más varianza (XGBoost quedó en 38,0% y Random Forest en 40,1%, frente a 37,8% de la logística
  ajustada).
- Además, la matrícula de estos datos se **simuló con un modelo logístico** (supuesto S-15): la logística tiene ventaja
  por construcción. Con datos reales podría ganar un árbol.
- No es un fracaso: el modelo avanzado se construyó, se comparó con evidencia y perdió. Elegir el simple cuando rinde
  igual es la **navaja de Occam**.

## 4. ¿El Sprint 3 mejora al Sprint 2?
- La logística del Sprint 2 (C = 1) y la ajustada (C = 0,01) se reentrenan con los mismos datos y se miden en los
  mismos 761 inscritos: 37,2% y 37,8% de error.
- La diferencia es de 0,7 puntos, unos **5 inscritos**. Para saber si es real se remuestrean los **mismos** inscritos
  1.000 veces y se recalcula la diferencia: el IC 95% va de −1,6 a +2,8 puntos. Como incluye el 0, **no se puede decir
  que uno sea mejor**: rinden igual.
- ¿Por qué no cambiar a C = 1 al ver que dio menos error en la prueba? Porque la prueba dejaría de ser una medición
  independiente: elegir mirándola infla el resultado (lección de H-48). C se eligió con la validación, antes.

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
  percentiles 2,5 y 97,5 dan el IC 95% (0,624 a 0,700).

## Preguntas de control
1. Escriba la fórmula de la regresión logística y explique qué significa un β positivo.
2. ¿Qué hace la regularización C y por qué un C pequeño puede mejorar la prueba?
3. Explique el bootstrap y el submuestreo de variables en Random Forest. ¿Qué problema resuelven?
4. ¿En qué se diferencia el boosting de XGBoost del bagging de Random Forest?
5. ¿Por qué la log-loss es mejor criterio de elección que el error %?
6. ¿Qué significa un AUC de 0,663 y su IC de 0,624 a 0,700?
7. El modelo ajustado no mejora a la logística del Sprint 2. ¿Cómo se comprueba que la diferencia es azar?
