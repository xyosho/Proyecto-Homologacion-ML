// Analítica: tablero que se actualiza solo con los aspirantes registrados (tiempo real de Supabase).
// Gráficas predeterminadas y gráficas propias (agrupar por un dato, elegir la medida y el tipo). Cada gráfica permite
// cambiar el tipo y ver la tabla con los números. Pestañas por semestre de ingreso y comparación entre semestres. Reglas de dataviz: un solo eje, color por categoría en orden fijo,
// barras finas con extremos redondeados, leyenda solo con 2 o más series y vista de tabla siempre disponible.
import { $, el, icono, pct, km, dia, hace, animarNumero, animarEntrada, sinMovimiento, avisar,
  CANALES, ESTADOS, ETIQUETA_ESTADO, NOMBRE_BECA, PROPENSION, TIPO, GENERO, PROGRAMAS, SERIES, ESTADO_COLOR } from "./ui.js";
import { estado, banda, zona, ubicacionDe, esJefe, nombreAsesor, esSimulado, enMiCartera } from "./datos.js";

const GRIS = "#B9B1B1", TINTA = "#4A4A4A", REJILLA = "#F1E6E6";
const media = (v) => { const x = v.filter((n) => n !== null && n !== undefined && !Number.isNaN(n)); return x.length ? x.reduce((s, n) => s + n, 0) / x.length : null; };
const conPrediccion = (a) => a.propension !== null && a.propension !== undefined;

