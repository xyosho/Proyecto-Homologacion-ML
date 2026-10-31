# Sprint 3 — Modelado

**Proyecto:** Modelo Predictivo de Segmentación de Mercado y Propensión a la Matrícula · Unicervantes
**Entrega:** jueves 5 de noviembre de 2026 · Homologación de Data Mining y Machine Learning

> **Pedido del docente (Semana 3):** entregar un modelo de Machine Learning que ya haga predicciones (no tiene que ser
> perfecto, pero debe funcionar) y una tabla comparativa sencilla: "El cálculo sencillo de la Semana 2 tenía un error
> del X%, mientras que este modelo de la Semana 3 tiene un error del Y%".

> Cifras del 31-oct-2026, con la regla de becas corregida: la Beca Saber 11 es del 35% el 1er semestre y del 30% desde
> el 2º; Mi Vocación, del 30% y del 20%; el pronto pago no es un descuento de la Universidad.

## La frase pedida
**El cálculo sencillo de la Semana 2 (modelo base) tenía un error del 42,2%, mientras que el modelo de la Semana 3
(regresión logística) tiene un error del 38,2%** en los 761 inscritos de 2026-2, que ningún modelo vio al entrenar ni al
elegirse.

| Modelo (prueba 2026-2) | Error % | AUC-ROC (IC 95%) | Brier |
|---|---|---|---|
| Sin modelo (clase mayoritaria) | 44,5% | 0,500 | 0,247 |
| Modelo base (Sprint 2) | 42,2% | 0,622 (0,581–0,658) | 0,237 |
| **Regresión logística (elegido)** | **38,2%** | **0,663 (0,624–0,699)** | **0,228** |
| Random Forest | 39,0% | 0,648 (0,608–0,684) | 0,232 |
| XGBoost | 38,4% | 0,661 (0,622–0,696) | 0,229 |

El modelo base da 42,2% y no el 40,7% del Sprint 2 porque aquí se entrena con un periodo más (entrenamiento +
validación), igual que los demás modelos.

## Qué se entrega
| Entregable | Dónde |
|---|---|
| **Objetivo 1:** ¿se matricula el inscrito? Modelo base, regresión logística, Random Forest y XGBoost | Secciones 2 y 3 de los cuadernos |
| **Objetivo 2:** ¿pierde la beca al cerrar el primer semestre? | Sección 4 de los cuadernos |
| Cuaderno para Google Colab | [`sprint3_modelado_colab.ipynb`](sprint3_modelado_colab.ipynb) |
| Cuaderno local (ejecutado, con sus salidas) | [`sprint3_modelado_local.ipynb`](sprint3_modelado_local.ipynb) |
| Script que entrena, compara y guarda modelos, tablas, figuras y predicciones | [`sprints/sprint_3_modelado/ejecutar_sprint3.py`](sprints/sprint_3_modelado/ejecutar_sprint3.py) |
| Justificación conceptual | [`sprints/sprint_3_modelado/justificacion_conceptual.md`](sprints/sprint_3_modelado/justificacion_conceptual.md) |
| Bitácora de auditoría de IA | [`sprints/sprint_3_modelado/bitacora_auditoria_ia.md`](sprints/sprint_3_modelado/bitacora_auditoria_ia.md) |

## Cómo se eligió el modelo (sin hacerse trampa)
| Conjunto | Periodos | Para qué |
|---|---|---|
| Entrenamiento | 2024-1 a 2025-2 | Aprender |
| Validación | 2026-1 (504 inscritos) | Elegir hiperparámetros y modelo, por **log-loss** |
| Prueba | 2026-2 (761 inscritos) | Medir **una sola vez** |

| Modelo | Combinaciones probadas | Log-loss en validación | AUC en validación |
|---|---|---|---|
| **Logística** | 4 (C) | **0,6368** (C = 0,01) | 0,678 |
| Random Forest | 16 | 0,6400 | 0,673 |
| XGBoost | 12 | 0,6450 | 0,666 |

- Ganó la regresión logística: el resultado depende de pocos factores que se suman (beca, distancia, la U invertida
  del ICFES, canal y entrevista), y los árboles, con cerca de 1.800 datos, pagan su flexibilidad con más varianza.
- El modelo avanzado se construyó, se comparó con evidencia y no ganó. Elegir el más simple cuando rinde igual es la
  navaja de Occam.
- El elegido se reentrena con todo el histórico (2.575 inscritos de 2024-1 a 2026-2) y es el que predice la campaña
  2027-1.

## Objetivo 2: pérdida de beca
Hay 557 becados con el primer semestre cerrado. Como son pocos, los hiperparámetros se eligen con **validación cruzada
estratificada de 5 pliegues** dentro del entrenamiento, y la prueba es 2026-1 (140 becados); la cohorte 2026-2 aún no
cierra semestre. No se usa el promedio del primer semestre, porque es justamente lo que define si se pierde la beca.

