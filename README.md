# Sprint 3 — Modelado

**Proyecto:** Modelo Predictivo de Segmentación de Mercado y Propensión a la Matrícula · Unicervantes
**Entrega:** jueves 5 de noviembre de 2026 · Homologación de Data Mining y Machine Learning

> **Pedido del docente (Semana 3):** entregar un modelo de Machine Learning que ya haga predicciones (no tiene que ser
> perfecto, pero debe funcionar) y una tabla comparativa sencilla: "El cálculo de la Semana 2 tenía un error del X%,
> mientras que este modelo de la Semana 3 tiene un error del Y%".

El proyecto predice **si el inscrito se matricula**. La regresión logística del Sprint 2 se compara con modelos más
avanzados: la misma logística con hiperparámetros ajustados, Random Forest y XGBoost.

## La frase pedida
**La regresión logística de la Semana 2 tenía un error del 37,2%, mientras que el modelo de la Semana 3 (regresión
logística ajustada) tiene un error del 37,8%** en los 761 inscritos de 2026-2, que ningún modelo vio al entrenar ni al
elegirse. **La diferencia (0,7 puntos) está dentro del margen del azar** (IC 95% de −1,6 a +2,8 puntos): los dos
modelos rinden igual.

| Modelo (prueba 2026-2) | Error % | AUC-ROC (IC 95%) | Brier |
|---|---|---|---|
| Sin modelo (clase mayoritaria) | 44,5% | 0,500 | 0,247 |
| Regresión logística del Sprint 2 (C = 1) | 37,2% | 0,676 (0,638–0,711) | 0,226 |
| **Regresión logística ajustada (elegida, C = 0,01)** | **37,8%** | **0,663 (0,624–0,700)** | **0,228** |
| Random Forest | 40,1% | 0,650 (0,612–0,686) | 0,233 |
| XGBoost | 38,0% | 0,660 (0,621–0,695) | 0,229 |

La logística del Sprint 2 da aquí 37,2% y no el 38,1% del Sprint 2 porque se reentrena con un periodo más
(entrenamiento + validación), igual que los demás modelos.

## Qué se entrega
| Entregable | Dónde |
|---|---|
| Regresión logística (del Sprint 2 y ajustada), Random Forest y XGBoost | Secciones 2 y 3 de los cuadernos |
| Modelos entrenados | [`sprints/sprint_3_modelado/modelos/`](sprints/sprint_3_modelado/modelos) |
| Tabla comparativa, búsqueda de hiperparámetros, métricas, figuras y predicciones | [`sprints/sprint_3_modelado/resultados/`](sprints/sprint_3_modelado/resultados) |
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
| **Logística** | 4 (C) | **0,6366** (C = 0,01) | 0,679 |
| Random Forest | 16 | 0,6410 | 0,674 |
| XGBoost | 12 | 0,6466 | 0,665 |

- Ganó la regresión logística: el resultado depende de pocos factores que se suman (beca, distancia, la U invertida
  del ICFES, canal y entrevista), y los árboles, con cerca de 1.800 datos, pagan su flexibilidad con más varianza.
- **No mejora a la logística del Sprint 2.** La diferencia en la prueba es de unos 5 inscritos y cabe en el margen del
  azar. No se cambia el modelo elegido al ver la prueba: eso la volvería una medición optimista.
- La matrícula de estos datos se simuló con un modelo logístico (supuesto S-15), así que la logística tiene ventaja por
  construcción. Con el histórico real de Admisiones la comparación se repite sin cambios.
- El elegido se reentrena con todo el histórico (2.575 inscritos de 2024-1 a 2026-2) y es el que predice la campaña
  2027-1.

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
- Tarda cerca de medio minuto. Guarda tablas, métricas, figuras y predicciones en `sprints/sprint_3_modelado/resultados/`
  y los modelos en `sprints/sprint_3_modelado/modelos/`.
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
  modelos/                               modelos entrenados (.joblib) y su ficha (.json)
  resultados/                            tablas, métricas, figuras y predicciones de la última ejecución
src/
  comun.py                               rutas y lectura de la configuración
  conexion_supabase.py                   conexión segura (clave publicable, solo lectura)
  datos.py                               lee las tablas planas de Supabase o de data/processed
  caracteristicas.py                     las columnas nuevas del Sprint 2, el índice vocacional y k-means
  modelado.py                            regresión logística, Random Forest, XGBoost y métricas
  flujo.py                               paso común: cargar y construir las características
config/reglas_negocio.yaml               tarifas, becas, particiones, rúbrica y parámetros
data/processed/                          dataset_matricula.csv y dataset_entrevista.csv (respaldo local)
requirements.txt · .env.example · .gitignore
```

## Preguntas de control para practicar
1. ¿Por qué la regresión logística le ganó a Random Forest y a XGBoost? ¿Es un fracaso del "modelo avanzado"?
2. ¿Cómo funciona un Random Forest por dentro (bootstrap, árboles, votación)? ¿Y XGBoost (residuos, tasa de
   aprendizaje)?
3. ¿Qué es la log-loss y por qué se usó para elegir modelos en vez del error %?
4. ¿Por qué la prueba 2026-2 se usa una sola vez y no se cambia el modelo elegido al verla?
5. El modelo ajustado no mejora a la logística del Sprint 2. ¿Qué significa que la diferencia esté "dentro del margen
   del azar"?
6. Si el modelo se equivoca en el 38% de los casos, ¿para qué le sirve a la Universidad?

## Seguridad y datos
- Las credenciales nunca se escriben en el código: viven en `.env` (excluido por `.gitignore`) o en los Secretos de
  Colab. La clave publicable solo puede **leer** las tablas planas (políticas RLS de Supabase).
- La base es **sintética anclada a datos reales de Colombia**: registros anónimos del Saber 11 (ICFES), direcciones
  de Catastro Bogotá y del DANE, y tarifas y becas oficiales de Unicervantes. La matrícula, las notas del colegio y la
  entrevista se simulan con supuestos documentados. Ningún dato identifica a una persona real (Ley 1581 de 2012).
