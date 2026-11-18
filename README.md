# Proyecto-Homologacion-ML

**Modelo Predictivo de Segmentación de Mercado y Propensión a la Matrícula — Unicervantes**

Proyecto de homologación de las asignaturas de **Data Mining** y **Machine Learning** (Facultad de Ingeniería,
Unicervantes). Busca predecir qué aspirantes a **Ingeniería en Analítica de Datos (AD)** e **Ingeniería en Sistemas de
Software e IA (SSIA)** pagarán la matrícula. Con eso, Admisiones y Mercadeo pueden priorizar su esfuerzo: a quién
llamar primero y qué ofrecer en eventos como ExpoEstudiantes.

## Qué se entrega al final
Al cierre de las 6 semanas el proyecto entrega un "paquete" de tres elementos:

| Elemento | Qué es |
|---|---|
| **Modelo predictivo funcional** | Un script en Python que, con los datos de un aspirante hipotético (puntaje ICFES, programa, situación económica…), da la probabilidad de que se matricule |
| **Repositorio de código ordenado** | El código dividido en pasos lógicos, con comentarios propios que explican qué hace cada parte y por qué se eligió esa metodología |
| **Informe ejecutivo (PDF)** | Un documento para las directivas, en lenguaje de negocio: qué problema resuelve el modelo, cómo usarlo en la estrategia de captación y cuál es su impacto económico estimado |

## Cronograma de sprints
Metodología ágil con entregas formales **cada jueves desde el 22 de octubre de 2026**. Cada sprint se publica en su
propia rama.

| Sprint | Entrega | Tema | Entregable concreto de la semana | Estado |
|---|---|---|---|---|
| 1 | Jue 22-oct-2026 | Definición del problema, datos de admisiones (o generación de datos sintéticos rigurosamente validados) y análisis exploratorio (EDA) | Tabla de datos (Excel o CSV) o un script que genere datos sintéticos que respeten las reglas de la Universidad (ICFES entre 0 y 500, tarifas oficiales). Conexión segura con Supabase, dataset plano y EDA inicial | ✅ Entregado · rama [`Sprint-1`](https://github.com/xyosho/Proyecto-Homologacion-ML/tree/Sprint-1) |
| 2 | Jue 29-oct-2026 | Ingeniería de características: variables derivadas útiles para el negocio, incluida la entrevista de admisión convertida en un puntaje vocacional con procesamiento de lenguaje natural (NLP) | La misma tabla con columnas nuevas (por ejemplo "¿Aplica a Beca Mi Vocación? (Sí/No)") y un primer modelo, una regresión logística, como punto de comparación | ✅ Entregado · rama [`Sprint-2`](https://github.com/xyosho/Proyecto-Homologacion-ML/tree/Sprint-2) |
| 3 | Jue 5-nov-2026 | Modelado: la regresión logística del Sprint 2, mejorada con el puntaje NLP, frente a regresiones de conteo (Poisson y binomial negativa) y modelos avanzados de clasificación (Random Forest y XGBoost) para predecir la matrícula | Un modelo de Machine Learning que ya haga predicciones y una tabla comparativa: "el cálculo de la Semana 2 tenía un error del X%; este modelo, del Y%" | ✅ Entregado · rama [`Sprint-3`](https://github.com/xyosho/Proyecto-Homologacion-ML/tree/Sprint-3) |
| 4 | Jue 12-nov-2026 | Machine Learning explicable (XAI): SHAP o LIME para justificar las decisiones del modelo y su coherencia con las reglas de negocio | Un análisis que responda "¿por qué el modelo toma sus decisiones?" (por ejemplo, que pesa más el ICFES que la edad), explicado en español sencillo | ✅ Entregado · rama [`Sprint-4`](https://github.com/xyosho/Proyecto-Homologacion-ML/tree/Sprint-4) |
| 5 | Jue 19-nov-2026 | Validación e impacto comercial: escenarios de cómo el modelo optimiza la captación y la asignación de recursos | Una prueba con datos que el modelo no haya visto, si acierta o falla, y un cálculo estimado de cómo ayuda a la Universidad a no perder dinero o estudiantes | ✅ Entregado · rama [`Sprint-5`](https://github.com/xyosho/Proyecto-Homologacion-ML/tree/Sprint-5) |
| 6 | Jue 26-nov-2026 | Integración final, documentación del repositorio y defensa oral | Repositorio final, informe ejecutivo en PDF y sustentación oral | Pendiente |

## Condiciones de cada entrega
- **Justificación conceptual:** explicación de la lógica matemática y estadística empleada, redactada con palabras
  propias.
- **Sustentación técnica semanal:** en la revisión de cada jueves se hace una pregunta de control sobre los
  fundamentos del entregable.

## App web de Admisiones (avance del Sprint 6)
La carpeta [`sprints/sprint_6_integracion/app_web`](sprints/sprint_6_integracion/app_web) tiene la app para los
asesores, publicada en Vercel y conectada a Supabase. Con ella registran aspirantes y ven en el navegador la
probabilidad de matrícula. También crean enlaces de la encuesta y de la entrevista vocacional, y los comparten como
enlace o como código QR. Una tarea diaria de Vercel hace una consulta mínima a Supabase para que el proyecto no se pause
por inactividad. El repositorio no guarda ninguna clave. Cómo desplegarla y configurarla, en su
[README](sprints/sprint_6_integracion/app_web/README.md).

## Datos
Mientras Admisiones entrega el histórico real, el proyecto usa una base **sintética anclada a datos reales de
Colombia**:
- registros reales y anónimos del Saber 11 (ICFES, datos abiertos);
- direcciones reales de Catastro Bogotá y del DANE, asignadas al azar, para medir la distancia al campus;
- tarifas y becas oficiales de Unicervantes;
- un resultado de matrícula simulado como Bernoulli, con la tasa p = 43/76 de una muestra de ejemplo, y otros
  supuestos documentados.

Ningún dato identifica a una persona real (Ley 1581 de 2012). Con los datos reales de Admisiones, el mismo código se
vuelve a ejecutar.

## Tecnologías
Python (pandas, scikit-learn, XGBoost, SHAP, LIME) · Supabase (PostgreSQL con seguridad a nivel de fila) · Jupyter y
Google Colab.

Las credenciales nunca se escriben en el código: viven en un archivo `.env` (excluido del repositorio) o en los
Secretos de Colab, y la clave que usa Python solo puede **leer** las tablas analíticas anonimizadas.

---
Estudiante: Frank Sebastian Higuera Perez · Ingeniería en Analítica de Datos · Unicervantes, Bogotá.
