# ¿Por qué el modelo toma sus decisiones? (explicación para directivas)

El modelo estima, para cada inscrito, la probabilidad de que pague la matrícula. Con la técnica SHAP se mide cuánto aporta cada factor a esa probabilidad, sumando o restando frente a un inscrito promedio.

## Lo que más pesa

1. **Beca y precio** — 20% del peso total de las explicaciones.
2. **Entrevista vocacional** — 17% del peso total de las explicaciones.
3. **Canal de captación** — 12% del peso total de las explicaciones.
4. **Puntaje Saber 11** — 9% del peso total de las explicaciones.
5. **Distancia al campus** — 8% del peso total de las explicaciones.

El modelo le da **6.7 veces más peso al puntaje Saber 11 que a la edad** del aspirante.

## ¿Tiene sentido para la Universidad?

- ✅ Más descuento → más probabilidad de matrícula. (correlación entre descuento y su contribución SHAP (con el valor neto) > 0)
- ✅ Las becas pesan a favor frente a no tener beca. (contribución media de la beca: MI_VOCACION +0.39, NINGUNA -0.48, SABER_11 +0.46)
- ✅ Más distancia → menos probabilidad. (correlación entre distancia y su contribución < 0)
- ✅ Saber 11 en U invertida: los puntajes muy altos tienen más opciones y se matriculan menos. (contribución media por banda: < 230 -0.41, 230-289 +0.12, 290-329 +0.12, ≥ 330 -0.24)
- ✅ La entrevista vocacional pesa a favor. (contribución media del concepto con entrevista +0.09 vs. sin entrevista -0.71)
- ✅ Más vocación en sus palabras (puntaje NLP) → más probabilidad. (correlación entre el puntaje NLP y su contribución, entre los entrevistados, > 0)
- ✅ El género NO domina las decisiones. (puesto 16 de 16; importancia 0.004 vs. 0.445 del primero)
- ✅ Paridad por género: el modelo no crea una brecha que no exista en los datos. (brecha predicha F-M 0.007 vs. brecha real 0.007)

## ¿El modelo encontró las causas reales?

Como los datos son sintéticos, conocemos los efectos verdaderos con los que se generaron. La explicación SHAP recupera **9 de 10** efectos:

- ✅ Descuento (beca): verdadero positivo (β = 3.0); según el modelo, positivo.
- ✅ Distancia al campus: verdadero negativo (β = -0.35); según el modelo, negativo.
- ✅ Saber 11 (término cuadrático): verdadero U invertida (β = -0.25); según el modelo, U invertida.
- ✅ Entrevista vocacional: verdadero positivo (β = 0.6); según el modelo, positivo.
- ✅ Apoyo FOES: verdadero positivo (β = 0.5); según el modelo, positivo.
- ✅ Programa SSIA: verdadero positivo (β = 0.1); según el modelo, positivo.
- ✅ Ingreso a mitad de año: verdadero negativo (β = -0.1); según el modelo, negativo.
- ✅ Canal (orden de los 8 canales): verdadero inmersión > referido > campus day/convenio > web > redes > llamada > expo; según el modelo, correlación de Spearman con el orden real = 0.97.
- ⚠️ Estrato (orden de los 6 estratos): verdadero estrato 1 el más bajo; 4 el más alto; según el modelo, correlación de Spearman con el orden real = 0.32.
- ✅ Género (sin efecto real): verdadero ninguno (β = 0); según el modelo, importancia 0.004 log-odds.

Los efectos que no recupera son pequeños, tienen pocos casos (con 2.575 inscritos no se distinguen del azar) o son asociaciones: el modelo le da peso a algo que en el generador no causa la matrícula porque va de la mano con otras variables. Lección: una explicación muestra lo que el modelo aprendió, no garantiza la causa.

## Un chequeo independiente

Al desordenar cada factor en los inscritos de 2026-2, el que más hace caer la exactitud del modelo es **Entrevista vocacional** (el AUC cae 0.072), seguido de **Beca y precio**. Los dos están entre los tres primeros de SHAP.

## Tres inscritos de la campaña 2027-1

- Propensión **ALTA** (inscrito 2033, 84%): SHAP señala Colegio de procedencia | Beca y precio | Entrevista vocacional; LIME, puntaje_vocacional_nlp > 3.95 | aplica_icetex <= 0.00 | apoyo_foes <= 0.00.
- Propensión **MEDIA** (inscrito 2162, 62%): SHAP señala Beca y precio | Canal de captación | Distancia al campus; LIME, 3.21 < puntaje_vocacional_nlp <= 3.95 | canal=INMERSION | apoyo_foes <= 0.00.
- Propensión **BAJA** (inscrito 1472, 32%): SHAP señala Beca y precio | Puntaje Saber 11 | Distancia al campus; LIME, puntaje_vocacional <= 2.00 | apoyo_foes <= 0.00 | aplica_icetex <= 0.00.

> Recordatorio: el resultado de matrícula y las notas son sintéticos. Con datos reales de Admisiones, este análisis se repite sin cambios y puede mostrar otros pesos.