// ---------------------------------------------------------------------------- dimensiones y medidas
const DIMENSIONES = {
  fecha: { nombre: "Fecha de registro (día o mes)", grupo: "Tiempo", valor: (a) => dia(a.creado_en), orden: "fecha", etiqueta: (k) => new Date(`${k}T12:00:00`).toLocaleDateString("es-CO", { day: "numeric", month: "short" }) },
  programa: { nombre: "Programa", grupo: "El aspirante", valor: (a) => a.programa, orden: ["AD", "SSIA"], etiqueta: (k) => k, largo: (k) => PROGRAMAS[k] },
  periodo: { nombre: "Semestre de ingreso", grupo: "Tiempo", valor: (a) => a.periodo, orden: "texto" },
  canal: { nombre: "¿Cómo conoció la Universidad?", grupo: "Captación y seguimiento", valor: (a) => a.canal || "SIN", etiqueta: (k) => (k === "SIN" ? "Sin dato" : CANALES[k]) },
  beca: { nombre: "Beca que se aplica", grupo: "Predicción y resultado", valor: (a) => a.beca || "NINGUNA", orden: ["SABER_11", "MI_VOCACION", "NINGUNA"], etiqueta: (k) => NOMBRE_BECA[k] },
  propension: { nombre: "Propensión a matricularse", grupo: "Predicción y resultado", valor: (a) => a.propension || "SIN", orden: ["ALTA", "MEDIA", "BAJA", "SIN"], fijos: ["ALTA", "MEDIA", "BAJA"],
    etiqueta: (k) => (k === "SIN" ? "Sin predecir" : PROPENSION[k]), colores: ESTADO_COLOR },
  decision: { nombre: "¿Se matricularía? (predicción)", grupo: "Predicción y resultado", valor: (a) => (conPrediccion(a) ? (a.se_matricularia ? "SI" : "NO") : "SIN"), orden: ["SI", "NO", "SIN"], fijos: ["SI", "NO"],
    etiqueta: (k) => ({ SI: "Sí", NO: "No", SIN: "Sin predecir" })[k], colores: { SI: ESTADO_COLOR.ALTA, NO: ESTADO_COLOR.BAJA, SIN: GRIS } },
  estado: { nombre: "Estado del seguimiento", grupo: "Captación y seguimiento", valor: (a) => a.estado, orden: [...Object.keys(ESTADOS), "NO_MATRICULADO"], etiqueta: (k) => ETIQUETA_ESTADO[k] },
  fuente: { nombre: "Cómo se registró (personal o encuesta)", grupo: "Captación y seguimiento", valor: (a) => (a.origen === "SIMULADO" ? "SIMULADO" : a.fuente === "ENCUESTA" ? "ENCUESTA" : "APP"),
    orden: ["APP", "ENCUESTA", "SIMULADO"], etiqueta: (k) => ({ APP: "Lo registró el personal", ENCUESTA: "Llenó la encuesta", SIMULADO: "Base simulada" })[k] },
  origen: { nombre: "Origen (app o base simulada)", grupo: "Captación y seguimiento", soloJefe: true, valor: (a) => a.origen, orden: ["APP", "SIMULADO"], etiqueta: (k) => (k === "APP" ? "Registrados en la app" : "Base simulada") },
  resultado: { nombre: "¿Se matriculó? (resultado real)", grupo: "Predicción y resultado", soloJefe: true, valor: (a) => (a.matriculado_real === true ? "SI" : a.matriculado_real === false ? "NO" : null),
    orden: ["SI", "NO"], etiqueta: (k) => (k === "SI" ? "Se matriculó" : "No se matriculó"), colores: { SI: ESTADO_COLOR.ALTA, NO: ESTADO_COLOR.BAJA } },
  asesor: { nombre: "Asesor asignado", grupo: "Captación y seguimiento", soloJefe: true, valor: (a) => a.asesor_id || "SIN", etiqueta: (k) => (k === "SIN" ? "Sin asesor" : nombreAsesor(k)) },
  ubicacion: { nombre: "Localidad o municipio", grupo: "Ubicación", valor: (a) => a.ubicacion },
  ciudad: { nombre: "Bogotá frente a cada municipio", grupo: "Ubicación", valor: (a) => (ubicacionDe(a.ubicacion)?.tipo === "LOCALIDAD" ? "Bogotá D.C." : a.ubicacion) },
  zona: { nombre: "Zona de distancia (por vía)", grupo: "Ubicación", valor: (a) => zona(a.distancia_vial_km) || "SIN", orden: ["CERCA", "MEDIA", "LEJOS", "SIN"],
    etiqueta: (k) => ({ CERCA: "Cerca (≤ 10 km)", MEDIA: "Media (10–20 km)", LEJOS: "Lejos (> 20 km)", SIN: "Sin ubicación" })[k] },
  estrato: { nombre: "Estrato", grupo: "El aspirante", valor: (a) => String(a.estrato), orden: ["1", "2", "3", "4", "5", "6"], etiqueta: (k) => `Estrato ${k}` },
  banda: { nombre: "Nivel ICFES", grupo: "El aspirante", valor: (a) => banda(a.icfes), orden: ["Bajo", "Medio", "Alto", "Superior"] },
  tipo_colegio: { nombre: "Tipo de colegio", grupo: "El aspirante", valor: (a) => a.tipo_colegio || "SIN", etiqueta: (k) => (k === "SIN" ? "Sin dato" : TIPO[k]) },
  genero: { nombre: "Género", grupo: "El aspirante", valor: (a) => a.genero || "SIN", etiqueta: (k) => (k === "SIN" ? "Sin dato" : GENERO[k]) },
};
const MEDIDAS = {
  cantidad: { nombre: "Aspirantes", calc: (l) => l.length, formato: (v) => String(v) },
  pct_real: { nombre: "% que se matriculó (real)", calc: (l) => { const r = l.filter((a) => a.matriculado_real === true || a.matriculado_real === false); return r.length ? r.filter((a) => a.matriculado_real).length / r.length : null; }, formato: (v) => pct(v), porcentaje: true },
  pct_si: { nombre: "% que se matricularía", calc: (l) => { const p = l.filter(conPrediccion); return p.length ? p.filter((a) => a.se_matricularia).length / p.length : null; }, formato: (v) => pct(v), porcentaje: true },
  prob_media: { nombre: "Probabilidad promedio", calc: (l) => media(l.filter(conPrediccion).map((a) => a.probabilidad_matricula)), formato: (v) => pct(v), porcentaje: true },
  km_via: { nombre: "Distancia promedio por vía", calc: (l) => media(l.map((a) => a.distancia_vial_km)), formato: (v) => km(v), unidad: "km" },
  km_recta: { nombre: "Distancia promedio en línea recta", calc: (l) => media(l.map((a) => a.distancia_campus_km)), formato: (v) => km(v), unidad: "km" },
  icfes: { nombre: "ICFES promedio", calc: (l) => media(l.map((a) => a.icfes)), formato: (v) => Math.round(v).toString() },
};
const EJES = {
  icfes: { nombre: "Puntaje ICFES", valor: (a) => a.icfes },
  prob: { nombre: "Probabilidad de matrícula", valor: (a) => a.probabilidad_matricula, porcentaje: true },
  km_via: { nombre: "Distancia por vía (km)", valor: (a) => a.distancia_vial_km },
  km_recta: { nombre: "Distancia en línea recta (km)", valor: (a) => a.distancia_campus_km },
  edad: { nombre: "Edad", valor: (a) => a.edad },
  vocacional: { nombre: "Puntaje vocacional (1 a 5)", valor: (a) => a.puntaje_vocacional },
};
const TIPOS = { barras: "Barras", horizontal: "Barras horizontales", dona: "Dona", linea: "Línea", dispersion: "Dispersión" };
const ICONO_TIPO = { barras: "barras", horizontal: "barras-h", dona: "dona", linea: "linea", dispersion: "puntos" };

