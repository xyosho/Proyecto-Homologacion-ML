# Sprint 2 — Ingeniería de características y regresión logística

**Proyecto:** Modelo Predictivo de Segmentación de Mercado y Propensión a la Matrícula · Unicervantes
**Entrega:** jueves 29 de octubre de 2026 · Homologación de Data Mining y Machine Learning

> **Pedido del docente (Semana 2):** entregar la misma tabla de datos con columnas nuevas y útiles (por ejemplo,
> "¿Aplica a Beca Mi Vocación? Sí/No" o `segmento_rendimiento_icfes`) y un primer cálculo que sirva de punto de
> comparación.

El proyecto predice **si el inscrito se matricula**. El modelo base es una **regresión logística**.

## Qué se entrega
| Entregable | Dónde |
|---|---|
| La tabla del Sprint 1 con **14 columnas nuevas** (2.991 inscritos) | Se construye al ejecutar el cuaderno o el script; se publica en Supabase como `dataset_caracteristicas` (solo lectura) |
| La **entrevista de admisión convertida en números**: rúbrica de 1 a 5 por sección e índice vocacional de 0 a 100 | Sección 2 del cuaderno · [`data/processed/dataset_entrevista.csv`](data/processed/dataset_entrevista.csv) |
| Segmentación de mercado con **k-means** (5 segmentos con nombres en español sencillo) | Columna `segmento_mercado` y gráficas del cuaderno |
| **Regresión logística** (el modelo base) y su error | Sección 7 del cuaderno · [`resultados/metricas_logistica_sprint2.json`](sprints/sprint_2_caracteristicas/resultados/metricas_logistica_sprint2.json) |
| Cuaderno para Google Colab | [`sprint2_caracteristicas_colab.ipynb`](sprint2_caracteristicas_colab.ipynb) |
| Cuaderno local (ejecutado, con sus salidas) | [`sprint2_caracteristicas_local.ipynb`](sprint2_caracteristicas_local.ipynb) |
| Script que genera la tabla, el Excel, las gráficas y las métricas | [`sprints/sprint_2_caracteristicas/ejecutar_sprint2.py`](sprints/sprint_2_caracteristicas/ejecutar_sprint2.py) |
| Justificación conceptual y bitácora de auditoría de IA | [`justificacion_conceptual.md`](sprints/sprint_2_caracteristicas/justificacion_conceptual.md) · [`bitacora_auditoria_ia.md`](sprints/sprint_2_caracteristicas/bitacora_auditoria_ia.md) |
| Resultados de la última ejecución (tablas, métricas y figuras) | [`sprints/sprint_2_caracteristicas/resultados/`](sprints/sprint_2_caracteristicas/resultados) |

## La entrevista de admisión en números
La entrevista de admisión tiene preguntas abiertas. Para que un modelo la use, el entrevistador califica cada sección
con una **rúbrica de 1 a 5** (1 = muy débil, 3 = aceptable, 5 = sobresaliente):

| Sección del formulario | Columna |
|---|---|
| Interés por el programa académico | `entrevista_interes_programa` |
| Historia de vida (cualidades, aspectos por mejorar, colegio, tiempo libre) | `entrevista_proyecto_vida` |
| Interés por la universidad | `entrevista_interes_universidad` |
| Conciencia social | `entrevista_conciencia_social` |
| Apariencia y actitud (expresión y argumentación) | `entrevista_expresion` |

- **Índice vocacional** = 25 × (promedio de las 5 calificaciones − 1), de 0 a 100. Es una regla fija.
- Entre los entrevistados, la matrícula sube de 38% (índice hasta 40) a cerca de 60% (índice mayor de 60). Sin
  entrevista es de 29%.
- La sección de **salud mental** no entra al modelo: es un dato sensible (Ley 1581 de 2012, art. 5). Queda solo para
  Bienestar, en una tabla cerrada que la API no deja leer.
- No hay respuestas reales de entrevistas: las calificaciones se simulan con un supuesto documentado (S-46), coherentes
  con el puntaje vocacional que exige la beca Mi Vocación.

## Las 14 columnas nuevas
| Columna | Qué es |
|---|---|
| `particion` | Conjunto temporal: entrenamiento (2024-1 a 2025-2), validación (2026-1), prueba (2026-2) y campaña (2027-1) |
| `aplica_beca_saber11` | Sí/No: puntaje global Saber 11 ≥ 310 |
| `aplica_beca_mi_vocacion` | Sí/No: presentó la entrevista y su puntaje vocacional es ≥ 3 |
| `indice_vocacional` | Índice de 0 a 100 de la entrevista de admisión (vacío si no hubo entrevista) |
| `segmento_rendimiento_icfes` | Bajo (< 250), medio (250-309), alto (310-349) o superior (≥ 350) |
| `brecha_colegio_vs_icfes` | Si rinde más en el colegio que en el examen (diferencia de puntajes estandarizados) |
| `ahorro_beca_primer_semestre` | Cuánto le ahorra la beca en el 1er semestre (tarifa plena − precio neto), en COP |
| `log_distancia` | Logaritmo de la distancia por vías desde la dirección hasta el campus |
| `zona_distancia` | Cerca (hasta 10 km), media (10 a 20 km) o lejos (más de 20 km) |
| `rezago_saber11` | Tiempo entre el Saber 11 y la inscripción |
| `canal_agrupado` | Eventos, relacional o digital |
| `estrato_grupo` | Estratos 1 y 2, estrato 3 o estratos 4 a 6 |
| `colegio_privado` | 1 si el colegio es privado |
| `segmento_mercado` | Perfil del aspirante según k-means |

