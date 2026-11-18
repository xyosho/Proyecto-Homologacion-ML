// SPRINT 6 — App web de ingreso de aspirantes (Vercel + Supabase).
// El personal de Admisiones inicia sesión (Supabase Auth), registra aspirantes, predice su matrícula en el navegador
// con modelo.js (el mismo modelo del proyecto), hace el seguimiento y mira la analítica en vivo. Los datos están en
// aspirante_registrado, que solo el personal autorizado puede leer o escribir (RLS, sql/08_app_aspirantes.sql).
// Roles: el asesor trabaja sus aspirantes; el jefe de admisiones ve todos y el asesor de cada uno (Equipo); el
// administrador además crea usuarios y cambia roles (Usuarios); la psicóloga vocacional ve su agenda y la entrevista
// vocacional de los aspirantes a los que se les envió (psicologia.js). RLS en Supabase hace cumplir cada rol.
// En localhost, con ?demo (o ?demo=asesor, ?demo=jefe), funciona sin Supabase y guarda en este navegador.
import { crearModelo } from "./modelo.js";
import { $, el, icono, cop, pct, km, coma, fecha, hace, iniciales, avisar, conEspera, animarNumero, animarEntrada, sinMovimiento,
  PROGRAMAS, CANALES, ESTADOS, ETIQUETA_ESTADO, NOMBRE_BECA, TIPO, MEDIOS, REGIMEN, PROPENSION, GENERO, ZONAS, ESTADO_COLOR } from "./ui.js";
import { estado, ErrorApp, traducirError, almacenSupabase, almacenDemo, cargarAspirantes, reemplazar, quitar, escucharCambios,
  dejarDeEscuchar, banda, zona, ubicacionDe, predecirYGuardar, ROLES, esJefe, esAdmin, nombreAsesor, cargarEquipo, esSimulado,
  traspasadoPorMi, enMiCartera, escucharDemo, esPsicologa, ESTADO_ENTREVISTA, conEntrevista, urlEntrevista } from "./datos.js";
import { iniciarPsicologia, cargarPsicologia, escucharPsicologia, pintarAgenda, pintarVocacionales, pintarFichaVocacional } from "./psicologia.js";
import { iniciarPerfil, pintarPerfil, pintarUsuarioMenu } from "./perfil.js";
import { iniciarFormulario, mostrarFormulario } from "./formulario.js";
import { iniciarEquipo, pintarEquipo, pintarUsuarios, llenarSelectoresAsesor } from "./equipo.js";
import { mostrarAnalitica, actualizarAnalitica, pintarEstadoVivo } from "./analitica.js";
import { pintarRuta } from "./mapa.js";
import { bloqueQR, nombreArchivoQR } from "./qr.js";
import { iniciarEncuestas, pintarEncuestas, cargarEnlaces } from "./encuestas.js";

const VISTAS = { resumen: "Resumen", registrar: "Registrar aspirante", encuestas: "Enlaces de encuesta", aspirantes: "Aspirantes", analitica: "Analítica", equipo: "Equipo", usuarios: "Usuarios", perfil: "Mi perfil",
  agenda: "Agenda", vocacionales: "Aspirantes vocacionales" };
const SOLO_PSICOLOGA = ["agenda", "vocacionales", "vocacional"], PSICOLOGA_PUEDE = [...SOLO_PSICOLOGA, "perfil"];
const TITULO_APP = "Ingreso de aspirantes";

// ---------------------------------------------------------------------------- páginas de error
const ERRORES = {
  404: { icono: "brujula", titulo: "Esta página no existe", texto: "La dirección no corresponde a ninguna sección de la app. Puede que el enlace esté mal escrito." },
  aspirante: { icono: "usuario", titulo: "No encontramos a este aspirante", texto: "Puede que lo hayan eliminado o que el enlace esté incompleto." },
  conexion: { icono: "sin-red", titulo: "No pudimos conectar con la base de datos", texto: "Revise la conexión a internet. Los datos están a salvo en Supabase; vuelva a intentar en un momento." },
  permiso: { icono: "candado", titulo: "Su cuenta no tiene permiso", texto: "Inició sesión, pero su cuenta no está en la lista del personal autorizado. Pida acceso al administrador." },
  rol: { icono: "candado", titulo: "Esta sección no es para su rol", texto: "La ve el jefe de admisiones o el administrador. Si la necesita, pida al administrador que cambie su rol." },
  general: { icono: "alerta", titulo: "Algo salió mal", texto: "Ocurrió un error inesperado. Intente de nuevo; si se repite, recargue la página." },
};
function paginaError(tipo, { detalle = "", acciones = null, codigo = null } = {}) {
  const e = ERRORES[tipo] || ERRORES.general;
  const botones = acciones || [
    { texto: "Ir al resumen", clase: "primario", fn: () => { location.hash = "#/resumen"; } },
    { texto: "Volver", clase: "secundario", fn: () => history.back() },
  ];
  return el("div", { class: "pagina-error", dataset: { tipo } },
    el("div", { class: "error-ilustracion", "aria-hidden": "true" }, el("span", { class: "error-codigo", text: codigo ?? (tipo === "404" ? "404" : "") }), icono(e.icono, "ic error-icono")),
    el("h1", { tabindex: "-1", text: e.titulo }), el("p", { class: "texto-suave", text: e.texto }),
    detalle && el("details", { class: "error-detalle" }, el("summary", { text: "Detalle técnico" }), el("code", { text: detalle })),
    el("div", { class: "acciones centradas" }, botones.map((b) => el("button", { type: "button", class: b.clase, onclick: b.fn }, b.texto))));
}
function mostrarErrorEnApp(tipo, opciones) {
  document.querySelectorAll("[data-vista]").forEach((s) => { s.hidden = s.id !== "vista-error"; });
  $("vista-error").replaceChildren(paginaError(tipo, opciones));
  animarEntrada($("vista-error"));
  marcarNavegacion(null);
  document.title = `${(ERRORES[tipo] || ERRORES.general).titulo} · ${TITULO_APP}`;
  $("vista-error").querySelector("h1")?.focus({ preventScroll: true });
}
function pantallaError(tipo, opciones) {                         // antes de que la app exista (arranque)
  $("cargando").hidden = true; $("app").hidden = true; $("vista-acceso").hidden = true;
  $("pantalla-error").hidden = false;
  $("pantalla-error").replaceChildren(el("img", { src: "logo_unicervantes.png", alt: "Unicervantes", class: "logo-error" }), paginaError(tipo, opciones));
}
const recargar = { texto: "Recargar la página", clase: "primario", fn: () => location.reload() };