const PREDETERMINADAS = [
  { id: "p-registros", titulo: "Registros en el tiempo", dim: "fecha", medida: "cantidad", tipo: "linea" },
  { id: "p-propension", titulo: "Propensión a matricularse", dim: "propension", medida: "cantidad", tipo: "dona" },
  { id: "p-canal", titulo: "¿Cómo conocieron la Universidad?", dim: "canal", medida: "cantidad", tipo: "horizontal" },
  { id: "p-distancias", titulo: "Distancia al campus por ubicación: línea recta y por vías", dim: "ubicacion", medidas: ["km_recta", "km_via"], tipo: "horizontal" },
  { id: "p-dist-prob", titulo: "Distancia por vía y probabilidad de matrícula", tipo: "dispersion", x: "km_via", y: "prob" },
  { id: "p-programa", titulo: "Probabilidad promedio por programa", dim: "programa", medida: "prob_media", tipo: "barras" },
  { id: "p-semestre", titulo: "Aspirantes por semestre de ingreso", dim: "periodo", medida: "cantidad", tipo: "barras" },
  { id: "p-seguimiento", titulo: "Seguimiento de los aspirantes", dim: "estado", medida: "cantidad", tipo: "horizontal" },
  { id: "p-icfes-prob", titulo: "Puntaje ICFES y probabilidad de matrícula", tipo: "dispersion", x: "icfes", y: "prob" },
];
// El jefe y el administrador ven además cómo se reparte el trabajo entre asesores
const POR_ASESOR = [{ id: "p-asesor", titulo: "Aspirantes por asesor", dim: "asesor", medida: "cantidad", tipo: "horizontal" },
  { id: "p-asesor-prob", titulo: "Probabilidad promedio por asesor", dim: "asesor", medida: "prob_media", tipo: "horizontal" }];
const predeterminadas = () => structuredClone(esJefe() ? [...PREDETERMINADAS.slice(0, 3), ...POR_ASESOR, ...PREDETERMINADAS.slice(3)] : PREDETERMINADAS);
const tiposPermitidos = (s) => (s.tipo === "dispersion" ? ["dispersion"] : s.dim === "fecha" ? ["linea", "barras"]
  : s.medidas ? ["horizontal", "barras"] : s.medida === "cantidad" ? ["horizontal", "barras", "dona"] : ["horizontal", "barras"]);

// ---------------------------------------------------------------------------- configuración guardada (por usuario)
const claveGuardado = () => `unicervantes-analitica-v1:${estado.usuario || "demo"}`;
function leerGraficas() {
  try {
    const g = JSON.parse(localStorage.getItem(claveGuardado()));
    // una gráfica guardada con un eje que ya no existe (p. ej. el antiguo riesgo de perder la beca) se descarta
    const validas = Array.isArray(g) ? g.filter((x) => x.tipo !== "dispersion" || (EJES[x.x] && EJES[x.y])) : [];
    if (validas.length) return esJefe() ? validas : validas.filter((x) => !DIMENSIONES[x.dim]?.soloJefe);
  } catch { /* sin almacenamiento */ }
  return predeterminadas();
}
function guardarGraficas() { try { localStorage.setItem(claveGuardado(), JSON.stringify(graficas)); } catch { /* sin almacenamiento */ } }

let graficas = [], instancias = new Map(), conTabla = new Set(), iniciada = false, pendiente = null, semestre = "";

// ---------------------------------------------------------------------------- datos
// Sin el semestre: la base de la comparación entre semestres. Con él: lo que muestran indicadores y gráficas.
function filtradosSinSemestre() {
  const prog = $("a-programa").value, dias = Number($("a-rango").value), ori = esJefe() ? $("a-origen").value : "";
  const desde = dias ? Date.now() - dias * 86400000 : 0;
  return estado.aspirantes.filter((a) => enMiCartera(a) && (!prog || a.programa === prog) && (!ori || a.origen === ori) && new Date(a.creado_en).getTime() >= desde);
}
const filtrados = () => filtradosSinSemestre().filter((a) => !semestre || a.periodo === semestre);
const semestres = () => [...new Set([...estado.modelo.reglas.periodos, ...estado.aspirantes.map((a) => a.periodo)])].filter(Boolean).sort();