El precio que se usa es el **precio neto del 1er semestre** (`valor_neto_primer_semestre`, ya en la tabla del
Sprint 1). Todo lo que se aprende de los datos (escalas y segmentos) se ajusta **solo con el entrenamiento**, para que
la validación y la prueba no "vean" el futuro (sin fuga de datos).

## Resultados
**Segmentos de mercado** (k-means sobre 6 variables estandarizadas; k = 5 elegido por la silueta, 0,193):

| Segmento | Inscritos | % que se matriculó | Rasgo real |
|---|---|---|---|
| S1: Colegio público, viven cerca del campus | 847 | 44,6% | 100% colegio público · 10,1 km por vías |
| S2: Buen puntaje ICFES, colegio privado | 747 | 52,8% | ICFES 315 |
| S3: Viven lejos del campus, estrato más bajo | 599 | 37,7% | 29,1 km por vías · estrato 2,2 |
| S4: Colegio privado, notas bajas en el colegio | 549 | 46,0% | notas 3,77 · ICFES 250 |
| S5: Aspirantes mayores, viven cerca del campus | 249 | 46,1% | 22,8 años · 14,4 km por vías |

Los nombres son relativos al promedio de todos los inscritos (ICFES 274, 15,6 km, 18,2 años). La silueta es baja:
los segmentos son perfiles útiles para Mercadeo, no grupos naturales.

**Regresión logística, el modelo base** (C = 1, sin ajuste de hiperparámetros, entrenada con 2024-1 a 2025-2):

| Periodo evaluado | Error | AUC |
|---|---|---|
| Validación (2026-1, 504 inscritos) | 35,7% | 0,680 |
| Prueba (2026-2, 761 inscritos) | 38,1% | 0,676 |

El AUC mide qué tan bien ordena a los inscritos (0,5 es azar). Este es el punto de comparación de los modelos del
Sprint 3.

## Cómo ejecutarlo
### En Google Colab
1. Abra [`sprint2_caracteristicas_colab.ipynb`](sprint2_caracteristicas_colab.ipynb) con el botón **Open in Colab**.
2. En el panel **Secretos** (icono de llave) cree `SUPABASE_URL` y `SUPABASE_KEY` (la clave **publicable**, nunca la
   secreta) y active el acceso del cuaderno.
3. *Entorno de ejecución → Ejecutar todas.* El cuaderno instala las librerías y escribe en Colab una copia de los
   módulos de `src/`, así que no necesita nada más del repositorio. Lee `dataset_matricula` y `dataset_entrevista`.

### En el computador
```bash
python -m venv .venv
.venv\Scripts\activate            # Windows (en Linux o Mac: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env             # y escriba ahí SUPABASE_URL y SUPABASE_KEY (clave publicable)
python sprints/sprint_2_caracteristicas/ejecutar_sprint2.py
```
- Sin `.env`, o con `--local`, los datos se leen de `data/processed/` (las mismas tablas planas que están en Supabase).
- El script guarda la tabla, el Excel, las gráficas y las métricas en `sprints/sprint_2_caracteristicas/resultados/`.
- También puede abrir [`sprint2_caracteristicas_local.ipynb`](sprint2_caracteristicas_local.ipynb) en Jupyter o VS Code.

## Estructura
```
README.md
sprint2_caracteristicas_colab.ipynb      cuaderno para Google Colab
sprint2_caracteristicas_local.ipynb      cuaderno local (ejecutado)
sprints/sprint_2_caracteristicas/
  ejecutar_sprint2.py                    genera tabla, Excel, gráficas y métricas
  justificacion_conceptual.md            la lógica de las columnas, la rúbrica, k-means y la regresión logística
  bitacora_auditoria_ia.md               qué se verificó del trabajo hecho con IA y qué se corrigió
  resultados/                            métricas, tablas y figuras de la última ejecución
src/
  comun.py                               rutas y lectura de la configuración
  conexion_supabase.py                   conexión segura (clave publicable, solo lectura)
  datos.py                               lee las tablas planas de Supabase o de data/processed
  caracteristicas.py                     las 14 columnas nuevas, el índice vocacional y k-means
  modelado.py                            regresión logística y métricas
  flujo.py                               paso común: cargar y construir las características
  graficas_sprint2.py                    gráficas del sprint en español sencillo
config/reglas_negocio.yaml               tarifas, becas, particiones, rúbrica y parámetros
data/processed/                          dataset_matricula.csv y dataset_entrevista.csv (respaldo local)
requirements.txt · .env.example · .gitignore
```

## Seguridad y datos
- Las credenciales nunca se escriben en el código: viven en `.env` (excluido por `.gitignore`) o en los Secretos de
  Colab. La clave publicable solo puede **leer** las tablas planas (políticas RLS de Supabase).
- La base es **sintética anclada a datos reales de Colombia**: registros anónimos del Saber 11 (ICFES), direcciones
  de Catastro Bogotá y del DANE, y tarifas y becas oficiales de Unicervantes. La matrícula, las notas del colegio y la
  entrevista se simulan con supuestos documentados. Ningún dato identifica a una persona real (Ley 1581 de 2012).
