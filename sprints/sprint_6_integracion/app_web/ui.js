// Utilidades de interfaz: crear elementos, formatos en español de Colombia, avisos emergentes, animaciones y catálogos.

export const $ = (id) => document.getElementById(id);

export function el(etiqueta, atributos = {}, ...hijos) {
  const e = document.createElement(etiqueta);
  for (const [k, v] of Object.entries(atributos)) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") e.className = v;
    else if (k === "text") e.textContent = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else if (k === "dataset") Object.assign(e.dataset, v);
    else if (k === "estilo") Object.assign(e.style, v);           // CSSOM: permitido por la CSP (no hay estilos en línea)
    else e.setAttribute(k, v === true ? "" : v);
  }
  for (const h of hijos.flat()) if (h !== null && h !== undefined && h !== false) e.append(h instanceof Node ? h : String(h));
  return e;
}

// Ícono del sprite de index.html
export function icono(nombre, clase = "ic") {
  const s = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  s.setAttribute("class", clase); s.setAttribute("aria-hidden", "true");
  const u = document.createElementNS("http://www.w3.org/2000/svg", "use");
  u.setAttribute("href", `#i-${nombre}`); s.append(u);
  return s;
}

// ---------------------------------------------------------------------------- formatos
export const cop = (v) => (v === null || v === undefined ? "—" : "$" + Math.round(v).toLocaleString("es-CO"));
export const pct = (v, d = 0) => (v === null || v === undefined ? "—" : (v * 100).toFixed(d).replace(".", ",") + "%");
export const km = (v, d = 1) => (v === null || v === undefined ? "—" : `${Number(v).toFixed(d).replace(".", ",")} km`);
export const coma = (v) => String(v).replace(".", ",");
export const fecha = (iso) => new Date(iso).toLocaleString("es-CO", { timeZone: "America/Bogota", dateStyle: "medium", timeStyle: "short" });
export const dia = (iso) => new Date(iso).toLocaleDateString("en-CA", { timeZone: "America/Bogota" });   // AAAA-MM-DD en Bogotá
export function hace(iso) {
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 60) return "hace un momento";
  if (s < 3600) return `hace ${Math.floor(s / 60)} min`;
  if (s < 86400) return `hace ${Math.floor(s / 3600)} h`;
  return fecha(iso);
}
export const iniciales = (nombre) => nombre.trim().split(/\s+/).filter((p) => /^[\p{L}]/u.test(p)).slice(0, 2).map((p) => p[0].toUpperCase()).join("") || "?";

// ---------------------------------------------------------------------------- movimiento
export const sinMovimiento = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// Cuenta desde el valor actual hasta el nuevo (KPIs)
export function animarNumero(nodo, valor, formato = (v) => Math.round(v).toLocaleString("es-CO")) {
  if (valor === null || valor === undefined || Number.isNaN(valor)) { nodo.textContent = "—"; nodo.dataset.valor = ""; return; }
  const desde = Number(nodo.dataset.valor || 0);
  nodo.dataset.valor = valor;
  nodo.textContent = formato(valor);                             // el valor final queda puesto aunque no se anime
  if (sinMovimiento() || desde === valor || document.hidden) return;
  const t0 = performance.now(), dur = 650;
  setTimeout(() => { if (nodo.dataset.valor === String(valor)) nodo.textContent = formato(valor); }, dur + 80);   // por si el navegador pausa la animación
  const paso = (t) => {
    if (nodo.dataset.valor !== String(valor)) return;             // llegó otro valor mientras animaba
    const p = Math.min(1, Math.max(0, (t - t0) / dur)), suave = 1 - (1 - p) ** 3;
    nodo.textContent = formato(desde + (valor - desde) * suave);
    if (p < 1) requestAnimationFrame(paso); else nodo.textContent = formato(valor);
  };
  requestAnimationFrame(paso);
}

// Entrada escalonada de los hijos de una vista
export function animarEntrada(contenedor) {
  if (sinMovimiento()) return;
  contenedor.classList.remove("entrando");
  [...contenedor.children].forEach((h, i) => h.style.setProperty("--i", Math.min(i, 8)));
  void contenedor.offsetWidth;                                   // reinicia la animación
  contenedor.classList.add("entrando");
}

// ---------------------------------------------------------------------------- avisos emergentes
export function avisar(texto, tipo = "info", { duracion = 4200, accion = null } = {}) {
  const zona = $("avisos-emergentes");
  const nombreIcono = { exito: "check", error: "alerta", info: "info", vivo: "vivo" }[tipo] || "info";
  const caja = el("div", { class: "aviso-emergente", dataset: { tipo }, role: tipo === "error" ? "alert" : "status" },
    icono(nombreIcono), el("p", { text: texto }),
    accion && el("button", { type: "button", class: "enlace", text: accion.texto, onclick: () => { accion.fn(); cerrar(); } }),
    el("button", { type: "button", class: "cerrar", "aria-label": "Cerrar aviso", onclick: () => cerrar() }, icono("x")));
  const cerrar = () => { caja.classList.add("saliendo"); setTimeout(() => caja.remove(), sinMovimiento() ? 0 : 220); };
  zona.append(caja);
  while (zona.children.length > 4) zona.firstElementChild.remove();
  if (duracion) setTimeout(cerrar, duracion);
  return cerrar;
}