// ---------------------------------------------------------------------------- semestres
function elegirSemestre(s) { semestre = s; pintarSemestres(); pintarKpis(); pintarComparacion(); pintarTodo(); }
function pintarSemestres() {
  const base = filtradosSinSemestre(), lista = semestres();
  if (semestre && !lista.includes(semestre)) semestre = "";
  $("a-semestres").replaceChildren(...[["", "Todos"], ...lista.map((s) => [s, s])].map(([valor, texto]) =>
    el("button", { type: "button", "aria-pressed": String(semestre === valor), onclick: () => elegirSemestre(valor),
      dataset: { vacio: String((valor ? base.filter((a) => a.periodo === valor).length : base.length) === 0) } },
      texto, el("span", { class: "insignia", text: (valor ? base.filter((a) => a.periodo === valor).length : base.length).toLocaleString("es-CO") }))));
}
function pintarComparacion() {
  const base = filtradosSinSemestre(), lista = semestres();
  const resumen = (l) => {
    const P = l.filter(conPrediccion), si = P.filter((a) => a.se_matricularia).length;
    return { n: l.length, pred: P.length, si, pctSi: P.length ? si / P.length : null, prob: media(P.map((a) => a.probabilidad_matricula)),
      via: media(l.map((a) => a.distancia_vial_km)), nuevos: l.filter((a) => a.estado === "NUEVO").length,
      reales: l.filter((a) => a.matriculado_real === true || a.matriculado_real === false).length, matriculo: l.filter((a) => a.matriculado_real).length,
      logrados: l.filter((a) => ["INSCRITO", "MATRICULADO"].includes(a.estado)).length };
  };
  const filas = lista.map((s) => ({ s, ...resumen(base.filter((a) => a.periodo === s)) }));
  const max = Math.max(1, ...filas.map((f) => f.n));
  const fila = (f, total = false) => el("tr", { class: total ? "fila-total" : "fila-enlace", dataset: { activo: String(!total && f.s === semestre) },
    onclick: total ? null : () => elegirSemestre(f.s === semestre ? "" : f.s) },
    el("th", { scope: "row", text: total ? "Todos" : f.s }),
    el("td", {}, el("div", { class: "mini-prob" }, el("b", { text: f.n }),
      !total && el("span", { class: "mini-barra" }, el("i", { estilo: { width: `${(100 * f.n) / max}%`, background: "var(--rojo)" } })))),
    el("td", { text: String(f.pred) }), el("td", { text: f.pctSi === null ? "—" : `${f.si} (${pct(f.pctSi)})` }),
    el("td", { text: f.prob === null ? "—" : pct(f.prob) }),
    el("td", { text: f.reales ? `${f.matriculo} (${pct(f.matriculo / f.reales)})` : "—" }),
    el("td", { text: f.via === null ? "—" : km(f.via) }),
    el("td", { text: String(f.nuevos) }), el("td", { text: String(f.logrados) }));
  $("a-comparacion-filas").replaceChildren(...filas.map((f) => fila(f)), fila({ s: "", ...resumen(base) }, true));
}

function agrupar(lista, s, maxCat) {
  const D = DIMENSIONES[s.dim], medidas = s.medidas || [s.medida], grupos = new Map();
  for (const a of lista) { const k = D.valor(a); if (k === null || k === undefined) continue; if (!grupos.has(k)) grupos.set(k, []); grupos.get(k).push(a); }
  let claves = [...grupos.keys()];
  let porMes = false;
  if (D.orden === "fecha") {
    claves.sort();
    porMes = claves.length > 1 && (new Date(claves.at(-1)) - new Date(claves[0])) / 86400000 > 120;
    if (porMes) {                                                  // se agrupa por mes y los meses vacíos quedan en 0
      const meses = new Map();
      for (const [k, l] of grupos) { const m = k.slice(0, 7); if (!meses.has(m)) meses.set(m, []); meses.get(m).push(...l); }
      grupos.clear(); meses.forEach((l, m) => grupos.set(m, l));
      const todos = [], [a0, m0] = claves[0].split("-").map(Number), [a1, m1] = claves.at(-1).split("-").map(Number);
      for (let a = a0, m = m0; a < a1 || (a === a1 && m <= m1); m === 12 ? (a++, m = 1) : m++) todos.push(`${a}-${String(m).padStart(2, "0")}`);
      claves = todos;
    } else if (claves.length > 1) {                                // días sin registros = 0 (la línea no salta)
      const todos = [], fin = new Date(`${claves.at(-1)}T12:00:00`);
      for (let d = new Date(`${claves[0]}T12:00:00`); d <= fin && todos.length < 400; d.setDate(d.getDate() + 1)) todos.push(d.toLocaleDateString("en-CA"));
      claves = todos;
    }
  } else if (Array.isArray(D.orden)) claves = D.orden.filter((k) => grupos.has(k) || (D.fijos || []).includes(k));
  else if (D.orden === "texto") claves.sort();
  else claves.sort((x, y) => grupos.get(y).length - grupos.get(x).length || String(x).localeCompare(String(y), "es"));
  let otros = [];
  if (D.orden !== "fecha" && !Array.isArray(D.orden) && claves.length > maxCat) {
    otros = claves.slice(maxCat - 1).flatMap((k) => grupos.get(k)); claves = claves.slice(0, maxCat - 1);
  }
  const fila = (clave, etiqueta, l) => ({ clave, etiqueta, n: l.length, valores: medidas.map((m) => MEDIDAS[m].calc(l)) });
  const etiquetaMes = (k) => new Date(`${k}-15T12:00:00`).toLocaleDateString("es-CO", { month: "short", year: "numeric" });
  const filas = claves.map((k) => fila(k, porMes ? etiquetaMes(k) : D.etiqueta ? D.etiqueta(k) : k, grupos.get(k) || []));
  if (otros.length) filas.push(fila("OTROS", "Otros", otros));
  return { filas, medidas, D };
}

