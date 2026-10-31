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
  flexibilidad con más varianza (XGBoost casi empató en error, 38,4% frente a 38,2%, pero con menor AUC).
- No es un fracaso: el modelo avanzado se construyó, se comparó con evidencia y perdió. Elegir el simple cuando rinde
  igual es la **navaja de Occam**.

## 4. Elegir y evaluar sin hacerse trampa
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
  percentiles 2,5 y 97,5 dan el IC 95% (0,624 a 0,699).

## 5. Objetivo 2 con pocos datos
- Con 417 becados de entrenamiento, separar otro periodo de validación dejaría muy pocos datos. Por eso se usa
  **validación cruzada estratificada de 5 pliegues**: cada becado se predice una vez con un modelo que no lo vio, y
  "estratificada" significa que cada pliegue conserva la proporción de pérdidas.
- Con 140 becados de prueba, el IC del AUC es ancho (0,59 a 0,77): el modelo ordena mejor que el azar, pero la cifra
  es incierta. Hay que comunicarlo: **con estos datos el modelo de beca es modesto**.
- **Certeza en el grupo de mayor riesgo:** si se marca al 10% más riesgoso, 79% de ellos sí pierde la beca, frente a
  57% de la tasa general. Esto equivale a la **precisión** en ese corte.
- **¿Por qué no cambiar al modelo que rindió mejor en la prueba?** Porque la prueba dejaría de ser una medición
  independiente: elegir mirándola infla el resultado (es la misma lección de H-48).

## Preguntas de control
1. Escriba la fórmula de la regresión logística y explique qué significa un β positivo.
2. ¿Qué hace la regularización C y por qué un C pequeño puede mejorar la prueba?
3. Explique el bootstrap y el submuestreo de variables en Random Forest. ¿Qué problema resuelven?
4. ¿En qué se diferencia el boosting de XGBoost del bagging de Random Forest?
5. ¿Por qué la log-loss es mejor criterio de elección que el error %?
6. ¿Qué significa un AUC de 0,663 y su IC de 0,624 a 0,699?
7. ¿Por qué validación cruzada en el objetivo 2? ¿Qué significa "estratificada"?
