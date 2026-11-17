# Justificación conceptual — Sprint 5 (BORRADOR)

> ⚠️ **Borrador de apoyo.** Reescríbalo con sus propias palabras. La pregunta típica de la sustentación es: "¿de dónde
> salen esos millones?".

## 1. ¿Por qué un conjunto sellado?
- Cada vez que se mira un conjunto de datos para tomar una decisión (elegir variables, hiperparámetros o modelo), ese
  conjunto deja de ser "nuevo" para el modelo. El error medido ahí se vuelve optimista.
- La prueba 2026-2 se miró en el Sprint 3 para reportar el error final. Después el proyecto siguió cambiando, así que
  ya no es una prueba virgen.
- La campaña 2027-1 se selló cuando se generaron los datos (Semana 1). Ninguna decisión pudo depender de ella. Por eso
  su error (34,4%) es la mejor estimación de cómo funcionará el modelo en la siguiente campaña.
- Que se parezca al error de la prueba 2026-2 (34,2%) indica que **no hubo sobreajuste** al proceso de elección.
- En 2027-1 se matriculó el 60,6% (252 de 416). Es más que el 56,6% de la muestra de ejemplo (S-15), pero la binomial
  lo permite: z = 1,65, menor que 2.

## 2. Precisión, utilidad y orden
- **Un error del 34% no significa que el modelo no sirva:**
  - La Universidad no necesita adivinar uno por uno quién se matricula. Necesita **ordenar** a quién dedicarle el
    tiempo de los asesores y el presupuesto.
  - El AUC (0,676, frente a 0,657 de la logística del Sprint 2) mide justamente el orden. En el quintil superior se
    matricula el 78% y en el inferior, el 35%: más del doble.
  - En error individual el modelo mejora poco a la logística del Sprint 2 (34,4% frente a 37,3%), y esa diferencia
    cabe en el margen del azar (IC 95%: −5,8 a +0,2 puntos). XGBoost queda empatado (34,1%: falla en un inscrito
    menos). Su ventaja está en el orden y en que se puede explicar, no en acertar uno por uno.
- **Calibración:** que el 58% predicho signifique cerca de 58% real. En 2027-1 la probabilidad media fue 57,6% y la
  tasa real 60,6%. Con buena calibración, las probabilidades se pueden multiplicar por pesos.

## 3. Valor esperado
- **Definición:** el valor esperado de una decisión con resultado incierto es E[X] = Σ pᵢ·xᵢ.
- **Ejemplo:** llamar a un inscrito con p = 0,5 sube su probabilidad 10 puntos. Si su 1er semestre vale $4 M, el valor
  esperado de la llamada es 0,10 matrículas y 0,10 × $4 M = $400.000 de ingreso.
- Sumando sobre los 125 inscritos llamados (30% de 416) se obtienen las matrículas y el ingreso de la estrategia. **No
  es una promesa:** es el promedio que se obtendría si la campaña se repitiera muchas veces.
- No se resta un costo de la llamada porque el proyecto no tiene ese dato.

## 4. ¿Por qué el efecto de la llamada es 4p(1−p)?
- **La forma:** es una parábola que vale 0 en p = 0 y en p = 1, y 1 en p = 0,5.
- **La idea:** el seguimiento no convence a quien ya decidió que no, ni hace falta para quien ya decidió que sí. Cambia
  la decisión del **indeciso**.
- **Implicaciones:**
  - Ordenar por probabilidad (llamar a los "seguros") desperdicia llamadas: da 7,5 matrículas y $26,7 M, menos que
    llamar al azar (10,1 y $42,1 M).
  - El modelo sirve para **encontrar a los indecisos**: 12,3 matrículas y $53,6 M, es decir, 2,2 matrículas y $11,5 M
    más que al azar.
- **Es un supuesto.** En la vida real se mide con un experimento: llamar a la mitad de los indecisos al azar y
  comparar contra la otra mitad.

## 5. Matrículas extra en una feria (Escenario 2)
- Expo Estudiantes 2026-1: llegaron 74 inscritos por la feria y se matricularon 29.
- Con seguimiento priorizado a 22 de ellos (30%) se esperan 2,2 matrículas más.
- La feria trae inscritos con menor tasa (39% en 2026-1, frente a 56,6% de la muestra): allí hay más indecisos, y es
  donde el seguimiento priorizado ayuda más.
- No se calcula el costo por matriculado de la feria porque no hay datos de la inversión en el evento.

## 6. Análisis de sensibilidad
- Cuando un resultado depende de supuestos no validados, se mueve cada supuesto (aquí ±50%) dejando los demás fijos.
- El **gráfico de tornado** ordena los supuestos de mayor a menor efecto: dice **qué hay que medir primero**.
- En el Escenario 1, las matrículas adicionales con el modelo (12,3):
  - con el efecto de la llamada ±50%, van de 6,1 a 18,4;
  - con la capacidad de seguimiento ±50%, van de 6,2 a 18,0.
- Antes de ampliar el seguimiento, un piloto debe medir el efecto real de la llamada.

## 7. Límites
- **Datos sintéticos:** las cifras ilustran el método, no son una promesa para la Universidad.
- **No es causal:** el modelo predice quién se matricula, pero no dice que la llamada cause la matrícula (eso es el
  supuesto del efecto de la llamada).
- **Una sola campaña de prueba:** el IC del error (30,0% a 38,9%) es ancho. Con más campañas se reduce.

## Preguntas de control
1. ¿Qué es un conjunto de prueba "contaminado"? ¿Por qué 2027-1 no lo está?
2. Calcule a mano el valor esperado de llamar a un inscrito con p = 0,3 cuyo 1er semestre vale $3 M.
3. ¿Por qué 4p(1−p) hace que llamar primero a los de mayor probabilidad sea peor que llamar al azar en ingreso?
4. ¿Por qué el seguimiento priorizado suma más matrículas en la feria que en otros canales?
5. ¿Qué es un gráfico de tornado y qué le dice a la directiva?
6. ¿Qué experimento propondría para medir el efecto real de la llamada?
