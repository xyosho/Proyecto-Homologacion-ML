# Sprint 5 — Resultados de validación e impacto

## 1. ¿Acierta con datos que nunca vio?

Se abrió el resultado de la campaña 2027-1 (416 inscritos, sellado desde la Semana 1). El modelo se equivocó en **33.9%** de los casos (IC 95%: 29.6%–38.7%) frente a 35.3% de la regresión logística del Sprint 2. Su AUC fue 0.697 (IC 95%: 0.644–0.744). La diferencia con la logística del Sprint 2 (-1,4 puntos) está dentro del margen del azar (IC 95%: -4,1 a 1,2): los dos rinden igual.

Lo más útil es el **orden**: en el 20% de inscritos con mayor probabilidad se matriculó el 80%, y en el 20% con menor probabilidad, el 29%.

## 2. Escenario 1 · ¿A quién llamar primero?

Con capacidad de seguimiento para 125 inscritos (30%):

| Estrategia | Matrículas adicionales | Ingreso 1er semestre |
|---|---|---|
| Al azar (sin modelo) | 10,2 | $42.090.889 |
| Mayor probabilidad primero | 7,5 | $25.659.015 |
| Indecisos primero (modelo) | 12,3 | $53.315.204 |

Priorizar a los indecisos con el modelo deja 2,1 matrículas y $11.224.315 más que llamar al azar en una sola campaña. Llamar primero a los de mayor probabilidad es lo peor: ellos se iban a matricular de todos modos. El supuesto que más mueve el resultado es **el efecto de la llamada**: con ±50%, las matrículas adicionales van de 6,1 a 18,4.

## 3. Escenario 2 · Expo Estudiantes

En la Expo de la campaña 2026-1 se inscribieron 74 aspirantes y se matricularon 30. Con seguimiento priorizado a 22 de ellos (30%), se esperan 2,2 matrículas más. No se calcula el costo por matriculado porque no hay datos de la inversión en el evento.

## 4. Acciones por segmento de mercado (campaña 2027-1)

| Segmento | Inscritos | Propensión media | Acción sugerida |
|---|---|---|---|
| S4: Aspirantes mayores, puntaje ICFES bajo | 35 | 62% | asegurar: proceso de matrícula ágil y recordatorio de las fechas de pago |
| S1: Colegio privado, estrato más alto | 152 | 64% | asegurar: proceso de matrícula ágil y recordatorio de las fechas de pago |
| S2: Colegio público, viven cerca del campus | 132 | 59% | asegurar: proceso de matrícula ágil y recordatorio de las fechas de pago |
| S3: Viven lejos del campus, estrato más bajo | 97 | 52% | asegurar: proceso de matrícula ágil y recordatorio de las fechas de pago; ofrecer el beneficio de transporte y revisar FOES de su municipio |

> Las cifras usan dos supuestos (la capacidad de seguimiento y el efecto de la llamada) y datos sintéticos; la sensibilidad muestra cómo cambian. El ingreso sale de las tarifas oficiales menos la beca de cada inscrito. No se incluyen costos porque no hay datos de ellos. Con datos reales de Admisiones, el mismo cálculo se repite.
