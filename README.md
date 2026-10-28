# Sprint 2 — Ingeniería de características y modelo base

**Proyecto:** Modelo Predictivo de Segmentación de Mercado y Propensión a la Matrícula · Unicervantes
**Entrega:** jueves 29 de octubre de 2026 · Homologación de Data Mining y Machine Learning

> **Pedido del docente (Semana 2):** entregar la misma tabla de datos con columnas nuevas y útiles (por ejemplo,
> "¿Aplica a Beca Mi Vocación? Sí/No" o "Promedio estimado"; también `probabilidad_acceso_beca` y
> `segmento_rendimiento_icfes`) y un cálculo muy sencillo (modelo base) que sirva de punto de comparación.

## Qué se entrega
| Entregable | Dónde |
|---|---|
| La tabla del Sprint 1 con **15 columnas nuevas** (2.991 inscritos, sin vacíos) | Se construye al ejecutar el cuaderno o el script; se publica en Supabase como `dataset_caracteristicas` (solo lectura) |
| Segmentación de mercado con **k-means** (5 segmentos con nombres en español sencillo) | Columna `segmento_mercado` y gráficas del cuaderno |
| **Modelo base**: tasa histórica de matrícula por tipo de beca × tipo de canal | Sección 6 del cuaderno |
| Cuaderno para Google Colab | [`sprint2_caracteristicas_colab.ipynb`](sprint2_caracteristicas_colab.ipynb) |
| Cuaderno local (ejecutado, con sus salidas) | [`sprint2_caracteristicas_local.ipynb`](sprint2_caracteristicas_local.ipynb) |
| Script que genera la tabla, el Excel, las gráficas y las métricas | [`sprints/sprint_2_caracteristicas/ejecutar_sprint2.py`](sprints/sprint_2_caracteristicas/ejecutar_sprint2.py) |

## Las 15 columnas nuevas
| Columna | Qué es |
|---|---|
| `particion` | Conjunto temporal: entrenamiento (2024-1 a 2025-2), validación (2026-1), prueba (2026-2) y campaña (2027-1) |
| `aplica_beca_saber11` | Sí/No: puntaje global Saber 11 ≥ 310 |
| `aplica_beca_mi_vocacion` | Sí/No: presentó la entrevista y su puntaje vocacional es ≥ 3 |
| `probabilidad_acceso_beca` | Probabilidad de recibir una beca según los requisitos que cumple (frecuencia histórica con suavizado de Laplace) |
| `segmento_rendimiento_icfes` | Bajo (< 250), medio (250-309), alto (310-349) o superior (≥ 350) |
| `promedio_estimado_universidad` | Promedio esperado en el 1er semestre (regresión lineal con el Saber 11, las notas del colegio y el estrato) |
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
Sprint 1). Todo lo que se aprende de los datos (tasas, regresión, escalas y segmentos) se ajusta **solo con el
entrenamiento**, para que la validación y la prueba no "vean" el futuro (sin fuga de datos).

## Resultados
**Segmentos de mercado** (k-means sobre 6 variables estandarizadas; k = 5 elegido por la silueta, 0,193):

| Segmento | Inscritos | % que se matriculó | Rasgo real |
|---|---|---|---|
| S1: Colegio público, viven cerca del campus | 847 | 45,2% | 100% colegio público · 10,1 km por vías |
| S2: Buen puntaje ICFES, colegio privado | 747 | 51,1% | ICFES 315 |
| S3: Viven lejos del campus, estrato más bajo | 599 | 37,5% | 29,1 km por vías · estrato 2,2 |
| S4: Colegio privado, notas bajas en el colegio | 549 | 46,6% | notas 3,77 · ICFES 250 |
| S5: Aspirantes mayores, viven cerca del campus | 249 | 47,0% | 22,8 años · 14,4 km por vías |

Los nombres son relativos al promedio de todos los inscritos (ICFES 274, 15,6 km, 18,2 años). La silueta es baja:
los segmentos son perfiles útiles para Mercadeo, no grupos naturales.

**Modelo base:**

| Periodo evaluado | Modelo base | Decir siempre «no se matricula» |
|---|---|---|
| Validación (2026-1, 504 inscritos) | 37,7% de error · AUC 0,646 | 42,5% de error |
| Prueba (2026-2, 761 inscritos) | 41,7% de error · AUC 0,615 | 44,4% de error |

Este error es el punto de comparación que deben superar los modelos de Machine Learning del Sprint 3.

## Cómo ejecutarlo
### En Google Colab
1. Abra [`sprint2_caracteristicas_colab.ipynb`](sprint2_caracteristicas_colab.ipynb) con el botón **Open in Colab**.
2. En el panel **Secretos** (icono de llave) cree `SUPABASE_URL` y `SUPABASE_KEY` (la clave **publicable**, nunca la
   secreta) y active el acceso del cuaderno.
3. *Entorno de ejecución → Ejecutar todas.* El cuaderno instala las librerías y escribe en Colab una copia de los
   módulos de `src/`, así que no necesita nada más del repositorio.

### En el computador
```bash
python -m venv .venv
.venv\Scripts\activate            # Windows (en Linux o Mac: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env             # y escriba ahí SUPABASE_URL y SUPABASE_KEY (clave publicable)
python sprints/sprint_2_caracteristicas/ejecutar_sprint2.py
```
- Sin `.env`, o con `--local`, los datos se leen de `data/processed/` (las mismas tablas planas que están en Supabase).
- El script guarda la tabla, el Excel, las gráficas y las métricas en `sprints/sprint_2_caracteristicas/resultados/`
  (esa carpeta no se versiona: se genera al ejecutar).
- También puede abrir [`sprint2_caracteristicas_local.ipynb`](sprint2_caracteristicas_local.ipynb) en Jupyter o VS Code.

## Estructura
```
README.md
sprint2_caracteristicas_colab.ipynb      cuaderno para Google Colab
sprint2_caracteristicas_local.ipynb      cuaderno local (ejecutado)
sprints/sprint_2_caracteristicas/
  ejecutar_sprint2.py                    genera tabla, Excel, gráficas y métricas
src/
  comun.py                               rutas y lectura de la configuración
  conexion_supabase.py                   conexión segura (clave publicable, solo lectura)
  datos.py                               lee las tablas planas de Supabase o de data/processed
  caracteristicas.py                     las 15 columnas nuevas y k-means
  modelado.py                            modelo base y métricas
  flujo.py                               paso común: cargar y construir las características
  graficas_sprint2.py                    gráficas del sprint en español sencillo
config/reglas_negocio.yaml               tarifas, becas, particiones y parámetros
data/processed/                          dataset_matricula.csv y dataset_permanencia.csv (respaldo local)
requirements.txt · .env.example · .gitignore
```

## Seguridad y datos
- Las credenciales nunca se escriben en el código: viven en `.env` (excluido por `.gitignore`) o en los Secretos de
  Colab. La clave publicable solo puede **leer** las tablas planas (políticas RLS de Supabase).
- La base es **sintética anclada a datos reales de Colombia**: registros anónimos del Saber 11 (ICFES), direcciones
  de Catastro Bogotá y del DANE, y tarifas y becas oficiales de Unicervantes. La matrícula y las notas del colegio se
  simulan con supuestos documentados. Ningún dato identifica a una persona real (Ley 1581 de 2012).