// ---------------------------------------------------------------------------- Chart.js
const etiquetasDeValor = {                                         // número al final de cada barra (pocas barras)
  id: "etiquetasDeValor",
  afterDatasetsDraw(chart, _a, opciones) {
    if (!opciones || !opciones.activo) return;
    const { ctx } = chart, horizontal = chart.options.indexAxis === "y";
    ctx.save(); ctx.font = "600 12px 'Open Sans', sans-serif"; ctx.fillStyle = TINTA;
    chart.data.datasets.forEach((ds, i) => {
      const meta = chart.getDatasetMeta(i); if (meta.hidden) return;
      meta.data.forEach((barra, j) => {
        const v = ds.data[j]; if (v === null || v === undefined) return;
        const texto = opciones.formatos[i](v);
        if (horizontal) { ctx.textAlign = "left"; ctx.textBaseline = "middle"; ctx.fillText(texto, barra.x + 6, barra.y); }
        else { ctx.textAlign = "center"; ctx.textBaseline = "bottom"; ctx.fillText(texto, barra.x, barra.y - 4); }
      });
    });
    ctx.restore();
  },
};
function prepararChart() {
  const C = window.Chart; if (!C) return false;
  C.defaults.font.family = "'Open Sans', 'Segoe UI', Arial, sans-serif"; C.defaults.font.size = 12; C.defaults.color = TINTA;
  C.defaults.plugins.legend.display = false;
  Object.assign(C.defaults.plugins.tooltip, { backgroundColor: "#FFFFFF", titleColor: "#1A1A1A", bodyColor: TINTA, borderColor: "#EBDADA",
    borderWidth: 1, padding: 10, cornerRadius: 8, boxPadding: 4, usePointStyle: true });
  C.defaults.animation.duration = sinMovimiento() ? 0 : 550;
  C.register(etiquetasDeValor);
  return true;
}

