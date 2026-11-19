# Sprint 5 — Validación con datos no vistos e impacto en matrículas (Semana 5 · jueves 19-nov-2026)

**Proyecto:** Modelo Predictivo de Segmentación de Mercado y Propensión a la Matrícula · Unicervantes
**Entrega:** jueves 19 de noviembre de 2026 · Homologación de Data Mining y Machine Learning

## Entregable de la semana
> Probar el modelo con datos que nunca ha visto para demostrar que funciona en la vida real, y calcular cuánto dinero o
> cuántos estudiantes podría ahorrar o retener la Universidad con este modelo. Incluir escenarios de captación (por
> ejemplo ExpoEstudiantes).

## Respuesta corta
**1. Datos nunca vistos.** El resultado de la campaña 2027-1 (416 inscritos) estuvo **sellado desde la Semana 1** y se
abrió solo aquí:

| Modelo (campaña 2027-1) | Error % (IC 95%) | AUC-ROC (IC 95%) | Brier |
|---|---|---|---|
| Regresión logística del Sprint 2 (modelo base) | 35,3% (31,0–40,1) | 0,665 (0,608–0,713) | 0,222 |
| **Regresión logística con NLP (elegida)** | **33,9% (29,6–38,7)** | **0,697 (0,644–0,744)** | **0,213** |
| XGBoost | 34,1% (30,0–38,5) | 0,687 (0,635–0,735) | 0,216 |

- El error del modelo elegido es **cercano al de la prueba del Sprint 3 (32,7%)**: no estaba sobreajustado.
- Frente a la logística del Sprint 2, el error baja 1,4 puntos, pero la diferencia está dentro del margen del azar
  (IC 95%: −4,1 a +1,2 puntos): **todavía no se puede afirmar que sea mejor**.
- Lo útil es el **orden**: en el 20% con mayor probabilidad se matriculó el 80%; en el 20% con menor probabilidad,
  el 29%.

**2. Cuántos estudiantes retiene** (valor esperado con dos supuestos: capacidad de seguimiento y efecto de la llamada;
datos sintéticos):

| Escenario | Con el modelo | Sin el modelo |
|---|---|---|
| E1 · Seguimiento a 125 inscritos de 2027-1 | 12,3 matrículas adicionales · $53,3 M de ingreso del 1er semestre | 10,2 · $42,1 M (al azar) |
| E2 · Expo Estudiantes 2026-1 (74 inscritos, 30 matriculados) | +2,2 matrículas con seguimiento a 22 inscritos | sin seguimiento priorizado |

- **El valor del modelo en el seguimiento (E1):** 2,1 matrículas y $11,2 M más que llamar al azar en una sola campaña
  (cada matrícula vale su precio neto del 1er semestre, con las tarifas oficiales).
- Llamar primero a los de mayor probabilidad es **lo peor**: ya se iban a matricular.
- El supuesto que más mueve E1 es el efecto de la llamada: con ±50%, las matrículas adicionales van de 6,1 a 18,4.
- No se calculan costos (del seguimiento ni de la Expo) porque el proyecto no tiene esos datos.

## Lo que se entrega
| Entregable | Archivo |
|---|---|
| Prueba en la campaña 2027-1 | [`resultados/prueba_campana_2027_1.csv`](sprints/sprint_5_validacion_impacto/resultados/prueba_campana_2027_1.csv) · `prueba_campana_por_quintil.csv` · [`figuras/prueba_campana_2027_1.png`](sprints/sprint_5_validacion_impacto/resultados/figuras/prueba_campana_2027_1.png) |
| Escenario 1 (seguimiento) + sensibilidad | [`resultados/escenario1_seguimiento.csv`](sprints/sprint_5_validacion_impacto/resultados/escenario1_seguimiento.csv) · `escenario1_sensibilidad.csv` · [`figuras/escenario1_seguimiento.png`](sprints/sprint_5_validacion_impacto/resultados/figuras/escenario1_seguimiento.png) |
| Escenario 2 (Expo Estudiantes) | [`resultados/escenario2_expo.csv`](sprints/sprint_5_validacion_impacto/resultados/escenario2_expo.csv) · `escenario2_segmentos_expo.csv` · [`figuras/escenario2_expo.png`](sprints/sprint_5_validacion_impacto/resultados/figuras/escenario2_expo.png) |
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

En Google Colab, abra el cuaderno `_colab` con el botón **Open in Colab**. Con los Secretos `SUPABASE_URL` y
`SUPABASE_KEY` lee de Supabase; **sin clave** no hay que subir nada: lee `data/processed` de la rama `Sprint-5` en
GitHub, incluido el resultado sellado de 2027-1.

## Preguntas de control para practicar
1. ¿Por qué el resultado de 2027-1 se selló desde la Semana 1? ¿Qué se habría perdido si se usaba antes?
2. Si el error es 34% y su ventaja sobre la logística del Sprint 2 cabe en el margen del azar, ¿por qué el modelo sirve? Use la tabla por
   quintiles y el AUC.
3. ¿Qué es un valor esperado y por qué las cifras de los escenarios lo son?
4. ¿Por qué es mala idea llamar primero a los de mayor probabilidad?
5. ¿Qué supuesto mueve más el escenario 1 y qué recomendaría validar primero con Admisiones?
6. ¿Qué cambiaría en estos cálculos con datos reales de Admisiones?