- **Elegida: regresión logística.** Su log-loss de validación cruzada (0,6337) queda a menos de 0,002 de la del Random
  Forest (0,6333), así que se queda el modelo más simple.
- Se equivoca en 37,9%, frente a 42,9% de decir "todos la pierden". AUC 0,686 (IC 95%: 0,591–0,771).
- Si se marca al 10% de becados con mayor riesgo, el 79% de ellos sí perdió la beca; la tasa general es 57%.
- Lectura: el modelo ordena mejor que la regla sencilla, pero con 140 becados el intervalo es ancho. Sirve como alerta
  temprana, no para decidir solo quién recibe tutoría.

## Cómo ejecutarlo
### En Google Colab
1. Abra [`sprint3_modelado_colab.ipynb`](sprint3_modelado_colab.ipynb) con el botón **Open in Colab**.
2. En el panel **Secretos** (icono de llave) cree `SUPABASE_URL` y `SUPABASE_KEY` (la clave **publicable**, nunca la
   secreta) y active el acceso del cuaderno.
3. *Entorno de ejecución → Ejecutar todas.* El cuaderno instala las librerías y escribe en Colab una copia de los
   módulos de `src/`, así que no necesita nada más del repositorio. Entrena todo dentro (tarda unos minutos).

### En el computador
```bash
python -m venv .venv
.venv\Scripts\activate            # Windows (en Linux o Mac: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env             # y escriba ahí SUPABASE_URL y SUPABASE_KEY (clave publicable)
python sprints/sprint_3_modelado/ejecutar_sprint3.py
```
- Sin `.env`, o con `--local`, los datos se leen de `data/processed/` (las mismas tablas planas que están en Supabase).
- Tarda cerca de 1,5 minutos. Guarda tablas, métricas, figuras y predicciones en `sprints/sprint_3_modelado/resultados/`
  y los modelos en `sprints/sprint_3_modelado/modelos/` (esas carpetas no se versionan: se generan al ejecutar).
- También puede abrir [`sprint3_modelado_local.ipynb`](sprint3_modelado_local.ipynb) en Jupyter o VS Code.

## Estructura
```
README.md
sprint3_modelado_colab.ipynb             cuaderno para Google Colab
sprint3_modelado_local.ipynb             cuaderno local (ejecutado)
sprints/sprint_3_modelado/
  ejecutar_sprint3.py                    entrena, compara y guarda modelos, tablas, figuras y predicciones
  justificacion_conceptual.md            la lógica matemática y estadística de los modelos
  bitacora_auditoria_ia.md               qué se verificó del trabajo hecho con IA y qué se corrigió
src/
  comun.py                               rutas y lectura de la configuración
  conexion_supabase.py                   conexión segura (clave publicable, solo lectura)
  datos.py                               lee las tablas planas de Supabase o de data/processed
  caracteristicas.py                     las columnas nuevas del Sprint 2 y k-means
  modelado.py                            modelo base, modelos de Machine Learning y métricas
  flujo.py                               paso común: cargar y construir las características
config/reglas_negocio.yaml               tarifas, becas, particiones y parámetros
data/processed/                          dataset_matricula.csv y dataset_permanencia.csv (respaldo local)
requirements.txt · .env.example · .gitignore
```

## Preguntas de control para practicar
1. ¿Por qué la regresión logística le ganó a Random Forest y casi empató con XGBoost? ¿Es un fracaso del "modelo
   avanzado"?
2. ¿Cómo funciona un Random Forest por dentro (bootstrap, árboles, votación)? ¿Y XGBoost (residuos, tasa de
   aprendizaje)?
3. ¿Qué es la log-loss y por qué se usó para elegir modelos en vez del error %?
4. ¿Por qué la prueba 2026-2 se usa una sola vez?
5. Si el modelo se equivoca en el 38% de los casos, ¿para qué le sirve a la Universidad?
6. En el modelo de beca el Random Forest tuvo una log-loss un poco menor en la validación cruzada. ¿Por qué se eligió
   la regresión logística?

## Seguridad y datos
- Las credenciales nunca se escriben en el código: viven en `.env` (excluido por `.gitignore`) o en los Secretos de
  Colab. La clave publicable solo puede **leer** las tablas planas (políticas RLS de Supabase).
- La base es **sintética anclada a datos reales de Colombia**: registros anónimos del Saber 11 (ICFES), direcciones
  de Catastro Bogotá y del DANE, y tarifas y becas oficiales de Unicervantes. La matrícula y las notas del colegio se
  simulan con supuestos documentados. Ningún dato identifica a una persona real (Ley 1581 de 2012).
