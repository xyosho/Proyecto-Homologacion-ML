# Proyecto-Homologacion-ML

**Modelo Predictivo de Segmentación de Mercado y Propensión a la Matrícula — Unicervantes**

Proyecto de homologación de las asignaturas de **Data Mining** y **Machine Learning** (Facultad de Ingeniería,
Unicervantes). Busca predecir qué aspirantes a **Ingeniería en Analítica de Datos (AD)** e **Ingeniería en Sistemas de
Software e IA (SSIA)** pagarán la matrícula y, si entran con beca, qué tan probable es que la pierdan en el primer
semestre. Con eso, Admisiones y Mercadeo pueden priorizar su esfuerzo: a quién llamar primero, qué ofrecer en eventos
como ExpoEstudiantes y a qué becados acompañar a tiempo.

## Qué se entrega al final
Al cierre de las 6 semanas el proyecto entrega un "paquete" de tres elementos:

| Elemento | Qué es |
|---|---|
| **Modelo predictivo funcional** | Un script en Python que, con los datos de un aspirante hipotético (puntaje ICFES, programa, situación económica…), da la probabilidad de que se matricule o de que pierda los beneficios de su beca |
| **Repositorio de código ordenado** | El código dividido en pasos lógicos, con comentarios propios que explican qué hace cada parte y por qué se eligió esa metodología |
| **Informe ejecutivo (PDF)** | Un documento para las directivas, en lenguaje de negocio: qué problema resuelve el modelo, cómo usarlo en la estrategia de captación y cuál es su impacto económico estimado |

## Cronograma de sprints
Metodología ágil con entregas formales **cada jueves desde el 22 de octubre de 2026**. Cada sprint se publica en su
propia rama.

| Sprint | Entrega | Tema | Entregable concreto de la semana | Estado |
|---|---|---|---|---|
| 1 | Jue 22-oct-2026 | Definición del problema, datos de admisiones (o generación de datos sintéticos rigurosamente validados) y análisis exploratorio (EDA) | Tabla de datos (Excel o CSV) o un script que genere datos sintéticos que respeten las reglas de la Universidad (ICFES entre 0 y 500, tarifas oficiales). Conexión segura con Supabase, dataset plano y EDA inicial | ✅ Entregado · rama [`Sprint-1`](https://github.com/xyosho/Proyecto-Homologacion-ML/tree/Sprint-1) |
| 2 | Jue 29-oct-2026 | Ingeniería de características: variables derivadas útiles para el negocio (por ejemplo `probabilidad_acceso_beca` y `segmento_rendimiento_icfes`) | La misma tabla con columnas nuevas (por ejemplo "¿Aplica a Beca Mi Vocación? (Sí/No)" o "Promedio estimado") y un cálculo sencillo (modelo base) como punto de comparación | Pendiente |
| 3 | Jue 5-nov-2026 | Modelado: un modelo base (*baseline*) y un modelo avanzado de clasificación (Random Forest o XGBoost) para predecir matrícula o retención | Un modelo de Machine Learning que ya haga predicciones y una tabla comparativa: "el cálculo sencillo de la Semana 2 tenía un error del X%; este modelo, del Y%" | Pendiente |
| 4 | Jue 12-nov-2026 | Machine Learning explicable (XAI): SHAP o LIME para justificar las decisiones del modelo y su coherencia con las reglas de negocio | Un análisis que responda "¿por qué el modelo toma sus decisiones?" (por ejemplo, que pesa más el ICFES que la edad), explicado en español sencillo | Pendiente |
| 5 | Jue 19-nov-2026 | Validación e impacto comercial: escenarios de cómo el modelo optimiza la captación y la asignación de recursos | Una prueba con datos que el modelo no haya visto, si acierta o falla, y un cálculo estimado de cómo ayuda a la Universidad a no perder dinero o estudiantes | Pendiente |
| 6 | Jue 26-nov-2026 | Integración final, documentación del repositorio y defensa oral | Repositorio final, informe ejecutivo en PDF y sustentación oral | Pendiente |

## Condiciones de cada entrega
- **Justificación conceptual:** explicación de la lógica matemática y estadística empleada, redactada con palabras
  propias del estudiante.
- **Bitácora de auditoría de IA:** cómo se validaron los datos sintéticos y el código generado con herramientas de IA,
  mostrando qué sesgos o errores se detectaron y cómo se corrigieron.
- **Sustentación técnica semanal:** en la revisión de cada jueves se hace una pregunta de control sobre los
  fundamentos del entregable.

## Datos
Mientras Admisiones entrega el histórico real, el proyecto usa una base **sintética anclada a datos reales de
Colombia**:
- registros reales y anónimos del Saber 11 (ICFES, datos abiertos);
- direcciones reales de Catastro Bogotá y del DANE, asignadas al azar, para medir la distancia al campus;
- tarifas y becas oficiales de Unicervantes;
- un resultado de matrícula simulado con supuestos documentados.

Ningún dato identifica a una persona real (Ley 1581 de 2012). Con los datos reales de Admisiones, el mismo código se
vuelve a ejecutar.

## Tecnologías
Python (pandas, scikit-learn, XGBoost, SHAP, LIME) · Supabase (PostgreSQL con seguridad a nivel de fila) · Jupyter y
Google Colab.

Las credenciales nunca se escriben en el código: viven en un archivo `.env` (excluido del repositorio) o en los
Secretos de Colab, y la clave que usa Python solo puede **leer** el dataset analítico.

---
Estudiante: Frank Sebastian Higuera Perez · Ingeniería en Analítica de Datos · Unicervantes, Bogotá.