// Botón en espera (con giro) mientras dura una promesa
export async function conEspera(boton, texto, fn) {
  const original = boton.innerHTML;
  boton.disabled = true; boton.setAttribute("aria-busy", "true");
  boton.replaceChildren(el("span", { class: "giro", "aria-hidden": "true" }), texto);
  try { return await fn(); }
  finally { boton.disabled = false; boton.removeAttribute("aria-busy"); boton.innerHTML = original; }
}

// ---------------------------------------------------------------------------- catálogos
export const PROGRAMAS = { AD: "Ingeniería en Analítica de Datos", SSIA: "Ingeniería en Sistemas de Software e IA" };
export const CANALES = { EXPOESTUDIANTES: "Feria ExpoEstudiantes", SITIO_WEB: "Sitio web / formulario de preinscripción",
  REDES_SOCIALES: "Redes sociales", REFERIDO: "Referido por un estudiante o egresado", CAMPUS_DAY: "Campus Day / Familia Fest",
  LLAMADA_WHATSAPP: "Llamada o WhatsApp de un asesor", INMERSION: "Programa de inmersión universitaria",
  COLEGIO_CONVENIO: "Charla en su colegio (convenio)", OTRO: "Otro medio" };
export const DETALLE_CANAL = { EXPOESTUDIANTES: "¿En qué feria o ciudad?", REFERIDO: "¿Quién lo refirió?", CAMPUS_DAY: "¿En qué fecha?",
  COLEGIO_CONVENIO: "Nombre del colegio", REDES_SOCIALES: "¿Qué red social?", OTRO: "¿Cuál?" };
export const ESTADOS = { NUEVO: "Nuevo", CONTACTADO: "Contactado", INTERESADO: "Interesado", INSCRITO: "Inscrito", MATRICULADO: "Matriculado", DESCARTADO: "Descartado" };
export const ETIQUETA_ESTADO = { ...ESTADOS, NO_MATRICULADO: "No se matriculó" };   // la base simulada trae el resultado real
export const NOMBRE_BECA = { SABER_11: "Saber 11", MI_VOCACION: "Mi Vocación", NINGUNA: "Sin beca" };
export const TIPO = { PUBLICO: "Público", PRIVADO: "Privado", TECNICO: "Técnico" };
export const MEDIOS = { WHATSAPP: "WhatsApp", LLAMADA: "Llamada", CORREO: "Correo" };
export const REGIMEN = { CONTRIBUTIVO: "Contributivo", SUBSIDIADO: "Subsidiado", ESPECIAL: "Especial o de excepción" };
export const PROPENSION = { ALTA: "Alta", MEDIA: "Media", BAJA: "Baja" };
export const GENERO = { F: "Femenino", M: "Masculino" };
export const ZONAS = { CERCA: "Cerca", MEDIA: "Media", LEJOS: "Lejos" };

// Dirección de Bogotá a partir de sus partes (la usan el registro de la app y la encuesta del aspirante)
export const LETRAS = ["", "A", "B", "C", "D", "E", "F", "G", "H"];
const VIA_CALLE = ["Calle", "Avenida Calle", "Diagonal"];          // "Sur" va con la calle; "Este" con la carrera
export function armarDireccion({ tipo, numero, letra = "", bis = "", cuadrante = "", cruce, letraCruce = "", placa }) {
  if (!tipo || !numero || !cruce || !placa) return "";
  const vaConVia = (cuadrante === "Sur" && VIA_CALLE.includes(tipo)) || (cuadrante === "Este" && !VIA_CALLE.includes(tipo));
  const via = [tipo, numero + letra, bis, vaConVia ? cuadrante : ""].filter(Boolean).join(" ");
  return `${via} # ${cruce}${letraCruce}-${placa}${cuadrante && !vaConVia ? " " + cuadrante : ""}`;
}

// Paleta de gráficas (validada con el validador de dataviz en modo claro, fondo blanco: pasa CVD y visión normal; los
// tonos claros llevan etiquetas o la vista de tabla). Orden fijo: el color sigue a la categoría, nunca al puesto.
export const SERIES = ["#B5121B", "#2A78D6", "#1BAF7A", "#C99A00", "#6250D6", "#E87BA4"];
export const ESTADO_COLOR = { ALTA: "#1E7A3C", MEDIA: "#C99A00", BAJA: "#B5121B", SIN: "#B9B1B1" };