// ---------------------------------------------------------------------------- navegación
function ruta() {
  const h = decodeURIComponent(location.hash.replace(/^#\/?/, ""));
  if (h === "") return { vista: "resumen" };
  if (h.startsWith("aspirante/")) return { vista: "detalle", id: h.slice("aspirante/".length) };
  if (h.startsWith("vocacional/")) return { vista: "vocacional", id: h.slice("vocacional/".length) };
  return h in VISTAS ? { vista: h } : { vista: "404" };
}
function marcarNavegacion(vista) {
  document.querySelectorAll("[data-nav]").forEach((a) => {
    if (a.dataset.nav === vista) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  });
  // "Más" de la barra inferior queda marcado en las secciones que solo están en el menú completo
  if (["encuestas", "equipo", "usuarios", "perfil"].includes(vista)) $("barra-mas").setAttribute("aria-current", "page"); else $("barra-mas").removeAttribute("aria-current");
}
function navegar({ animar = true } = {}) {
  const r = ruta();
  if (r.vista === "404") { mostrarErrorEnApp("404"); return; }
  // La psicóloga entra a su agenda; las secciones del asesor no son para su rol (y las suyas no son para los demás)
  if (esPsicologa() && r.vista === "resumen") { history.replaceState(null, "", "#/agenda"); navegar({ animar }); return; }
  if (esPsicologa() ? !PSICOLOGA_PUEDE.includes(r.vista) : SOLO_PSICOLOGA.includes(r.vista)) { mostrarErrorEnApp("rol"); return; }
  if ((r.vista === "equipo" && !esJefe()) || (r.vista === "usuarios" && !esAdmin())) { mostrarErrorEnApp("rol"); return; }
  const necesitaDatos = !["registrar", "encuestas", "usuarios", "perfil"].includes(r.vista);
  if (necesitaDatos && estado.errorCarga) {
    mostrarErrorEnApp(estado.errorCarga.tipo === "permiso" ? "permiso" : "conexion", {
      detalle: estado.errorCarga.message, acciones: [{ texto: "Reintentar", clase: "primario", fn: reintentarCarga }, recargar] });
    return;
  }
  const id = `vista-${r.vista}`;
  document.querySelectorAll("[data-vista]").forEach((s) => { s.hidden = s.id !== id; });
  marcarNavegacion(r.vista === "detalle" ? "aspirantes" : r.vista === "vocacional" ? "vocacionales" : r.vista);
  if (r.vista === "resumen") pintarResumen();
  if (r.vista === "aspirantes") pintarLista();
  if (r.vista === "detalle") { if (!pintarDetalle(r.id)) return; }
  if (r.vista === "registrar") mostrarFormulario();
  if (r.vista === "encuestas") pintarEncuestas();
  if (r.vista === "analitica") mostrarAnalitica();
  if (r.vista === "equipo") pintarEquipo();
  if (r.vista === "usuarios") pintarUsuarios();
  if (r.vista === "perfil") pintarPerfil();
  if (r.vista === "agenda") pintarAgenda();
  if (r.vista === "vocacionales") pintarVocacionales();
  if (r.vista === "vocacional") pintarFichaVocacional(r.id);
  document.title = `${VISTAS[r.vista] || "Aspirante"} · ${TITULO_APP}`;
  if (animar) { animarEntrada($(id)); window.scrollTo(0, 0); }
  $(id).querySelector("h1")?.focus({ preventScroll: true });
}
async function reintentarCarga() {
  $("vista-error").querySelectorAll("button").forEach((b) => { b.disabled = true; });
  await cargarAspirantes();
  if (estado.errorCarga) avisar(estado.errorCarga.message, "error"); else avisar("Datos cargados de nuevo.", "exito", { duracion: 2000 });
  navegar();
}

// ---------------------------------------------------------------------------- piezas comunes
const avatar = (nombre, clase = "avatar") => el("span", { class: clase, "aria-hidden": "true", text: iniciales(nombre) });
const chip = (texto, tono, conIcono = null) => el("span", { class: "chip", dataset: { tono: tono || "" } }, conIcono && icono(conIcono, "ic ic-chico"), texto);
const chipPropension = (a) => (a.propension ? chip(PROPENSION[a.propension], a.propension) : chip("Sin predecir", "SIN"));
function esqueletoFilas(n, columnas) {
  return Array.from({ length: n }, () => el("tr", { class: "fila-esqueleto" }, Array.from({ length: columnas }, () => el("td", {}, el("span", { class: "esqueleto" })))));
}

// ---------------------------------------------------------------------------- vista: resumen
function saludo() {
  const h = Number(new Date().toLocaleString("en-US", { timeZone: "America/Bogota", hour: "numeric", hour12: false }));
  return h < 12 ? "Buenos días" : h < 19 ? "Buenas tardes" : "Buenas noches";
}
function pintarResumen() {
  $("r-saludo").textContent = `${saludo()} · ${new Date().toLocaleDateString("es-CO", { timeZone: "America/Bogota", weekday: "long", day: "numeric", month: "long" })}`;
  const L = estado.aspirantes, cargando = !estado.cargados;
  document.querySelectorAll("#vista-resumen .kpi").forEach((k) => { k.dataset.cargando = cargando ? "si" : "no"; });
  if (cargando) return;
  const P = L.filter((a) => a.propension), si = P.filter((a) => a.se_matricularia).length;
  const app = L.filter((a) => !esSimulado(a) && enMiCartera(a)), sim = L.filter(esSimulado).length;
  const semana = app.filter((a) => Date.now() - new Date(a.creado_en).getTime() < 7 * 86400000).length;
  animarNumero($("rk-total"), L.length);
  $("rk-total-sub").textContent = sim ? `${app.length} en la app · ${sim.toLocaleString("es-CO")} de la base simulada` : `${semana} en los últimos 7 días`;
  animarNumero($("rk-pred"), P.length); $("rk-pred-sub").textContent = L.length ? `${pct(P.length / L.length)} de los registrados` : "Sin registros";
  animarNumero($("rk-si"), P.length ? si / P.length : null, (v) => pct(v)); $("rk-si-sub").textContent = P.length ? `${si} de ${P.length} con predicción` : "Sin predicciones";
  const nuevos = app.filter((a) => a.estado === "NUEVO").length;
  animarNumero($("rk-nuevos"), nuevos); $("rk-nuevos-sub").textContent = nuevos ? "aún sin contactar" : "todos contactados";

  // barra de propensión (100% apilada, con etiquetas)
  const c = { ALTA: 0, MEDIA: 0, BAJA: 0 }; P.forEach((a) => { c[a.propension] += 1; });
  $("r-propension").replaceChildren(...(P.length ? ["ALTA", "MEDIA", "BAJA"].filter((k) => c[k]).map((k) => {
    const s = el("span", { class: "apilada-segmento", title: `${PROPENSION[k]}: ${c[k]}` });
    s.style.flexGrow = c[k]; s.style.background = ESTADO_COLOR[k];
    return s;
  }) : [el("span", { class: "apilada-vacia", text: "Sin predicciones todavía" })]));
  $("r-propension-leyenda").replaceChildren(...["ALTA", "MEDIA", "BAJA"].map((k) => el("li", {},
    el("i", { estilo: { background: ESTADO_COLOR[k] } }), `${PROPENSION[k]} `, el("b", { text: `${c[k]}${P.length ? ` · ${pct(c[k] / P.length)}` : ""}` }))));

  const prioridad = app.filter((a) => a.propension === "MEDIA" && a.estado === "NUEVO")
    .sort((x, y) => Math.abs(x.probabilidad_matricula - 0.5) - Math.abs(y.probabilidad_matricula - 0.5)).slice(0, 6);
  const filaPersona = (a, derecha) => el("li", {}, el("a", { href: `#/aspirante/${a.id}`, class: "persona" }, avatar(a.nombre),
    el("span", { class: "persona-texto" }, el("b", { text: a.nombre }), el("small", { text: [a.programa, a.ubicacion, esJefe() && nombreAsesor(a.asesor_id)].filter(Boolean).join(" · ") })), derecha));
  $("prioridad").replaceChildren(...(prioridad.length ? prioridad.map((a) => filaPersona(a,
    el("span", { class: "persona-dato" }, el("b", { text: pct(a.probabilidad_matricula) }), el("small", { text: a.telefono || a.correo || "sin contacto" }))))
    : [el("li", { class: "vacio-lista" }, icono("check"), "No hay indecisos pendientes de contactar.")]));
  const recientes = app.slice().sort((x, y) => y.creado_en.localeCompare(x.creado_en)).slice(0, 6);
  $("recientes").replaceChildren(...(recientes.length ? recientes.map((a) => filaPersona(a,
    el("span", { class: "persona-dato" }, chipPropension(a), el("small", { text: hace(a.creado_en) }))))
    : [el("li", { class: "vacio-lista" }, icono("usuario-mas"), el("span", {}, "Todavía no hay aspirantes. ", el("a", { href: "#/registrar", text: "Registre el primero" }), "."))]));
}

// ---------------------------------------------------------------------------- vista: aspirantes
let limite = 100;
function filtrados() {
  const q = $("f-buscar").value.trim().toLowerCase(), prog = $("f-programa").value, prop = document.querySelector("#f-propension [aria-pressed='true']")?.dataset.valor || "";
  const est = $("f-estado").value, zon = $("f-zona").value, orden = $("f-orden").value, ase = esJefe() ? $("f-asesor").value : "";
  const ori = esJefe() ? $("f-origen").value : "";
  const L = estado.aspirantes.filter((a) => (!prog || a.programa === prog) && (!est || a.estado === est) && (!ori || a.origen === ori)
    && (!ase || (ase === "SIN" ? !a.asesor_id : a.asesor_id === ase))
    && (!zon || (zona(a.distancia_vial_km) || "SIN") === zon)
    && (!prop || (prop === "SIN" ? !a.propension : a.propension === prop))
    && (!q || [a.nombre, a.correo, a.telefono, a.colegio, a.ubicacion].some((v) => v && v.toLowerCase().includes(q))));
  const prob = (a) => a.probabilidad_matricula ?? -1;
  const comparar = { reciente: (x, y) => y.creado_en.localeCompare(x.creado_en), "prob-desc": (x, y) => prob(y) - prob(x),
    "prob-asc": (x, y) => (x.probabilidad_matricula ?? 2) - (y.probabilidad_matricula ?? 2), nombre: (x, y) => x.nombre.localeCompare(y.nombre, "es"),
    "dist-asc": (x, y) => (x.distancia_vial_km ?? 1e9) - (y.distancia_vial_km ?? 1e9) }[orden];
  return L.sort(comparar);
}
function pintarConteosPropension() {
  const c = { "": estado.aspirantes.length, ALTA: 0, MEDIA: 0, BAJA: 0, SIN: 0 };
  estado.aspirantes.forEach((a) => { c[a.propension || "SIN"] += 1; });
  document.querySelectorAll("#f-propension button").forEach((b) => { b.querySelector("small").textContent = c[b.dataset.valor]; });
}
function pintarLista() {
  pintarConteosPropension();
  const tb = $("filas"), total = estado.aspirantes.length;
  $("vista-aspirantes").querySelector("h1").firstChild.textContent = esJefe() ? "Aspirantes " : "Mis aspirantes ";
  if (!estado.cargados) { $("tabla-contenedor").hidden = false; $("lista-vacia").hidden = true; tb.replaceChildren(...esqueletoFilas(6, esJefe() ? 11 : 10)); return; }
  const L = filtrados();
  $("lista-conteo").textContent = total ? (L.length === total ? `${total}` : `${L.length} de ${total}`) : "";
  $("lista-vacia").hidden = L.length > 0; $("tabla-contenedor").hidden = L.length === 0;
  $("lista-vacia").replaceChildren(icono(total ? "buscar" : "usuario-mas", "ic vacio-icono"),
    el("p", { text: total ? "Ningún aspirante coincide con la búsqueda o los filtros." : "Todavía no hay aspirantes registrados." }),
    total ? el("button", { type: "button", class: "secundario", onclick: limpiarFiltros, text: "Quitar filtros" }) : el("a", { class: "boton primario", href: "#/registrar", text: "Registrar el primero" }));
  const celda = (etiqueta, ...c) => el("td", { dataset: { etiqueta } }, ...c);
  tb.replaceChildren(...L.slice(0, limite).map((a) => {
    const tr = el("tr", { dataset: { nuevo: estado.nuevos.has(a.id) ? "si" : "no" }, onclick: (ev) => { if (!ev.target.closest("a, button")) location.hash = `#/aspirante/${a.id}`; } },
      celda("Aspirante", el("div", { class: "persona" }, avatar(a.nombre), el("span", { class: "persona-texto" },
        el("a", { class: "nombre", href: `#/aspirante/${a.id}`, text: a.nombre }),
        el("small", {}, a.ubicacion || "—", esSimulado(a) && el("span", { class: "chip chico", dataset: { tono: "SIMULADO" }, text: "Base simulada" }),
          a.fuente === "ENCUESTA" && el("span", { class: "chip chico", dataset: { tono: "ENCUESTA" }, text: "Encuesta" }),
          traspasadoPorMi(a) && el("span", { class: "chip chico", dataset: { tono: "TRASPASADO" }, text: `Traspasado a ${nombreAsesor(a.asesor_id)}` }))))),
      celda("Contacto", a.telefono || a.correo ? [a.telefono && el("span", { text: a.telefono }), a.correo && el("small", { text: a.correo })] : el("small", { text: "Sin contacto" })),
      celda("Programa", el("span", { title: PROGRAMAS[a.programa], text: a.programa }), el("small", { text: a.periodo })),
      celda("ICFES", String(a.icfes), el("small", { text: banda(a.icfes) || "" })),
      celda("Beca", NOMBRE_BECA[a.beca] || "—"),
      celda("Distancia", a.distancia_vial_km === null || a.distancia_vial_km === undefined ? "—" : [el("span", { text: `${km(a.distancia_vial_km)} vía` }), el("small", { text: `${km(a.distancia_campus_km)} recta` })]),
      celda("Prob. matrícula", a.propension ? el("div", { class: "mini-prob" }, el("b", { text: pct(a.probabilidad_matricula) }),
        el("span", { class: "mini-barra" }, el("i", { estilo: { width: `${a.probabilidad_matricula * 100}%`, background: ESTADO_COLOR[a.propension] } }))) : el("small", { text: "Sin predecir" })),
      celda("¿Se matricularía?", a.propension ? chip(a.se_matricularia ? "Sí" : "No", a.se_matricularia ? "si" : "no") : "—"),
      celda("Seguimiento", chip(ETIQUETA_ESTADO[a.estado] || a.estado, a.estado)),
      esJefe() && el("td", { class: "solo-jefe", dataset: { etiqueta: "Asesor" } }, esSimulado(a)
        ? el("span", { class: "texto-suave", text: `${a.asesor_simulado || "—"} (simulado)` })
        : el("span", { class: a.asesor_id ? "" : "texto-suave", text: nombreAsesor(a.asesor_id) })),
      celda("Registrado", el("small", { title: fecha(a.creado_en), text: hace(a.creado_en) })));
    return tr;
  }));
  $("mas-filas").hidden = L.length <= limite;
  $("mas-filas").textContent = `Mostrar más (${L.length - limite} restantes)`;
  setTimeout(() => estado.nuevos.clear(), 1500);
}
function limpiarFiltros() {
  $("f-buscar").value = ""; ["f-programa", "f-estado", "f-zona", "f-asesor", "f-origen"].forEach((id) => { $(id).value = ""; });
  document.querySelectorAll("#f-propension button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.valor === "")));
  pintarLista();
}
function exportarCsv() {
  const cols = [["origen"], ["inscripcion_id", "inscripcion_simulada"], ["creado_en", "registrado"], ["nombre"], ["telefono"], ["correo"], ["medio_contacto"], ["genero"], ["edad"], ["programa"], ["periodo"],
    ["canal", "como_conocio"], ["canal_detalle"], ["icfes"], ["anios_desde_saber11"], ["estrato"], ["direccion"], ["direccion_complemento"],
    ["ubicacion"], ["distancia_campus_km", "km_linea_recta"], ["distancia_vial_km", "km_por_via"], ["ubicada_con"], ["colegio"], ["tipo_colegio"], ["beca"],
    ["precio_neto_primer_semestre"], ["probabilidad_matricula"], ["se_matricularia"], ["propension"], ["estado_entrevista"], ["puntaje_vocacional"], ["puntaje_vocacional_nlp"],
    ["estado", "seguimiento"], ["matriculado_real", "se_matriculo_real"], ["asesor_id", "asesor"], ["notas"]];
  const esc = (v) => { const s = v === null || v === undefined ? "" : String(v); return /[",;\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
  const valorCsv = (a, c) => (c === "estado_entrevista" ? (ESTADO_ENTREVISTA[a[c]] || "") : c === "asesor_id" ? (esSimulado(a) ? `${a.asesor_simulado || ""} (simulado)` : nombreAsesor(a.asesor_id))
    : c === "matriculado_real" ? (a[c] === null || a[c] === undefined ? "" : a[c] ? "Sí" : "No") : c === "canal" ? (a.canal ? CANALES[a.canal] : "") : c === "se_matricularia" ? (a[c] === null || a[c] === undefined ? "" : a[c] ? "Sí" : "No") : a[c]);
  const filas = filtrados().map((a) => cols.map(([c]) => esc(valorCsv(a, c))).join(","));
  const url = URL.createObjectURL(new Blob(["﻿" + [cols.map(([c, n]) => n || c).join(","), ...filas].join("\n")], { type: "text/csv;charset=utf-8" }));
  const enlace = el("a", { href: url, download: `aspirantes_${new Date().toISOString().slice(0, 10)}.csv` });
  document.body.append(enlace); enlace.click(); enlace.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  avisar(`Se descargaron ${filas.length} aspirantes en CSV.`, "exito", { duracion: 2500 });
}

// ---------------------------------------------------------------------------- vista: ficha del aspirante
let activo = null, notasSucias = false;
const filasDl = (dl, filas) => dl.replaceChildren(...filas.filter(Boolean).flatMap(([k, v]) => [el("dt", { text: k }), el("dd", {}, v ?? "—")]));
function pintarDetalle(id) {
  if (!estado.cargados) {                                          // primera carga: esqueleto
    $("d-nombre").textContent = "Cargando…"; $("d-avatar").textContent = ""; return true;
  }
  const a = estado.aspirantes.find((x) => x.id === id);
  if (!a) { mostrarErrorEnApp("aspirante", { acciones: [{ texto: "Ver la lista", clase: "primario", fn: () => { location.hash = "#/aspirantes"; } }] }); return false; }
  if (activo !== a.id) notasSucias = false;
  activo = a.id;
  $("d-error").hidden = true; $("d-guardado").textContent = "";
  $("d-avatar").textContent = iniciales(a.nombre);
  $("d-nombre").textContent = a.nombre;
  const sim = esSimulado(a);
  $("d-chips").replaceChildren(...[chip(a.programa, ""), chip(a.periodo, ""), chip(ETIQUETA_ESTADO[a.estado] || a.estado, a.estado), chipPropension(a),
    sim && chip("Base simulada", "SIMULADO"), a.fuente === "ENCUESTA" && chip("Llenó la encuesta", "ENCUESTA", "enlace")].filter(Boolean));
  $("d-registro").textContent = sim ? `Inscrito el ${fecha(a.creado_en)}`
    : `Registrado ${hace(a.creado_en)}${a.actualizado_en && a.actualizado_en !== a.creado_en ? ` · actualizado ${hace(a.actualizado_en)}` : ""}`;
  const entregado = traspasadoPorMi(a), lectura = sim || entregado;
  $("d-solo-lectura").hidden = !lectura;
  if (sim) $("d-solo-lectura-texto").textContent = `Base simulada de Supabase · inscripción N.º ${a.inscripcion_id} (${a.periodo}). Solo lectura: `
    + (a.matriculado_real === null || a.matriculado_real === undefined ? "su campaña sigue en curso, sin resultado todavía." : `resultado real: ${a.matriculado_real ? "se matriculó" : "no se matriculó"}.`);
  if (entregado) $("d-solo-lectura-texto").textContent = `Usted lo traspasó a ${nombreAsesor(a.asesor_id)} ${hace(a.traspasado_en)}`
    + `${a.motivo_traspaso ? ` («${a.motivo_traspaso}»)` : ""}. Ahora lo atiende esa persona; aquí queda en solo lectura.`;
  $("d-predecir").hidden = lectura;
  $("d-guardar").closest(".tarjeta").hidden = lectura;
  $("d-traspaso").hidden = sim;
  document.querySelector("#vista-detalle .zona-peligro").hidden = lectura;
  pintarTraspaso(a, entregado);
  pintarEntrevista(a, lectura);
  filasDl($("d-contacto"), [["Celular o teléfono", a.telefono], ["Correo", a.correo], ["Prefiere", MEDIOS[a.medio_contacto] || "Sin preferencia"],
    ["Autorizó el tratamiento de datos", sim ? "Dato simulado" : a.autoriza_datos ? "Sí (Ley 1581 de 2012)" : "No"]]);
  const tel = a.telefono ? a.telefono.replace(/[^0-9+]/g, "") : "";
  const wa = tel ? (tel.startsWith("+") ? tel.slice(1) : tel.length === 10 ? "57" + tel : tel) : "";
  $("d-enlaces").replaceChildren(...[tel && el("a", { class: "boton discreto", href: `tel:${tel}` }, icono("telefono"), "Llamar"),
    wa && el("a", { class: "boton discreto", href: `https://wa.me/${wa}`, target: "_blank", rel: "noopener noreferrer" }, icono("mensaje"), "WhatsApp"),
    a.correo && el("a", { class: "boton discreto", href: `mailto:${a.correo}` }, icono("correo"), "Correo")].filter(Boolean));
  if (!tel && !a.correo) $("d-enlaces").replaceChildren(el("p", { class: "nota", text: "Sin teléfono ni correo: no se le puede hacer seguimiento." }));
  const z = zona(a.distancia_vial_km), u = ubicacionDe(a.ubicacion);
  $("d-dist-via").textContent = km(a.distancia_vial_km); $("d-dist-recta").textContent = km(a.distancia_campus_km);
  $("d-dist-zona").replaceChildren(z ? chip(`Zona ${ZONAS[z].toLowerCase()}`, z) : chip("Sin ubicación", ""));
  $("d-dist-origen").textContent = a.ubicada_con === "CATASTRO" ? `Desde la placa ubicada en Catastro (${a.ubicacion}).`
    : a.distancia_vial_km !== null && a.distancia_vial_km !== undefined ? `Aproximada, desde el centro de ${a.ubicacion}.` : "Sin ubicación calculada.";
  $("d-dist-extrapola").hidden = !(u && u.fuera_de_entrenamiento);
  if (a.id !== $("d-ruta").dataset.de) {                           // la ruta se pinta al abrir la ficha, no en cada cambio en vivo
    $("d-ruta").dataset.de = a.id;
    const editable = !lectura && (esJefe() || a.asesor_id === estado.perfil?.user_id);
    pintarRuta(a, { guardar: editable ? async (c) => { if (activo === a.id) reemplazar(await estado.almacen.actualizar(a.id, c)); } : null });
  }
  const beca = a.beca || "NINGUNA", desc = Number(a.pct_descuento_adicional || 0);
  const p = estado.modelo.precios(a.programa, a.periodo, beca, desc);
  filasDl($("d-precio"), [["Beca que se aplica", NOMBRE_BECA[beca]],
    desc > 0 && ["Descuento institucional", `${(estado.modelo.reglas.descuentos.tipos[a.tipo_descuento] || {}).nombre || a.tipo_descuento} · ${pct(desc)}`],
    ["Tarifa del semestre", cop(p.bruto)],
    ["1er semestre", `${pct(p.pct_total)} · ${cop(p.neto)}`],
    ["Desde el 2º semestre", `${pct(p.pct_siguientes)} · ${cop(p.neto_siguientes)}`]]);
  filasDl($("d-datos"), [["Programa", PROGRAMAS[a.programa]], ["ICFES", `${a.icfes}${banda(a.icfes) ? ` (nivel ${banda(a.icfes).toLowerCase()})` : ""}`],
    ["Años desde el Saber 11", a.anios_desde_saber11 ?? "Sin dato (el modelo usa 0)"], ["Estrato", a.estrato],
    ["Becas solicitadas", [a.solicita_mi_vocacion && "Mi Vocación", a.solicita_saber11 && "Saber 11"].filter(Boolean).join(" · ") || "Ninguna"],
    ["Entrevista vocacional", textoEntrevista(a)],
    ["Dirección", [a.direccion, a.direccion_complemento].filter(Boolean).join(", ")], ["Localidad o municipio", a.ubicacion],
    a.apoyo_foes && ["Fondo municipal", "Solicitará FOES/FOEST"], ["Régimen de salud", REGIMEN[a.regimen_salud] || "Sin dato"],
    ["Crédito ICETEX", a.solicita_icetex ? (a.prediccion?.elegible_icetex === false ? "Lo solicitará, pero no cumple el mérito mínimo"
      : "Lo solicitará (Plan Talento STEM)") : "No lo solicitará"],
    ["Colegio", [a.colegio, TIPO[a.tipo_colegio]].filter(Boolean).join(" · ") || "Sin dato"],
    ["Género", GENERO[a.genero] || "Sin dato"], ["Edad", a.edad ? (a.edad > 40 ? "Más de 40 años" : `${a.edad} años`) : "Sin dato (el modelo usa 17)"],
    ["¿Cómo conoció la Universidad?", [a.canal ? CANALES[a.canal] : "Sin dato", a.canal_detalle].filter(Boolean).join(" · ")],
    ["Asesor asignado", sim ? `${a.asesor_simulado || "—"} (asesor simulado)` : nombreAsesor(a.asesor_id)],
    !sim && ["Cómo se registró", a.fuente === "ENCUESTA" ? `Llenó la encuesta en línea${nombreEnlace(a.enlace_id)}` : "Lo registró el personal en la app"]]);
  if (!notasSucias) { $("d-estado").value = a.estado; $("d-notas").value = a.notas || ""; }
  pintarPasosSeguimiento(a.estado);
  mostrarResultado(a);
  restaurarEliminar();
  return true;
}
function pintarPasosSeguimiento(actual) {
  const orden = ["NUEVO", "CONTACTADO", "INTERESADO", "INSCRITO", "MATRICULADO"], i = orden.indexOf(actual);
  $("d-camino").replaceChildren(...orden.map((k, j) => el("li", { dataset: { estado: actual === "DESCARTADO" ? "descartado" : j < i ? "hecho" : j === i ? "actual" : "pendiente" } },
    el("button", { type: "button", onclick: () => { $("d-estado").value = k; notasSucias = true; pintarPasosSeguimiento(k); } }, ESTADOS[k]))));
}

// La entrevista en una línea: el puntaje de la psicóloga (1 a 5) y el que lee el modelo NLP en sus palabras
const coma1 = (v) => Number(v).toFixed(1).replace(".", ",");
function textoEntrevista(a) {
  if (conEntrevista(a)) return `Puntaje vocacional ${a.puntaje_vocacional} de 5`
    + (a.puntaje_vocacional_nlp !== null && a.puntaje_vocacional_nlp !== undefined ? ` · según sus palabras ${coma1(a.puntaje_vocacional_nlp)}` : "");
  return a.estado_entrevista ? ESTADO_ENTREVISTA[a.estado_entrevista] : "No la ha presentado";
}
// Tarjeta "Entrevista vocacional" de la ficha: estado y botón para enviar el enlace personal al aspirante. Lo que
// responde (y la salud mental) solo lo ve la psicóloga; aquí llegan el estado y los puntajes.
function pintarEntrevista(a, lectura) {
  const sim = esSimulado(a);
  $("d-entrevista").hidden = sim;
  if (sim) return;
  $("d-entrevista-estado").textContent = a.estado_entrevista ? ESTADO_ENTREVISTA[a.estado_entrevista] : "Sin enviar";
  $("d-entrevista-estado").dataset.tono = a.estado_entrevista ? `ENT-${a.estado_entrevista}` : "";
  $("d-entrevista-texto").textContent = conEntrevista(a) ? `${textoEntrevista(a)}. La psicóloga vocacional la cerró${a.entrevistada_en ? ` ${hace(a.entrevistada_en)}` : ""}.`
    : a.estado_entrevista === "ENVIADA" ? "Se envió el enlace. Cuando el aspirante responda, le llega a la psicóloga para agendar la cita."
      : a.estado_entrevista ? "La psicóloga ya tiene sus respuestas y agenda la entrevista. El puntaje llega aquí cuando la cierre."
        : "Envíele el enlace de la entrevista vocacional: la responde en línea y le llega a la psicóloga (requisito de Mi Vocación).";
  $("d-entrevista-acciones").hidden = lectura || conEntrevista(a);
  $("d-entrevista-enviar").replaceChildren(icono("enlace"), a.estado_entrevista ? "Enviar un enlace nuevo" : "Enviar entrevista vocacional");
  if ($("d-entrevista-enlace").dataset.de !== a.id) { $("d-entrevista-enlace").hidden = true; $("d-entrevista-enlace").dataset.de = a.id; }
}
async function enviarEntrevista() {
  const a = estado.aspirantes.find((x) => x.id === activo); if (!a) return;
  try {
    const { enlace, aspirante } = await conEspera($("d-entrevista-enviar"), "Creando…", () => estado.almacen.crearEnlaceEntrevista(a.id));
    if (aspirante) reemplazar(aspirante);
    const url = urlEntrevista(enlace.token), { telefono } = a;
    const tel = telefono ? telefono.replace(/[^0-9]/g, "") : "";
    const texto = `Hola ${(a.nombre || "").split(/\s+/)[0]}, te comparto la entrevista vocacional de Unicervantes. Respóndela aquí: ${url}`;
    $("d-entrevista-enlace").replaceChildren(
      el("p", { class: "etiqueta", text: "Enlace personal (un solo uso, vence en 30 días)" }),
      el("input", { type: "text", readonly: true, value: url, "aria-label": "Enlace de la entrevista", class: "enlace-copiable" }),
      el("div", { class: "acciones" },
        el("button", { type: "button", class: "secundario", onclick: async () => { try { await navigator.clipboard.writeText(url); avisar("Enlace copiado.", "exito", { duracion: 1800 }); } catch { avisar("No se pudo copiar; selecciónelo y cópielo.", "info"); } } }, icono("copiar"), "Copiar"),
        tel && el("a", { class: "boton discreto", href: `https://wa.me/${tel.length === 10 ? "57" + tel : tel}?text=${encodeURIComponent(texto)}`, target: "_blank", rel: "noopener noreferrer" }, icono("mensaje"), "Enviar por WhatsApp")),
      bloqueQR(url, { titulo: `Entrevista vocacional · ${(a.nombre || "").split(/\s+/)[0] || "Unicervantes"}`, archivo: nombreArchivoQR("qr-entrevista", a.nombre) }));
    $("d-entrevista-enlace").hidden = false;
    pintarDetalle(a.id);
    avisar("Enlace de la entrevista listo para enviar.", "exito", { duracion: 2500 });
  } catch (e) { manejarError(e, $("d-error")); }
}

// Base simulada: la predicción del Sprint 6 guardada en Supabase (tabla prediccion) y sus razones (explicacion_prediccion)
const razonesSimuladas = new Map();
function prediccionDe(a) {
  if (!esSimulado(a)) return a.prediccion;
  return { simulado: true, probabilidad_matricula: a.probabilidad_matricula, umbral: estado.modelo.reglas.umbral_clasificacion,
    segmento_propension: a.propension, probabilidad_sin_beca: null, razones_matricula: razonesSimuladas.get(a.id) ?? null,
    puntaje_vocacional: a.puntaje_vocacional ?? null, puntaje_vocacional_nlp: null,
    distancia_vial_km: a.distancia_vial_km, distancia_campus_km: a.distancia_campus_km, recomendacion: null, avisos: [] };
}
async function cargarRazones(a) {
  try { razonesSimuladas.set(a.id, await estado.almacen.explicaciones(a.inscripcion_id)); }
  catch { razonesSimuladas.set(a.id, []); }
  if (activo === a.id) mostrarResultado(a);
}
function mostrarResultado(a) {
  const p = prediccionDe(a);
  $("d-resultado").hidden = !p; $("d-sin-prediccion").hidden = Boolean(p);
  $("d-predecir").replaceChildren(icono(p ? "recargar" : "chispa"), p ? "Volver a predecir" : "Predecir matrícula");
  if (!p) return;
  const s = estado.modelo.reglas.segmentos_propension;
  animarNumero($("p-prob"), p.probabilidad_matricula, (v) => pct(v));
  const si = p.probabilidad_matricula >= p.umbral;
  $("p-veredicto").replaceChildren(icono(si ? "check" : "x", "ic ic-chico"), si ? "Se matricularía" : "No se matricularía");
  $("p-veredicto").dataset.tono = si ? "si" : "no";
  $("p-propension").textContent = `Propensión ${PROPENSION[p.segmento_propension].toLowerCase()}`; $("p-propension").dataset.tono = p.segmento_propension;
  setTimeout(() => { $("p-marca").style.left = `${Math.min(100, Math.max(0, p.probabilidad_matricula * 100))}%`; }, 40);   // la transición CSS lo mueve
  const dif = p.probabilidad_sin_beca === null ? null : (p.probabilidad_matricula - p.probabilidad_sin_beca) * 100;
  const real = a.matriculado_real;
  $("p-beca").textContent = p.simulado
    ? (real === null || real === undefined ? "Campaña en curso: todavía no hay resultado real para comparar."
      : `Resultado real: ${real ? "se matriculó" : "no se matriculó"} · la predicción ${(p.probabilidad_matricula >= p.umbral) === real ? "acertó" : "no acertó"}.`)
    : dif === null ? (p.pct_descuento_inicial > 0
        ? `Sin beca: la probabilidad incluye solo el descuento institucional (${pct(p.pct_descuento_inicial)}).`
        : "Sin beca ni descuento: la probabilidad es con la tarifa plena.")
      : `Sin la beca sería ${pct(p.probabilidad_sin_beca)} (${dif >= 0 ? "+" : ""}${dif.toFixed(0)} puntos con la beca).`;
  if (p.razones_matricula === null) { $("p-razones").replaceChildren(el("li", { class: "cargando-razones" }, el("span", { class: "giro" }), "Cargando las razones…")); cargarRazones(a); }
  else $("p-razones").replaceChildren(...(p.razones_matricula.length ? p.razones_matricula : ["Sin razones guardadas para este aspirante."]).map((t) =>
    el("li", { dataset: { sentido: /aumenta/.test(t) ? "sube" : /reduce/.test(t) ? "baja" : "" } },
      icono(/aumenta/.test(t) ? "sube" : "baja", "ic ic-chico"), el("span", { text: t }))));
  const voc = p.puntaje_vocacional === undefined ? a.puntaje_vocacional ?? null : p.puntaje_vocacional;   // predicciones anteriores: de la ficha
  const nlp = p.puntaje_vocacional_nlp ?? null;
  filasDl($("p-detalle"), [p.segmento_mercado && ["Segmento de mercado", p.segmento_mercado],
    ["Entrevista que usó el modelo", voc === null ? "Sin entrevista" : `puntaje ${voc} de 5${nlp !== null ? ` · según sus palabras ${coma1(nlp)}` : ""}`],
    ["Distancia que usó el modelo", `${km(p.distancia_vial_km)} por vía (${km(p.distancia_campus_km)} en línea recta)`]]);
  $("p-recomendacion").closest(".recomendacion").hidden = !p.recomendacion;
  $("p-recomendacion").textContent = p.recomendacion || "";
  $("p-avisos").replaceChildren(...(p.avisos || []).map((t) => el("p", {}, icono("alerta", "ic ic-chico"), el("span", { text: t }))));
  $("p-fecha").textContent = p.simulado
    ? `Predicción del Sprint 6 guardada en Supabase (tabla prediccion) · umbral ${pct(p.umbral)} · bandas: baja < ${pct(s.BAJA)}, alta ≥ ${pct(s.ALTA)}`
    : `Predicho ${hace(a.predicho_en)} · umbral para «se matricularía»: ${pct(p.umbral)} · bandas: baja < ${pct(s.BAJA)}, alta ≥ ${pct(s.ALTA)}`;
}

async function predecirActivo() {
  const a = estado.aspirantes.find((x) => x.id === activo); if (!a) return;
  $("d-error").hidden = true;
  try {
    const n = await conEspera($("d-predecir"), "Calculando…", () => predecirYGuardar(a));
    pintarDetalle(n.id);
    avisar(`Predicción: ${pct(n.probabilidad_matricula)} · propensión ${PROPENSION[n.propension].toLowerCase()}.`, "exito", { duracion: 3000 });
  } catch (e) { manejarError(e, $("d-error")); }
}
async function guardarSeguimiento() {
  const a = estado.aspirantes.find((x) => x.id === activo); if (!a) return;
  try {
    await conEspera($("d-guardar"), "Guardando…", async () => {
      reemplazar(await estado.almacen.actualizar(a.id, { estado: $("d-estado").value, notas: $("d-notas").value.trim() || null }));
    });
    notasSucias = false; $("d-error").hidden = true;
    pintarDetalle(a.id);
    $("d-guardado").textContent = "Guardado.";
    avisar("Seguimiento guardado.", "exito", { duracion: 2000 });
  } catch (e) { manejarError(e, $("d-error")); }
}
// ---------------------------------------------------------------------------- traspaso entre asesores
// El asesor pasa el aspirante a otro asesor activo (motivo obligatorio); el jefe y el administrador, a cualquiera del
// equipo. Cada cambio queda en traspaso_aspirante (lo escribe un disparador en Supabase).
function pintarTraspaso(a, entregado) {
  const yo = estado.perfil.user_id;
  $("d-asesor-actual").textContent = `Lo atiende: ${nombreAsesor(a.asesor_id)}`;
  const destinos = estado.equipo.filter((p) => p.activo && p.rol !== "PSICOLOGA" && p.user_id !== a.asesor_id && (esJefe() || (p.rol === "ASESOR" && p.user_id !== yo)))
    .sort((x, y) => (x.rol === "ASESOR" ? 0 : 1) - (y.rol === "ASESOR" ? 0 : 1) || (x.nombre || "").localeCompare(y.nombre || "", "es"));
  const puede = !entregado && (esJefe() || a.asesor_id === yo);
  ["c-t-destino", "c-t-motivo", "t-acciones", "t-ayuda"].forEach((id) => { $(id).hidden = !puede; });
  $("t-obligatorio").hidden = esJefe();
  $("t-ayuda").textContent = esJefe() ? "Asigne el aspirante a otra persona del equipo. Quedará el registro del cambio."
    : "Si no puede continuar con este aspirante, páselo a otro asesor: lo verá en su lista y quedará el registro del traspaso.";
  if (puede) {
    const actual = $("t-destino").value;
    $("t-destino").replaceChildren(el("option", { value: "", text: destinos.length ? "Elija a quién" : "No hay otros asesores activos" }),
      ...destinos.map((p) => el("option", { value: p.user_id, text: `${p.nombre || p.correo}${p.rol !== "ASESOR" ? ` · ${ROLES[p.rol].toLowerCase()}` : ""}` })));
    $("t-destino").value = destinos.some((p) => p.user_id === actual) ? actual : "";
    restaurarTraspaso();
    $("t-traspasar").disabled = !destinos.length;
  }
  cargarHistorial(a.id);
}
async function cargarHistorial(id) {
  let h = [];
  try { h = await estado.almacen.historialTraspasos(id); } catch { /* sin historial */ }
  if (activo !== id) return;
  $("t-historial-caja").hidden = !h.length;
  $("t-historial").replaceChildren(...h.map((t) => el("li", {},
    el("span", {}, el("b", { text: nombreAsesor(t.de_asesor) }), " → ", el("b", { text: nombreAsesor(t.a_asesor) })),
    t.motivo && el("q", { text: t.motivo }),
    el("small", { text: `${fecha(t.creado_en)}${t.hecho_por && t.hecho_por !== t.de_asesor ? ` · lo hizo ${nombreAsesor(t.hecho_por)}` : ""}` }))));
}
function pedirTraspaso() {
  const destino = $("t-destino").value, motivo = $("t-motivo").value.trim();
  const malos = [destino === "", !esJefe() && motivo.length < 5];
  if (malos[0]) $("c-t-destino").dataset.error = ""; else delete $("c-t-destino").dataset.error;
  if (malos[1]) $("c-t-motivo").dataset.error = ""; else delete $("c-t-motivo").dataset.error;
  if (malos.some(Boolean)) return;
  $("t-acciones").replaceChildren(el("span", { class: "confirmar" }, `¿Traspasarlo a ${nombreAsesor(destino)}?`,
    el("button", { type: "button", class: "primario", onclick: () => traspasar(destino, motivo) }, "Sí, traspasar"),
    el("button", { type: "button", class: "discreto", text: "Cancelar", onclick: restaurarTraspaso })));
  $("t-acciones").querySelector("button").focus();
}
function restaurarTraspaso() {
  $("t-acciones").replaceChildren(el("button", { type: "button", class: "secundario", id: "t-traspasar", onclick: pedirTraspaso }, icono("flecha-der"), "Traspasar"));
}
async function traspasar(destino, motivo) {
  const a = estado.aspirantes.find((x) => x.id === activo); if (!a) return;
  const boton = $("t-acciones").querySelector(".primario");
  try {
    const nuevo = await conEspera(boton, "Traspasando…", () => estado.almacen.traspasar(a.id, destino, motivo));
    $("t-motivo").value = ""; $("t-destino").value = "";
    if (nuevo) { reemplazar(nuevo); pintarDetalle(a.id); }
    else {                                                         // el asesor ya no es el dueño: lo ve en solo lectura
      reemplazar({ ...a, asesor_id: destino, motivo_traspaso: motivo, traspasado_por: estado.perfil.user_id, traspasado_en: new Date().toISOString() });
      location.hash = "#/aspirantes";
    }
    avisar(`${a.nombre} ahora lo atiende ${nombreAsesor(destino)}.`, "exito", { duracion: 3500 });
  } catch (e) { manejarError(e, $("d-error")); restaurarTraspaso(); }
}

function pedirEliminar() {
  $("d-zona-eliminar").replaceChildren(el("span", { class: "confirmar" }, "¿Eliminar definitivamente?",
    el("button", { type: "button", class: "discreto peligro", onclick: eliminarActivo }, icono("basura"), "Sí, eliminar"),
    el("button", { type: "button", class: "discreto", text: "Cancelar", onclick: restaurarEliminar })));
  $("d-zona-eliminar").querySelector("button").focus();
}
function restaurarEliminar() {
  $("d-zona-eliminar").replaceChildren(el("button", { type: "button", id: "d-eliminar", class: "discreto peligro", onclick: pedirEliminar }, icono("basura"), "Eliminar aspirante"));
}
async function eliminarActivo() {
  const id = activo, a = estado.aspirantes.find((x) => x.id === id); if (!id) return;
  try {
    await estado.almacen.eliminar(id);
    quitar(id); activo = null;
    avisar(`Se eliminó a ${a ? a.nombre : "el aspirante"}.`, "info");
    location.hash = "#/aspirantes";
  } catch (e) { manejarError(e, $("d-error")); restaurarEliminar(); }
}

// ---------------------------------------------------------------------------- errores y conexión
function manejarError(e, caja = null) {
  const err = traducirError(e);
  if (err.tipo === "sesion") { avisar(err.message, "error"); cerrarSesion({ silencioso: true }); return; }
  if (caja) { caja.textContent = err.message; caja.hidden = false; }
  avisar(err.message, "error");
}
window.addEventListener("unhandledrejection", (ev) => { console.error(ev.reason); avisar("Ocurrió un error inesperado. Intente de nuevo.", "error"); });
window.addEventListener("error", (ev) => { if (ev.error) { console.error(ev.error); avisar("Ocurrió un error inesperado en la página.", "error"); } });
window.addEventListener("offline", () => { $("franja-red").hidden = false; avisar("Se perdió la conexión a internet.", "error", { duracion: 0 }); });
window.addEventListener("online", async () => {
  $("franja-red").hidden = true; avisar("Conexión restablecida.", "exito", { duracion: 2500 });
  if (estado.almacen && !$("app").hidden) { await cargarAspirantes(); navegar({ animar: false }); }
});

// Le traspasaron un aspirante (tiempo real de traspaso_aspirante)
document.addEventListener("traspaso", (ev) => {
  const t = ev.detail || {};
  if (!estado.perfil || t.a_asesor !== estado.perfil.user_id || t.hecho_por === estado.perfil.user_id) return;
  setTimeout(() => {                                               // la fila del aspirante llega por su propio canal
    const a = estado.aspirantes.find((x) => x.id === t.aspirante_id);
    avisar(`${nombreAsesor(t.hecho_por)} le traspasó a ${a ? a.nombre : "un aspirante"}${t.motivo ? `: «${t.motivo}»` : "."}`, "vivo",
      { duracion: 10000, accion: a ? { texto: "Ver", fn: () => { location.hash = `#/aspirante/${a.id}`; } } : null });
  }, 900);
});

// Encuestas que llegan sin predicción: la app del asesor dueño las predice sola (el aspirante nunca ve la predicción)
const prediciendo = new Set();
async function predecirEncuestas() {
  const pendientes = estado.aspirantes.filter((a) => a.fuente === "ENCUESTA" && !a.prediccion && a.asesor_id === estado.perfil?.user_id && !prediciendo.has(a.id));
  for (const a of pendientes.slice(0, 10)) {
    prediciendo.add(a.id);
    try { await predecirYGuardar(a); } catch (e) { console.error(e); }
  }
}
const nombreEnlace = (id) => { const e = estado.enlaces.find((x) => x.id === id); return e?.nombre ? ` («${e.nombre}»)` : ""; };

// Cambios en los datos (propios o de otra sesión, por tiempo real)
document.addEventListener("aspirantes", (ev) => {
  const d = ev.detail || {};
  $("nav-contador").textContent = $("barra-contador").textContent = estado.aspirantes.length ? estado.aspirantes.length.toLocaleString("es-CO") : "";
  if ($("app").hidden) return;
  if (d.tipo === "carga") { navegar({ animar: !$("vista-error").hidden }); actualizarAnalitica(); predecirEncuestas(); return; }
  if (d.remoto && d.tipo === "nuevo" && !estado.aspirantes.find((x) => x.id === d.id)?.traspasado_en) {
    const a = estado.aspirantes.find((x) => x.id === d.id);
    if (a) avisar(a.fuente === "ENCUESTA" ? `${a.nombre} llenó su encuesta` : `Nuevo aspirante: ${a.nombre}`, "vivo",
      { duracion: a.fuente === "ENCUESTA" ? 9000 : 4200, accion: { texto: "Ver", fn: () => { location.hash = `#/aspirante/${a.id}`; } } });
    if (a && a.fuente === "ENCUESTA") { predecirEncuestas(); document.dispatchEvent(new CustomEvent("enlaces")); }
  }
  const r = ruta();
  if (r.vista === "resumen") pintarResumen();
  if (r.vista === "aspirantes") pintarLista();
  if (r.vista === "analitica" || d.tipo === "vivo") actualizarAnalitica();
  if (r.vista === "detalle" && d.id === r.id) {
    if (d.remoto && d.tipo === "eliminado") { avisar("Este aspirante fue eliminado en otra sesión.", "info"); location.hash = "#/aspirantes"; }
    else navegar({ animar: false });
  }
});

// La psicóloga: cuando cambian sus citas o entrevistas se repinta la vista abierta
document.addEventListener("psicologia", () => {
  if ($("app").hidden || !esPsicologa()) return;
  const r = ruta();
  // La ficha abierta no se repinta (no borra lo que la psicóloga esté escribiendo), salvo si se pintó sin sus citas
  if (["agenda", "vocacionales"].includes(r.vista) || (r.vista === "vocacional" && $("vista-vocacional").dataset.sinAgenda)) navegar({ animar: false });
});
document.addEventListener("recargar-aspirantes", async () => { await cargarAspirantes(); const r = ruta(); if (r.vista === "vocacional") navegar({ animar: false }); });

document.addEventListener("equipo", () => {
  llenarSelectoresAsesor();
  pintarUsuarioMenu();
  if ($("app").hidden) return;
  const r = ruta();
  if (["equipo", "usuarios", "aspirantes", "detalle", "resumen", "perfil"].includes(r.vista)) navegar({ animar: false });
});

// ---------------------------------------------------------------------------- sesión e inicio
function mostrarAcceso({ noAutorizado = false, desactivado = false, mensaje = "" } = {}) {
  $("cargando").hidden = true; $("app").hidden = true; $("pantalla-error").hidden = true; $("vista-acceso").hidden = false;
  $("acceso-no-autorizado-texto").replaceChildren(el("strong", { text: desactivado ? "Su cuenta está desactivada." : "Su cuenta no está autorizada." }),
    desactivado ? " El administrador le quitó el acceso. Si es un error, pídale que la reactive." : " Inició sesión, pero no está en la lista del personal. Pida al administrador que le dé acceso.");
  $("form-acceso").hidden = noAutorizado; $("acceso-no-autorizado").hidden = !noAutorizado;
  $("acceso-error").hidden = !mensaje; $("acceso-error").textContent = mensaje;
  animarEntrada($("vista-acceso").firstElementChild);
  if (!noAutorizado) setTimeout(() => $("acceso-correo").focus(), 50);
}
async function entrarApp(perfil) {
  estado.perfil = perfil; estado.usuario = perfil.correo;
  document.body.dataset.rol = perfil.rol;
  $("cargando").hidden = true; $("vista-acceso").hidden = true; $("pantalla-error").hidden = true; $("app").hidden = false;
  pintarUsuarioMenu();
  if (!location.hash) history.replaceState(null, "", perfil.rol === "PSICOLOGA" ? "#/agenda" : "#/resumen");
  navegar();
  await cargarEquipo();
  if (perfil.rol === "PSICOLOGA") { await cargarAspirantes(); await cargarPsicologia(); escucharCambios(); escucharPsicologia(); pintarEstadoVivo(); return; }
  cargarEnlaces();                                                  // para decir en la ficha por qué enlace llegó cada encuesta
  await cargarAspirantes();
  if (estado.errorCarga) avisar(estado.errorCarga.message, "error");
  escucharCambios();
  pintarEstadoVivo();
}
async function revisarSesion(sesion) {
  if (!sesion) { mostrarAcceso(); return; }
  let perfil = null;
  try { perfil = await estado.almacen.perfil(sesion.user.id); }
  catch (e) { const err = traducirError(e); if (err.tipo === "conexion") { pantallaError("conexion", { detalle: err.message, acciones: [recargar] }); return; } }
  if (!perfil || !perfil.activo) { mostrarAcceso({ noAutorizado: true, desactivado: Boolean(perfil) }); return; }
  await entrarApp(perfil);
}
async function iniciarSesion(ev) {
  ev.preventDefault();
  const correo = $("acceso-correo").value.trim(), clave = $("acceso-clave").value;
  if (!correo || !clave) { $("acceso-error").textContent = "Escriba el correo y la contraseña."; $("acceso-error").hidden = false; return; }
  $("acceso-error").hidden = true;
  const r = await conEspera($("acceso-boton"), "Entrando…", () => estado.cliente.auth.signInWithPassword({ email: correo, password: clave }));
  $("acceso-clave").value = "";
  if (r.error) {
    const m = /invalid/i.test(r.error.message) ? "Correo o contraseña incorrectos." : traducirError(r.error).message;
    $("acceso-error").textContent = m; $("acceso-error").hidden = false;
    const t = $("form-acceso"); t.classList.remove("sacudir"); void t.offsetWidth; t.classList.add("sacudir");
    return;
  }
  await revisarSesion(r.data.session);
}
async function cerrarSesion({ silencioso = false } = {}) {
  if (estado.demo) return;
  await dejarDeEscuchar();
  await estado.cliente.auth.signOut().catch(() => {});
  estado.aspirantes = []; estado.cargados = false; estado.errorCarga = null; estado.perfil = null; estado.equipo = [];
  delete document.body.dataset.rol;
  history.replaceState(null, "", location.pathname + location.search);
  mostrarAcceso({ mensaje: silencioso ? "La sesión venció. Vuelva a iniciar sesión." : "" });
  if (!silencioso) avisar("Sesión cerrada.", "info", { duracion: 2000 });
}

function conectarEventos() {
  $("f-buscar").addEventListener("input", () => { limite = 100; pintarLista(); });
  // Celular: los filtros van plegados detrás de "Filtros y orden"; el botón dice cuántos están puestos
  const contarFiltros = () => {
    const n = ["f-programa", "f-estado", "f-zona", "f-asesor", "f-origen"].filter((id) => $(id).value).length + ($("f-orden").value !== "reciente" ? 1 : 0);
    $("f-activos").textContent = n || "";
  };
  ["f-programa", "f-estado", "f-zona", "f-orden", "f-asesor", "f-origen"].forEach((id) => $(id).addEventListener("change", () => { limite = 100; contarFiltros(); pintarLista(); }));
  $("f-mas").addEventListener("click", () => {
    const abiertos = $("f-mas").closest(".filtros").classList.toggle("abiertos");
    $("f-mas").setAttribute("aria-expanded", String(abiertos));
  });
  ["t-destino", "t-motivo"].forEach((id) => $(id).addEventListener("input", () => { delete $(`c-${id}`).dataset.error; }));
  $("f-propension").addEventListener("click", (ev) => {
    const b = ev.target.closest("button"); if (!b) return;
    document.querySelectorAll("#f-propension button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    limite = 100; pintarLista();
  });
  $("mas-filas").addEventListener("click", () => { limite += 100; pintarLista(); });
  $("recargar").addEventListener("click", () => conEspera($("recargar"), "Actualizando…", async () => {
    await cargarAspirantes(); if (!estado.errorCarga) avisar("Lista actualizada.", "exito", { duracion: 1800 });
  }));
  $("exportar").addEventListener("click", exportarCsv);
  $("d-predecir").addEventListener("click", predecirActivo);
  $("d-entrevista-enviar").addEventListener("click", enviarEntrevista);
  $("d-guardar").addEventListener("click", guardarSeguimiento);
  $("d-estado").addEventListener("change", () => { notasSucias = true; pintarPasosSeguimiento($("d-estado").value); });
  $("d-notas").addEventListener("input", () => { notasSucias = true; $("d-guardado").textContent = "Cambios sin guardar"; });
  const menuUsuario = (abrir) => {
    const abierto = abrir ?? $("usuario-opciones").hidden;
    $("usuario-opciones").hidden = !abierto; $("usuario-boton").setAttribute("aria-expanded", String(abierto));
    if (abierto) $("usuario-opciones").querySelector("a, button:not([hidden])")?.focus();
  };
  $("usuario-boton").addEventListener("click", (ev) => { ev.stopPropagation(); menuUsuario(); });
  document.addEventListener("click", (ev) => { if (!ev.target.closest(".usuario-menu")) menuUsuario(false); });
  document.addEventListener("keydown", (ev) => { if (ev.key === "Escape" && !$("usuario-opciones").hidden) { menuUsuario(false); $("usuario-boton").focus(); } });
  $("ir-perfil").addEventListener("click", () => menuUsuario(false));
  $("salir").addEventListener("click", () => { menuUsuario(false); cerrarSesion(); });
  const plegar = (si) => {
    document.body.classList.toggle("menu-plegado", si);
    $("plegar-menu").setAttribute("aria-expanded", String(!si));
    $("plegar-menu").setAttribute("aria-label", si ? "Desplegar el menú" : "Plegar el menú"); $("plegar-menu").title = si ? "Desplegar el menú" : "Plegar el menú";
    try { localStorage.setItem("unicervantes-menu-plegado", si ? "1" : "0"); } catch { /* sin almacenamiento */ }
  };
  $("plegar-menu").addEventListener("click", () => plegar(!document.body.classList.contains("menu-plegado")));
  try { plegar(localStorage.getItem("unicervantes-menu-plegado") === "1"); } catch { /* sin almacenamiento */ }
  $("acceso-salir").addEventListener("click", () => cerrarSesion());
  $("form-acceso").addEventListener("submit", iniciarSesion);
  const menuMovil = (abierto) => {
    document.body.classList.toggle("menu-abierto", abierto);
    ["menu-movil", "barra-mas"].forEach((id) => $(id).setAttribute("aria-expanded", String(abierto)));
    if (abierto) window.scrollTo({ top: 0, behavior: sinMovimiento() ? "auto" : "smooth" });   // el menú se abre en la barra superior
  };
  $("menu-movil").addEventListener("click", () => menuMovil(!document.body.classList.contains("menu-abierto")));
  $("barra-mas").addEventListener("click", () => menuMovil(!document.body.classList.contains("menu-abierto")));
  document.querySelectorAll("[data-nav], #ir-perfil").forEach((a) => a.addEventListener("click", () => menuMovil(false)));
  window.addEventListener("hashchange", () => { if (!$("app").hidden) navegar(); });
}

async function iniciar() {
  if (sinMovimiento()) document.documentElement.dataset.movimiento = "reducido";
  let M;
  try {
    const r = await fetch("modelo.json", { cache: "no-cache" });
    if (!r.ok) throw new Error(`modelo.json respondió ${r.status}`);
    M = await r.json();
  } catch (e) {
    pantallaError("general", { detalle: `No se pudo cargar el modelo (${e.message}).`, acciones: [recargar] }); return;
  }
  estado.modelo = crearModelo(M); estado.version = M.generado;
  $("estado-modelo").dataset.ok = "si"; $("estado-modelo").textContent = `Modelo ${M.generado}`;
  iniciarFormulario();
  iniciarEquipo();
  iniciarPerfil();
  iniciarEncuestas();
  iniciarPsicologia();
  conectarEventos();

  const local = ["localhost", "127.0.0.1", "[::1]"].includes(location.hostname);
  const demo = new URLSearchParams(location.search).get("demo");
  if (local && demo !== null) {
    estado.demo = true; estado.almacen = almacenDemo();
    $("aviso-demo").hidden = false; $("salir").hidden = true;
    const rol = { asesor: "asesor", asesor2: "asesor-2", jefe: "jefe", psicologa: "psicologa" }[demo] || "admin";
    escucharDemo();
    await entrarApp(await estado.almacen.perfil(`demo-${rol}`));
    return;
  }
  let config;
  try { config = await import("./config.js"); } catch { config = {}; }
  if (!config.SUPABASE_URL || !config.SUPABASE_KEY) {
    pantallaError("general", { detalle: "Falta la configuración de Supabase (config.js). En Vercel: variables SUPABASE_URL y SUPABASE_KEY.", acciones: [recargar] }); return;
  }
  if (!window.supabase) { pantallaError("conexion", { detalle: "No se pudo cargar supabase-js desde el CDN.", acciones: [recargar] }); return; }
  estado.googleMapsKey = config.GOOGLE_MAPS_KEY || "";
  estado.cliente = window.supabase.createClient(config.SUPABASE_URL, config.SUPABASE_KEY, { auth: { persistSession: true, autoRefreshToken: true } });
  estado.almacen = almacenSupabase(estado.cliente);
  estado.cliente.auth.onAuthStateChange((evento) => { if (evento === "SIGNED_OUT" && !$("app").hidden) mostrarAcceso(); });
  try {
    const { data } = await estado.cliente.auth.getSession();
    await revisarSesion(data.session);
  } catch (e) {
    pantallaError("conexion", { detalle: traducirError(e).message, acciones: [recargar] });
  }
}

iniciar();