function configuracion(s, lista) {
  if (s.tipo === "dispersion") {
    const X = EJES[s.x], Y = EJES[s.y];
    const puntos = lista.filter((a) => X.valor(a) !== null && X.valor(a) !== undefined && Y.valor(a) !== null && Y.valor(a) !== undefined)
      .map((a) => ({ x: X.valor(a), y: Y.valor(a), nombre: a.nombre }));
    const eje = (E) => ({ title: { display: true, text: E.nombre, color: TINTA, font: { weight: "600" } }, grid: { color: REJILLA }, border: { display: false },
      ticks: { callback: (v) => (E.porcentaje ? pct(v) : v) }, ...(E.porcentaje ? { min: 0, max: 1 } : {}) });
    return { vacio: puntos.length === 0, tabla: { columnas: ["Aspirante", X.nombre, Y.nombre], filas: puntos.map((p) => [p.nombre, X.porcentaje ? pct(p.x) : p.x, Y.porcentaje ? pct(p.y) : p.y]) },
      config: { type: "scatter", data: { datasets: [{ label: `${Y.nombre} según ${X.nombre.toLowerCase()}`, data: puntos, backgroundColor: SERIES[0],
        borderColor: "#FFFFFF", borderWidth: 1.5, pointRadius: 5, pointHoverRadius: 7 }] },
      options: { maintainAspectRatio: false, scales: { x: eje(X), y: eje(Y) },
        plugins: { tooltip: { callbacks: { title: (it) => it[0].raw.nombre, label: (it) => `${X.nombre}: ${X.porcentaje ? pct(it.raw.x) : it.raw.x} · ${Y.nombre}: ${Y.porcentaje ? pct(it.raw.y) : it.raw.y}` } } } } } };
  }
  const maxCat = s.tipo === "dona" ? 6 : s.medidas ? 10 : 12;
  const { filas, medidas, D } = agrupar(lista, s, maxCat);
  const vacio = filas.every((f) => f.n === 0);
  const formatos = medidas.map((m) => MEDIDAS[m].formato);
  const tabla = { columnas: [D.nombre, ...medidas.map((m) => MEDIDAS[m].nombre), ...(medidas[0] !== "cantidad" ? ["Aspirantes"] : [])],
    filas: filas.map((f) => [f.etiqueta, ...f.valores.map((v, i) => (v === null ? "—" : formatos[i](v))), ...(medidas[0] !== "cantidad" ? [f.n] : [])]) };
  const colorDe = (f, i) => (D.colores ? D.colores[f.clave] || GRIS : f.clave === "OTROS" ? GRIS : SERIES[i % SERIES.length]);
  if (s.tipo === "dona") {
    const total = filas.reduce((t, f) => t + (f.valores[0] || 0), 0);
    return { vacio, tabla, leyenda: filas.map((f, i) => ({ color: colorDe(f, i), texto: f.etiqueta, valor: `${f.valores[0]} · ${total ? pct(f.valores[0] / total) : "—"}` })),
      config: { type: "doughnut", data: { labels: filas.map((f) => f.etiqueta), datasets: [{ data: filas.map((f) => f.valores[0]),
        backgroundColor: filas.map(colorDe), borderColor: "#FFFFFF", borderWidth: 2, hoverOffset: 6 }] },
      options: { maintainAspectRatio: false, cutout: "62%", plugins: { tooltip: { callbacks: { label: (it) => ` ${it.label}: ${it.raw} (${total ? pct(it.raw / total) : "—"})` } } } } } };
  }
  const horizontal = s.tipo === "horizontal", linea = s.tipo === "linea", varias = medidas.length > 1;
  const porcentaje = MEDIDAS[medidas[0]].porcentaje;
  const datasets = medidas.map((m, i) => ({
    label: MEDIDAS[m].nombre, data: filas.map((f) => f.valores[i]),
    backgroundColor: linea ? SERIES[i] : varias ? SERIES[i] : filas.map((f) => (D.colores ? colorDe(f, 0) : f.clave === "OTROS" ? GRIS : SERIES[0])),
    borderColor: linea ? SERIES[i] : "#FFFFFF", borderWidth: linea ? 2 : 0, borderRadius: linea ? 0 : 4, borderSkipped: "start",
    maxBarThickness: 26, categoryPercentage: 0.72, barPercentage: varias ? 0.9 : 0.86,
    pointRadius: linea ? 4 : 0, pointHoverRadius: 6, pointBackgroundColor: SERIES[i], pointBorderColor: "#FFFFFF", pointBorderWidth: 1.5,
    tension: 0.25, fill: false, spanGaps: true,
  }));
  const valorEje = { grid: { color: REJILLA }, border: { display: false }, beginAtZero: true,
    ticks: { precision: 0, callback: (v) => (porcentaje ? pct(v) : MEDIDAS[medidas[0]].unidad ? `${v} km` : v) }, ...(porcentaje ? { max: 1 } : {}) };
  const catEje = { grid: { display: false }, border: { color: "#EBDADA" }, ticks: { autoSkip: !horizontal, maxRotation: 0,
    callback(v) { const t = this.getLabelForValue(v); return t.length > 26 ? `${t.slice(0, 25)}…` : t; } } };
  return { vacio, tabla, leyenda: varias ? medidas.map((m, i) => ({ color: SERIES[i], texto: MEDIDAS[m].nombre })) : null,
    config: { type: linea ? "line" : "bar", data: { labels: filas.map((f) => f.etiqueta), datasets },
      options: { maintainAspectRatio: false, indexAxis: horizontal ? "y" : "x", interaction: { mode: linea ? "index" : "nearest", intersect: !linea },
        layout: { padding: { right: horizontal ? 44 : 8, top: horizontal ? 0 : 18 } },
        scales: horizontal ? { x: valorEje, y: catEje } : { x: catEje, y: valorEje },
        plugins: { etiquetasDeValor: { activo: !linea && filas.length <= 12, formatos },
          tooltip: { callbacks: { label: (it) => ` ${it.dataset.label}: ${it.raw === null ? "—" : formatos[it.datasetIndex](it.raw)}` } } } } } };
}

// ---------------------------------------------------------------------------- tarjetas
function subtitulo(s) {
  if (s.tipo === "dispersion") return `Cada punto es un aspirante · ${EJES[s.x].nombre} contra ${EJES[s.y].nombre.toLowerCase()}`;
  return `${(s.medidas || [s.medida]).map((m) => MEDIDAS[m].nombre).join(" y ")} por ${DIMENSIONES[s.dim].nombre.toLowerCase()}`;
}
function crearTarjeta(s) {
  const tipos = tiposPermitidos(s);
  return el("section", { class: "tarjeta grafica", dataset: { id: s.id } },
    el("header", { class: "grafica-cabeza" },
      el("div", {}, el("h2", { text: s.titulo }), el("p", { class: "nota", text: subtitulo(s) })),
      el("div", { class: "grafica-acciones" },
        tipos.length > 1 && el("div", { class: "segmentado", role: "group", "aria-label": "Tipo de gráfica" }, tipos.map((t) =>
          el("button", { type: "button", title: TIPOS[t], "aria-label": TIPOS[t], "aria-pressed": String(s.tipo === t), dataset: { tipo: t },
            onclick: () => { s.tipo = t; guardarGraficas(); pintarTarjeta(s, true); } }, icono(ICONO_TIPO[t])))),
        el("button", { type: "button", class: "icono-boton", title: "Ver tabla", "aria-label": "Ver tabla", "aria-pressed": String(conTabla.has(s.id)),
          dataset: { accion: "tabla" }, onclick: () => { conTabla.has(s.id) ? conTabla.delete(s.id) : conTabla.add(s.id); pintarTarjeta(s, true); } }, icono("tabla")),
        el("button", { type: "button", class: "icono-boton", title: "Quitar gráfica", "aria-label": `Quitar ${s.titulo}`,
          onclick: () => quitarGrafica(s.id) }, icono("x")))),
    el("div", { class: "grafica-cuerpo" }),
    el("ul", { class: "leyenda", hidden: true }));
}

