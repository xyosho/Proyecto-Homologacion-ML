# Sprint 5 — Validación con datos no vistos e impacto comercial (Semana 5 · jueves 19-nov-2026)

**Proyecto:** Modelo Predictivo de Segmentación de Mercado y Propensión a la Matrícula · Unicervantes
**Entrega:** jueves 19 de noviembre de 2026 · Homologación de Data Mining y Machine Learning

## Lo que pidió el docente
> Probar el modelo con datos que nunca ha visto para demostrar que funciona en la vida real, y calcular cuánto dinero o
> cuántos estudiantes podría ahorrar o retener la Universidad con este modelo. Incluir escenarios de captación (por
> ejemplo ExpoEstudiantes).

## Respuesta corta
**1. Datos nunca vistos.** El resultado de la campaña 2027-1 (416 inscritos) estuvo **sellado desde la Semana 1** y se
abrió solo aquí:

| Modelo (campaña 2027-1) | Error % (IC 95%) | AUC-ROC (IC 95%) | Brier |
|---|---|---|---|
| Regresión logística del Sprint 2 (modelo base) | 37,3% (32,9–41,6) | 0,657 (0,603–0,707) | 0,224 |
| **Regresión logística con NLP (elegida)** | **34,4% (30,0–38,9)** | **0,676 (0,623–0,728)** | **0,220** |
| XGBoost | 34,1% (29,6–38,7) | 0,671 (0,617–0,722) | 0,220 |

- El error del modelo elegido es **parecido al de la prueba del Sprint 3 (34,2%)**: no estaba sobreajustado.
- Frente a la logística del Sprint 2, el error baja 2,9 puntos, pero la diferencia está dentro del margen del azar
  (IC 95%: −5,8 a +0,2 puntos): **todavía no se puede afirmar que sea mejor**.
- Lo útil es el **orden**: en el 20% con mayor probabilidad se matriculó el 78%; en el 20% con menor probabilidad,
  el 35%.

**2. Cuánto ahorra o retiene** (valor esperado con supuestos S-37 a S-39; datos sintéticos):

| Escenario | Con el modelo | Sin el modelo |
|---|---|---|
| E1 · Seguimiento a 125 inscritos de 2027-1 | 12,3 matrículas adicionales · **$49,8 M** netos | 10,1 · $38,4 M (al azar) |
| E2 · ExpoEstudiantes 2026-1 | $726.638 por matriculado | $758.621 por matriculado |

- **El valor del modelo en el seguimiento (E1):** +$11,5 M frente a llamar al azar en una sola campaña (cada matrícula
  vale su precio neto del 1er semestre).
- Llamar primero a los de mayor probabilidad es **lo peor**: ya se iban a matricular.
- El supuesto que más mueve E1 es el efecto de la llamada (S-38): con ±50%, el beneficio neto va de $23,0 M a $76,6 M.

## Lo que se entrega
| Entregable | Archivo |
|---|---|
| Prueba en la campaña 2027-1 | [`resultados/prueba_campana_2027_1.csv`](sprints/sprint_5_validacion_impacto/resultados/prueba_campana_2027_1.csv) · `prueba_campana_por_quintil.csv` · [`figuras/prueba_campana_2027_1.png`](sprints/sprint_5_validacion_impacto/resultados/figuras/prueba_campana_2027_1.png) |
| Escenario 1 (seguimiento) + sensibilidad | [`resultados/escenario1_seguimiento.csv`](sprints/sprint_5_validacion_impacto/resultados/escenario1_seguimiento.csv) · `escenario1_sensibilidad.csv` · [`figuras/escenario1_seguimiento.png`](sprints/sprint_5_validacion_impacto/resultados/figuras/escenario1_seguimiento.png) |
| Escenario 2 (ExpoEstudiantes) | [`resultados/escenario2_expo.csv`](sprints/sprint_5_validacion_impacto/resultados/escenario2_expo.csv) · `escenario2_segmentos_expo.csv` · [`figuras/escenario2_expo.png`](sprints/sprint_5_validacion_impacto/resultados/figuras/escenario2_expo.png) |
| Acciones por segmento de mercado | [`resultados/acciones_por_segmento.csv`](sprints/sprint_5_validacion_impacto/resultados/acciones_por_segmento.csv) |
| Resumen en lenguaje de negocio | [`resultados/resumen_impacto.md`](sprints/sprint_5_validacion_impacto/resultados/resumen_impacto.md) |
| Cuaderno explicado | [`sprint5_validacion_impacto_local.ipynb`](sprint5_validacion_impacto_local.ipynb) · [`sprint5_validacion_impacto_colab.ipynb`](sprint5_validacion_impacto_colab.ipynb) |
| Guía y justificación | [`GUIA.md`](sprints/sprint_5_validacion_impacto/GUIA.md) · [`justificacion_conceptual.md`](sprints/sprint_5_validacion_impacto/justificacion_conceptual.md) |

## Cómo ejecutarlo
```bash
python sprints/sprint_5_validacion_impacto/ejecutar_sprint5.py
```
Requiere los modelos del Sprint 3. Lee la tabla `resultado_campana_2027_1` de Supabase (o el archivo sellado local con
`--local`).

## Preguntas de control para practicar
1. ¿Por qué el resultado de 2027-1 se selló desde la Semana 1? ¿Qué se habría perdido si se usaba antes?
2. Si el error es 34% y su ventaja sobre la logística del Sprint 2 cabe en el margen del azar, ¿por qué el modelo sirve? Use la tabla por
   quintiles y el AUC.
3. ¿Qué es un valor esperado y por qué las cifras de los escenarios lo son?
4. ¿Por qué es mala idea llamar primero a los de mayor probabilidad?
5. ¿Qué supuesto mueve más el escenario 1 y qué recomendaría antes de invertir?
6. ¿Qué cambiaría en estos cálculos con datos reales de Admisiones?
