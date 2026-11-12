# Justificación conceptual — Sprint 4 (BORRADOR)

> ⚠️ **Borrador de apoyo.** Reescríbalo con sus propias palabras. La pregunta típica de la sustentación es: "¿qué
> significa que el descuento tenga un valor SHAP de +0,4?".

## 1. Valores de Shapley
- **Origen:** la teoría de juegos cooperativos (Shapley, 1953). Varios jugadores producen juntos un resultado. ¿Cuánto
  le corresponde a cada uno?
- **La respuesta de Shapley:** el aporte **marginal** promedio de cada jugador, considerando todos los órdenes posibles
  en que pudieron unirse al equipo.
- **Es el único reparto que cumple estas propiedades:**
  - **Eficiencia:** los aportes suman el resultado total.
  - **Simetría:** dos jugadores que aportan lo mismo reciben lo mismo.
  - **Jugador nulo:** quien no aporta nada recibe 0.
  - **Aditividad:** el reparto de la suma de dos juegos es la suma de los repartos.

## 2. SHAP: Shapley aplicado a una predicción (Lundberg y Lee, 2017)
- **El "juego"** es la predicción de un inscrito y **los "jugadores"** son sus variables.
- **La contribución** de una variable es cuánto mueve la predicción frente al **valor base**, que es la predicción
  promedio de un grupo de referencia:

      log-odds del inscrito = valor base + φ(beca) + φ(distancia) + … + φ(género)

- **En una regresión logística** con variables independientes, el cálculo es exacto y sencillo: φⱼ = βⱼ·(xⱼ − x̄ⱼ).
  - Ejemplo: si la distancia tiene β < 0 y el inscrito vive más lejos que el promedio, φ es negativa y "le resta".
- **En árboles**, TreeSHAP calcula los valores exactos en tiempo polinomial recorriendo los caminos del árbol.
- **Por qué se pueden agrupar variables:** gracias a la propiedad de eficiencia, las contribuciones se suman. Por eso
  "Beca y precio" es la suma de las contribuciones de beca, descuento, valor neto y probabilidad de acceso.
- **La escala es log-odds**, no puntos porcentuales: +0,4 en log-odds lleva un 45% a cerca de 55%.

## 3. LIME (Ribeiro et al., 2016)
- **Idea:** cerca de un punto, cualquier modelo complejo se parece a uno lineal. LIME:
  1. Genera miles de "vecinos" simulados del inscrito (3.000 aquí).
  2. Le pide al modelo su predicción para cada vecino.
  3. Ajusta una regresión lineal ponderada (los vecinos más parecidos pesan más).
  4. Los coeficientes de esa regresión son la explicación.
- **Diferencia con SHAP:**
  - LIME mide el **efecto de cambiar** la variable alrededor del inscrito.
  - SHAP mide **cuánto aleja** la variable al inscrito del promedio.
  - Ejemplo del proyecto: "no vivir en un municipio con FOES" aparece entre lo primero en LIME (vivir en uno cambiaría
    la probabilidad), pero casi nada en SHAP (casi nadie vive en uno, así que no vivir en uno es lo normal).
- **Debilidades de LIME:** depende del muestreo aleatorio y de cómo se definen los vecinos, y no garantiza que las
  contribuciones sumen la predicción.

## 4. Importancia por permutación
- Si se desordena al azar una variable en los datos de prueba, el modelo pierde esa información. La caída de
  rendimiento (AUC) mide cuánto dependía de ella.
- No usa SHAP. Si las dos técnicas coinciden en lo importante, la conclusión es más confiable.

## 5. Límites: explicar no es demostrar causas
- SHAP explica **el modelo**, no el mundo. Si dos variables están correlacionadas, el modelo puede apoyarse en
  cualquiera de las dos.
- **Caso del proyecto:** en el generador el promedio del colegio **no** tiene efecto en la matrícula. Aun así, el modelo
  le da algo de peso, porque en los datos la matrícula sube del 39% al 50% del quintil más bajo al más alto del
  promedio: el promedio va de la mano con otras variables (Saber 11, beca).
- **Los efectos pequeños se mueven con la muestra:** el ingreso a mitad de año (β = −0,10) salía con el signo invertido
  en la versión anterior de los datos y ahora sale bien; la edad pesaba antes (asociación) y ahora casi nada. Con pocos
  datos, un efecto pequeño se confunde con el azar.
- **Por eso se comparó con el generador:** es la única forma de saber si la explicación encontró la causa. Con datos
  reales eso no existe; habría que hacer experimentos (por ejemplo, ofrecer el descuento al azar).

## 6. Coherencia y equidad
- Que el modelo sea coherente con las reglas de negocio (el descuento ayuda, la distancia resta) es condición para que
  las directivas confíen en él.
- **Equidad:** que el género no domine y que el modelo no **amplifique** la diferencia real entre grupos (paridad:
  brecha predicha 0,007 frente a real 0,006).

## Preguntas de control
1. Explique con un ejemplo de tres amigos que comparten un taxi cómo se reparte el costo según Shapley.
2. ¿Qué significa que el descuento tenga una contribución de +0,4 para un inscrito? ¿Frente a qué se compara?
3. ¿Por qué la contribución de "no vivir en un municipio con FOES" es casi 0 en SHAP pero alta en LIME?
4. ¿Por qué se pueden sumar contribuciones en conceptos? ¿Qué propiedad lo permite?
5. El modelo usa el promedio del colegio, pero el generador no tenía ese efecto en la matrícula. ¿Cómo lo explica?
6. ¿Qué es la paridad y por qué importa en un modelo de admisiones?