function pintarTarjeta(s, rehacer = false) {
  const tarjeta = document.querySelector(`.grafica[data-id="${s.id}"]`); if (!tarjeta) return;
  const { config, vacio, tabla, leyenda } = configuracion(s, filtrados());
  tarjeta.querySelectorAll(".segmentado button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.tipo === s.tipo)));
  tarjeta.querySelector('[data-accion="tabla"]').setAttribute("aria-pressed", String(conTabla.has(s.id)));
  const cuerpo = tarjeta.querySelector(".grafica-cuerpo"), ul = tarjeta.querySelector(".leyenda");
  const anterior = instancias.get(s.id);
  const verTabla = conTabla.has(s.id);
  if (vacio || verTabla || rehacer || !anterior || anterior.config.type !== config.type) {
    if (anterior) { anterior.destroy(); instancias.delete(s.id); }
    cuerpo.replaceChildren();
  }
  ul.hidden = verTabla || vacio || !leyenda;
  if (leyenda) ul.replaceChildren(...leyenda.map((l) => el("li", {}, el("i", { estilo: { background: l.color } }), el("span", { text: l.texto }), l.valor && el("b", { text: l.valor }))));
  if (vacio) { cuerpo.replaceChildren(el("div", { class: "vacio-grafica" }, icono("barras"), el("p", { text: "Sin datos para estos filtros todavía." }))); return; }
  if (verTabla) {
    cuerpo.replaceChildren(el("div", { class: "tabla-contenedor compacta" }, el("table", {},
      el("thead", {}, el("tr", {}, tabla.columnas.map((c) => el("th", { scope: "col", text: c })))),
      el("tbody", {}, tabla.filas.slice(0, 200).map((f) => el("tr", {}, f.map((v) => el("td", { text: String(v) }))))))));
    return;
  }
  const actual = instancias.get(s.id);
  if (actual) { actual.data = config.data; actual.options = config.options; actual.update(); return; }
  const lienzo = el("canvas", { role: "img", "aria-label": `${s.titulo}. ${subtitulo(s)}. Use el botón de tabla para ver los números.` });
  cuerpo.replaceChildren(el("div", { class: "lienzo" }, lienzo));
  instancias.set(s.id, new window.Chart(lienzo, config));
}

function pintarTodo() {
  const cont = $("graficas");
  for (const [id, ch] of instancias) if (!graficas.some((g) => g.id === id)) { ch.destroy(); instancias.delete(id); }
  const ids = [...cont.children].map((t) => t.dataset.id);
  if (ids.join() !== graficas.map((g) => g.id).join()) {
    for (const ch of instancias.values()) ch.destroy();
    instancias.clear();
    cont.replaceChildren(...graficas.map(crearTarjeta));
  }
  graficas.forEach((g) => pintarTarjeta(g));
}

function quitarGrafica(id) {
  const g = graficas.find((x) => x.id === id);
  graficas = graficas.filter((x) => x.id !== id); guardarGraficas(); pintarTodo();
  avisar(`Se quitó «${g.titulo}».`, "info", { accion: { texto: "Deshacer", fn: () => { graficas.push(g); guardarGraficas(); pintarTodo(); } } });
}

// ---------------------------------------------------------------------------- indicadores
function pintarKpis() {
  const L = filtrados(), P = L.filter(conPrediccion), si = P.filter((a) => a.se_matricularia).length;
  animarNumero($("k-registrados"), L.length);
  animarNumero($("k-predichos"), P.length);
  $("k-predichos-sub").textContent = L.length ? `${pct(P.length / L.length)} de los registrados` : "Sin registros";
  animarNumero($("k-si"), P.length ? si / P.length : null, (v) => pct(v));
  $("k-si-sub").textContent = P.length ? `${si} de ${P.length} con predicción` : "Sin predicciones";
  animarNumero($("k-prob"), media(P.map((a) => a.probabilidad_matricula)), (v) => pct(v));
  const via = media(L.map((a) => a.distancia_vial_km)), recta = media(L.map((a) => a.distancia_campus_km));
  animarNumero($("k-via"), via, (v) => km(v));
  $("k-via-sub").textContent = recta === null ? "Sin ubicación" : `${km(recta)} en línea recta`;
}
export function pintarEstadoVivo() {
  const e = $("a-vivo");
  e.dataset.estado = estado.demo ? "demo" : estado.enVivo ? "vivo" : "sin";
  e.querySelector("span").textContent = estado.demo ? "Modo demostración"
    : `${estado.enVivo ? "En vivo" : "Sin tiempo real (se actualiza cada minuto)"}${estado.actualizado ? ` · ${hace(estado.actualizado)}` : ""}`;
}

// ---------------------------------------------------------------------------- agregar gráfica
function abrirDialogo() {
  const d = $("dialogo-grafica");
  $("g-tipo").value = "barras"; $("g-dim").value = "canal"; $("g-medida").value = "cantidad"; $("g-x").value = "icfes"; $("g-y").value = "prob";
  $("g-titulo").value = ""; actualizarDialogo();
  d.showModal();
}
function sugerencia() {
  if ($("g-tipo").value === "dispersion") return `${EJES[$("g-y").value].nombre} según ${EJES[$("g-x").value].nombre.toLowerCase()}`;
  return `${MEDIDAS[$("g-medida").value].nombre} por ${DIMENSIONES[$("g-dim").value].nombre.toLowerCase()}`;
}
function actualizarDialogo() {
  const disp = $("g-tipo").value === "dispersion";
  $("g-agrupado").hidden = disp; $("g-ejes").hidden = !disp;
  if ($("g-tipo").value === "dona") $("g-medida").value = "cantidad";
  $("g-medida").disabled = $("g-tipo").value === "dona";
  if ($("g-tipo").value === "linea") $("g-dim").value = "fecha";
  $("g-titulo").placeholder = sugerencia();
}
function agregarDesdeDialogo(ev) {
  ev.preventDefault();
  const tipo = $("g-tipo").value, titulo = $("g-titulo").value.trim() || sugerencia();
  const s = tipo === "dispersion" ? { id: `g-${Date.now()}`, titulo, tipo, x: $("g-x").value, y: $("g-y").value }
    : { id: `g-${Date.now()}`, titulo, tipo, dim: $("g-dim").value, medida: $("g-medida").value };
  if (!tiposPermitidos(s).includes(s.tipo)) s.tipo = tiposPermitidos(s)[0];
  graficas.unshift(s); guardarGraficas(); $("dialogo-grafica").close();
  pintarTodo(); avisar(`Se agregó «${titulo}».`, "exito", { duracion: 2500 });
  document.querySelector(`.grafica[data-id="${s.id}"]`)?.scrollIntoView({ behavior: sinMovimiento() ? "auto" : "smooth", block: "center" });
}

// ---------------------------------------------------------------------------- vista
export function mostrarAnalitica() {
  if (!iniciada) iniciar();
  pintarSemestres(); pintarComparacion();
  if (!window.Chart) { $("graficas").replaceChildren(el("p", { class: "error-general", text: "No se pudo cargar la librería de gráficas (Chart.js). Revise la conexión y recargue." })); return; }
  pintarKpis(); pintarEstadoVivo(); pintarTodo();
  animarEntrada($("graficas"));
}
export function actualizarAnalitica() {
  clearTimeout(pendiente);
  pendiente = setTimeout(() => {
    if (!$("vista-analitica").hidden && window.Chart) { pintarSemestres(); pintarComparacion(); pintarKpis(); pintarTodo(); }
    pintarEstadoVivo();
  }, 250);
}

function iniciar() {
  iniciada = true;
  prepararChart();
  graficas = leerGraficas();
  ["a-programa", "a-rango", "a-origen"].forEach((id) => $(id).addEventListener("change", () => { pintarSemestres(); pintarComparacion(); pintarKpis(); pintarTodo(); }));
  $("a-agregar").addEventListener("click", abrirDialogo);
  $("a-restaurar").addEventListener("click", () => {
    graficas = predeterminadas(); conTabla.clear(); guardarGraficas(); pintarTodo();
    avisar("Se restauraron las gráficas predeterminadas.", "info", { duracion: 2500 });
  });
  const grupos = ["El aspirante", "Captación y seguimiento", "Ubicación", "Predicción y resultado", "Tiempo"];
  $("g-dim").append(...grupos.map((g) => el("optgroup", { label: g }, Object.entries(DIMENSIONES)
    .filter(([, d]) => d.grupo === g && (!d.soloJefe || esJefe())).map(([k, d]) => el("option", { value: k, text: d.nombre })))));
  $("g-medida").append(...Object.entries(MEDIDAS).map(([k, m]) => el("option", { value: k, text: m.nombre })));
  for (const id of ["g-x", "g-y"]) $(id).append(...Object.entries(EJES).map(([k, e]) => el("option", { value: k, text: e.nombre })));
  $("g-tipo").append(...Object.entries(TIPOS).map(([k, t]) => el("option", { value: k, text: t })));
  ["g-tipo", "g-dim", "g-medida", "g-x", "g-y"].forEach((id) => $(id).addEventListener("change", actualizarDialogo));
  $("form-grafica").addEventListener("submit", agregarDesdeDialogo);
  $("g-cancelar").addEventListener("click", () => $("dialogo-grafica").close());
  setInterval(pintarEstadoVivo, 30000);
}
