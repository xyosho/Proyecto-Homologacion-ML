# Sprint 5 — Resultados de validación e impacto

## 1. ¿Acierta con datos que nunca vio?

Se abrió el resultado de la campaña 2027-1 (416 inscritos, sellado desde la Semana 1). El modelo se equivocó en **34.4%** de los casos (IC 95%: 30.0%–38.9%) frente a 37.3% de la regresión logística del Sprint 2. Su AUC fue 0.676 (IC 95%: 0.623–0.728). La diferencia con la logística del Sprint 2 (-2,9 puntos) está dentro del margen del azar (IC 95%: -5,8 a 0,2): los dos rinden igual.

Lo más útil es el **orden**: en el 20% de inscritos con mayor probabilidad se matriculó el 78%, y en el 20% con menor probabilidad, el 35%.

## 2. Escenario 1 · ¿A quién llamar primero?

Con capacidad de seguimiento para 125 inscritos (30%):

| Estrategia | Matrículas adicionales | Ingreso 1er semestre | Beneficio neto |
|---|---|---|---|
| Al azar (sin modelo) | 10.1 | $42.125.479 | $38.375.479 |
| Mayor probabilidad primero | 7.5 | $26.703.869 | $22.953.869 |
| Indecisos primero (modelo) | 12.3 | $53.592.488 | $49.842.488 |

Priorizar a los indecisos con el modelo genera $11.467.009 más que llamar al azar en una sola campaña. Llamar primero a los de mayor probabilidad es lo peor: ellos se iban a matricular de todos modos. El supuesto que más mueve el resultado es **el efecto de la llamada (S-38)**: con ±50% el beneficio neto va de $23.046.244 a $76.638.732.

## 3. Escenario 2 · ExpoEstudiantes

En la Expo de la campaña 2026-1 se matricularon 29 inscritos: cada uno costó $758.621 de la inversión del evento. Con seguimiento priorizado a los inscritos de la feria, se esperan 2.2 matrículas más y el costo baja a $726.638 por matriculado.

## 4. Acciones por segmento de mercado (campaña 2027-1)

| Segmento | Inscritos | Propensión media | Acción sugerida |
|---|---|---|---|
| S4: Aspirantes mayores, puntaje ICFES bajo | 35 | 62% | asegurar: proceso de matrícula ágil y recordatorio de las fechas de pago |
| S1: Colegio privado, estrato más alto | 152 | 62% | asegurar: proceso de matrícula ágil y recordatorio de las fechas de pago |
| S2: Colegio público, viven cerca del campus | 132 | 57% | asegurar: proceso de matrícula ágil y recordatorio de las fechas de pago |
| S3: Viven lejos del campus, estrato más bajo | 97 | 49% | ofrecer el beneficio de transporte y revisar FOES de su municipio |

> Todas las cifras en pesos usan supuestos (S-37 a S-39) y datos sintéticos; la sensibilidad muestra cómo cambian. Con datos reales de Admisiones y Mercadeo, el mismo cálculo se repite.
