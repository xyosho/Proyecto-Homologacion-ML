// Vista de la PSICÓLOGA VOCACIONAL: agenda (semana que se abre en mes, "Hoy", próxima cita y espacios libres), sus
// aspirantes vocacionales y la ficha de cada uno con la entrevista (lo que respondió por el enlace y lo que ella
// completa), la salud mental (confidencial), las citas y las anotaciones.
// Salud mental: dato sensible (Ley 1581 de 2012). Solo la ve la psicóloga (RLS en Supabase) y nunca entra al modelo, al
// NLP ni a la admisión; su única salida es la remisión a Bienestar Institucional.
import { $, el, icono, avisar, conEspera, animarEntrada, hace, iniciales, PROGRAMAS, CANALES, NOMBRE_BECA, PROPENSION, pct, km, dia } from "./ui.js";
import { estado, ESTADO_ENTREVISTA, nombreAsesor, calcular, traducirError } from "./datos.js";
import { SECCIONES, CON_QUIEN_VIVE, DOCUMENTOS, ESTADO_SALUD, MOTIVOS_CITA, ESTADOS_CITA, respuestasNLP } from "./vocacional.js";

const P = { citas: [], entrevistas: new Map(), remisiones: [], cargado: false, error: null, dia: null, mesAbierto: false,
  mes: null, filtro: "todos", buscar: "", pestana: "entrevista", canal: null };
const JORNADA = { desde: 7, hasta: 18 };                         // horas para agendar (7:00 a 18:00)
const HOY = () => dia(new Date().toISOString());
const DIAS = ["L", "M", "X", "J", "V", "S", "D"];
const MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];

// ---------------------------------------------------------------------------- fechas (hora de Bogotá, UTC−5 todo el año)
const horaDe = (iso) => new Date(iso).toLocaleTimeString("es-CO", { timeZone: "America/Bogota", hour: "2-digit", minute: "2-digit", hour12: false });
const minutosDe = (iso) => { const [h, m] = horaDe(iso).split(":").map(Number); return h * 60 + m; };
const isoBogota = (fecha, hhmm) => new Date(`${fecha}T${hhmm}:00-05:00`).toISOString();
const sumarDias = (fecha, n) => { const d = new Date(`${fecha}T12:00:00-05:00`); d.setUTCDate(d.getUTCDate() + n); return dia(d.toISOString()); };
const diaSemana = (fecha) => (new Date(`${fecha}T12:00:00-05:00`).getUTCDay() + 6) % 7;   // 0 = lunes
const textoDia = (fecha) => new Date(`${fecha}T12:00:00-05:00`).toLocaleDateString("es-CO", { timeZone: "America/Bogota", weekday: "long", day: "numeric", month: "long" });
const hhmm = (min) => `${String(Math.floor(min / 60)).padStart(2, "0")}:${String(min % 60).padStart(2, "0")}`;
const coma1 = (v) => (v === null || v === undefined ? "—" : Number(v).toFixed(1).replace(".", ","));

// ---------------------------------------------------------------------------- datos
const aspirante = (id) => estado.aspirantes.find((a) => a.id === id);
const vocacionales = () => estado.aspirantes.filter((a) => a.estado_entrevista);
const citasDe = (id) => P.citas.filter((c) => c.aspirante_id === id).sort((x, y) => x.inicio.localeCompare(y.inicio));
const citasDelDia = (fecha) => P.citas.filter((c) => dia(c.inicio) === fecha && c.estado !== "CANCELADA").sort((x, y) => x.inicio.localeCompare(y.inicio));
const proximaDe = (id) => citasDe(id).find((c) => c.estado === "PENDIENTE" && new Date(c.inicio) >= new Date(Date.now() - 3600e3));
export async function cargarPsicologia() {
  try {
    const [citas, entrevistas, remisiones] = await Promise.all([estado.almacen.listarCitas(), estado.almacen.listarEntrevistas(), estado.almacen.remisiones()]);
    P.citas = citas; P.entrevistas = new Map(entrevistas.map((v) => [v.aspirante_id, v])); P.remisiones = remisiones;
    P.cargado = true; P.error = null;
  } catch (e) { P.error = traducirError(e); }
  document.dispatchEvent(new CustomEvent("psicologia"));
}
// Tiempo real: una respuesta nueva al enlace o una cita creada en otra sesión llegan solas
export function escucharPsicologia() {
  if (!estado.cliente || P.canal) return;
  P.canal = estado.cliente.channel("psicologia-en-vivo")
    .on("postgres_changes", { event: "*", schema: "public", table: "cita_psicologia" }, () => cargarPsicologia())
    .on("postgres_changes", { event: "*", schema: "public", table: "entrevista_vocacional" }, (p) => {
      if (p.eventType === "INSERT" || (p.eventType === "UPDATE" && p.new.respondida_en && !p.old?.respondida_en)) {
        const a = aspirante(p.new.aspirante_id);
        avisar(`${a ? a.nombre : "Un aspirante"} respondió la entrevista vocacional`, "vivo", { duracion: 8000,
          accion: { texto: "Ver", fn: () => { location.hash = `#/vocacional/${p.new.aspirante_id}`; } } });
      }
      cargarPsicologia();
    })
    .subscribe();
}

// ---------------------------------------------------------------------------- piezas
const avatar = (a) => el("span", { class: "avatar", dataset: { tono: String((a.nombre || "?").length % 6) }, "aria-hidden": "true", text: iniciales(a.nombre || "?") });
const chipEstado = (e) => el("span", { class: "chip", dataset: { tono: `ENT-${e}` } }, ESTADO_ENTREVISTA[e] || "Sin entrevista");
function contacto(a) {
  const tel = a.telefono ? a.telefono.replace(/[^0-9+]/g, "") : "";
  const wa = tel ? (tel.startsWith("+") ? tel.slice(1) : tel.length === 10 ? "57" + tel : tel) : "";
  return { tel, wa };
}
function hoja(titulo, contenido, { ancho = false } = {}) {             // hoja inferior en el celular, ventana en el computador
  const d = el("dialog", { class: `ps-hoja${ancho ? " ancha" : ""}`, "aria-label": titulo },
    el("header", {}, el("h2", { text: titulo }), el("button", { type: "button", class: "cerrar", "aria-label": "Cerrar", onclick: () => d.close() }, icono("x"))),
    contenido);
  d.addEventListener("close", () => d.remove());
  d.addEventListener("click", (ev) => { if (ev.target === d) d.close(); });
  document.body.append(d); d.showModal();
  return d;
}

// ---------------------------------------------------------------------------- vista: agenda
export function pintarAgenda() {
  const v = $("vista-agenda");
  if (!P.dia) { P.dia = HOY(); P.mes = P.dia.slice(0, 7); }
  if (!P.cargado) { v.replaceChildren(cabezaAgenda(), el("div", { class: "tarjeta vacio-centro" }, el("span", { class: "giro" }), P.error ? P.error.message : "Cargando la agenda…")); return; }
  const hoy = citasDelDia(HOY()), hechas = hoy.filter((c) => c.estado === "ATENDIDA").length;
  const porEntrevistar = vocacionales().filter((a) => ["RESPONDIDA", "ENVIADA"].includes(a.estado_entrevista) && !proximaDe(a.id)).length;
  const proxima = hoy.find((c) => c.estado === "PENDIENTE" && minutosDe(c.inicio) + c.duracion_min >= minutosDe(new Date().toISOString()));
  const remisiones = P.remisiones.filter((r) => r.estado === "PENDIENTE");
  v.replaceChildren(
    cabezaAgenda(),
    el("div", { class: "ps-rejilla" },
      el("div", { class: "pila" },
        tarjetaHoy(hoy.length, hechas, porEntrevistar),
        calendario(),
        proxima && tarjetaProxima(proxima),
        remisiones.length > 0 && tarjetaRemisiones(remisiones)),
      listaDelDia(P.dia)));
  animarEntrada(v);
}
function cabezaAgenda() {
  const h = Number(new Date().toLocaleString("en-US", { timeZone: "America/Bogota", hour: "numeric", hour12: false }));
  const saludo = h < 12 ? "Buenos días" : h < 19 ? "Buenas tardes" : "Buenas noches";
  const nombre = (estado.perfil?.nombre || "").split(/\s+/)[0];
  return el("header", { class: "cabeza-vista" },
    el("div", {}, el("p", { class: "eyebrow", text: `${saludo}${nombre ? `, ${nombre}` : ""} · ${textoDia(HOY())}` }), el("h1", { tabindex: "-1", text: "Agenda" })),
    el("button", { type: "button", class: "primario", onclick: () => formularioCita({ fecha: P.dia }) }, icono("mas"), "Agendar cita"));
}
function tarjetaHoy(total, hechas, porEntrevistar) {
  const anillo = el("div", { class: "ps-anillo", role: "img", "aria-label": `${hechas} de ${total} citas atendidas` },
    el("strong", { text: total ? `${hechas}/${total}` : "0" }), el("small", { text: "atendidas" }));
  anillo.style.setProperty("--avance", total ? hechas / total : 0);
  return el("section", { class: "ps-hoy" },
    el("div", {}, el("p", { class: "ps-hoy-titulo", text: "Hoy" }),
      el("p", { class: "ps-hoy-texto", text: total ? `${total} ${total === 1 ? "cita" : "citas"} en la agenda` : "Sin citas para hoy" }),
      el("div", { class: "ps-hoy-acciones" },
        el("button", { type: "button", onclick: () => formularioCita({ fecha: HOY() }) }, icono("mas"), "Agendar"),
        el("button", { type: "button", onclick: () => { P.filtro = "pendientes"; location.hash = "#/vocacionales"; } }, icono("aspirantes"),
          `Por agendar (${porEntrevistar})`))),
    anillo);
}
function calendario() {
  const sel = P.dia, hoy = HOY();
  const puntos = (f) => {
    const cs = P.citas.filter((c) => dia(c.inicio) === f && c.estado !== "CANCELADA");
    return el("span", { class: "ps-puntos", "aria-hidden": "true" }, cs.slice(0, 3).map((c) => el("i", { dataset: { estado: c.estado } })));
  };
  const celda = (f, fueraDeMes = false) => el("button", { type: "button", class: "ps-dia", "aria-pressed": String(f === sel),
    "aria-label": `${textoDia(f)}${P.citas.some((c) => dia(c.inicio) === f && c.estado !== "CANCELADA") ? ", con citas" : ""}`,
    dataset: { hoy: String(f === hoy), fuera: String(fueraDeMes) }, onclick: () => { P.dia = f; P.mes = f.slice(0, 7); pintarAgenda(); } },
    el("span", { text: String(Number(f.slice(8))) }), puntos(f));
  const cabeza = el("div", { class: "ps-dias-semana", "aria-hidden": "true" }, DIAS.map((d) => el("span", { text: d })));
  let cuerpo, titulo;
  if (P.mesAbierto) {
    const primero = `${P.mes}-01`, inicio = sumarDias(primero, -diaSemana(primero));
    cuerpo = el("div", { class: "ps-mes" }, Array.from({ length: 42 }, (_, i) => { const f = sumarDias(inicio, i); return celda(f, f.slice(0, 7) !== P.mes); }));
    const [anio, m] = P.mes.split("-").map(Number);
    titulo = `${MESES[m - 1][0].toUpperCase()}${MESES[m - 1].slice(1)} de ${anio}`;
  } else {
    const lunes = sumarDias(sel, -diaSemana(sel));
    cuerpo = el("div", { class: "ps-semana" }, Array.from({ length: 7 }, (_, i) => celda(sumarDias(lunes, i))));
    titulo = `Semana del ${Number(lunes.slice(8))} de ${MESES[Number(lunes.slice(5, 7)) - 1]}`;
  }
  const mover = (n) => {
    if (P.mesAbierto) { const [a, m] = P.mes.split("-").map(Number); const d = new Date(Date.UTC(a, m - 1 + n, 1)); P.mes = d.toISOString().slice(0, 7); }
    else { P.dia = sumarDias(P.dia, 7 * n); P.mes = P.dia.slice(0, 7); }
    pintarAgenda();
  };
  const c = el("section", { class: "tarjeta ps-calendario" },
    el("div", { class: "ps-cal-cabeza" },
      el("button", { type: "button", class: "icono-boton", "aria-label": P.mesAbierto ? "Mes anterior" : "Semana anterior", onclick: () => mover(-1) }, icono("flecha-izq")),
      el("h2", { text: titulo }),
      el("button", { type: "button", class: "icono-boton", "aria-label": P.mesAbierto ? "Mes siguiente" : "Semana siguiente", onclick: () => mover(1) }, icono("flecha-der"))),
    cabeza, cuerpo,
    el("div", { class: "ps-cal-pie" },
      el("button", { type: "button", class: "enlace", onclick: () => { P.mesAbierto = !P.mesAbierto; P.mes = P.dia.slice(0, 7); pintarAgenda(); } },
        icono(P.mesAbierto ? "flecha-izq" : "calendario"), P.mesAbierto ? "Ver solo la semana" : "Ver el mes completo"),
      sel !== hoy && el("button", { type: "button", class: "enlace", onclick: () => { P.dia = hoy; P.mes = hoy.slice(0, 7); pintarAgenda(); } }, "Ir a hoy"),
      el("span", { class: "ps-leyenda" }, el("i", { dataset: { estado: "PENDIENTE" } }), "pendiente", el("i", { dataset: { estado: "ATENDIDA" } }), "atendida",
        el("i", { dataset: { estado: "NO_ASISTIO" } }), "no asistió")));
  // Deslizar a los lados cambia de semana o de mes (celular)
  let x0 = null;
  c.addEventListener("touchstart", (e) => { x0 = e.touches[0].clientX; }, { passive: true });
  c.addEventListener("touchend", (e) => { if (x0 === null) return; const dx = e.changedTouches[0].clientX - x0; x0 = null; if (Math.abs(dx) > 60) mover(dx < 0 ? 1 : -1); });
  return c;
}
function tarjetaProxima(c) {
  const a = aspirante(c.aspirante_id) || { nombre: "Aspirante" }, { tel, wa } = contacto(a);
  const enCurso = minutosDe(c.inicio) <= minutosDe(new Date().toISOString());
  return el("section", { class: "tarjeta ps-proxima" },
    el("p", { class: "eyebrow", text: enCurso ? "En curso" : `Próxima · ${horaDe(c.inicio)}` }),
    el("div", { class: "persona" }, avatar(a), el("div", { class: "persona-texto" }, el("b", { text: a.nombre }),
      el("small", { text: `${MOTIVOS_CITA[c.motivo]} · ${c.duracion_min} min · ${c.modalidad === "VIRTUAL" ? "virtual" : "presencial"}` }))),
    el("div", { class: "acciones" },
      el("a", { class: "boton primario", href: `#/vocacional/${c.aspirante_id}` }, icono("check"), "Atender"),
      wa && el("a", { class: "boton discreto", href: `https://wa.me/${wa}`, target: "_blank", rel: "noopener noreferrer" }, icono("mensaje"), "WhatsApp"),
      tel && el("a", { class: "boton discreto", href: `tel:${tel}` }, icono("telefono"), "Llamar")));
}
function tarjetaRemisiones(lista) {
  return el("section", { class: "tarjeta ps-remisiones" },
    el("div", { class: "tarjeta-cabeza" }, el("h2", {}, icono("escudo"), "Remisiones a Bienestar"), el("span", { class: "chip", text: String(lista.length) })),
    el("ul", { class: "ps-lista-simple" }, lista.map((r) => {
      const a = aspirante(r.aspirante_id) || { nombre: "Aspirante" };
      return el("li", {}, el("a", { href: `#/vocacional/${r.aspirante_id}`, text: a.nombre }), el("small", { text: `pendiente desde ${hace(r.creada_en)}` }),
        el("button", { type: "button", class: "enlace", onclick: async (ev) => {
          try { await conEspera(ev.currentTarget, "…", () => estado.almacen.actualizarRemision(r.id, { estado: "ENVIADA" })); await cargarPsicologia(); avisar("Remisión marcada como enviada.", "exito", { duracion: 2000 }); }
          catch (e) { avisar(traducirError(e).message, "error"); }
        } }, "Marcar enviada"));
    })),
    el("p", { class: "nota", text: "Confidencial. La remisión no afecta la admisión ni la predicción." }));
}
function listaDelDia(fecha) {
  const cs = citasDelDia(fecha), pasado = fecha < HOY();
  const items = [];
  let cursor = JORNADA.desde * 60;
  const ahora = fecha === HOY() ? minutosDe(new Date().toISOString()) : pasado ? 24 * 60 : 0;
  const libre = (desde, hasta) => {
    const d = Math.max(desde, Math.ceil(ahora / 30) * 30);
    if (hasta - d >= 30) items.push(el("li", { class: "ps-libre" }, el("button", { type: "button", onclick: () => formularioCita({ fecha, hora: hhmm(d) }) },
      icono("mas", "ic ic-chico"), `Libre ${hhmm(d)} – ${hhmm(hasta)} · Agendar`)));
  };
  for (const c of cs) {
    const ini = minutosDe(c.inicio);
    if (!pasado) libre(cursor, ini);
    items.push(tarjetaCita(c));
    cursor = Math.max(cursor, ini + c.duracion_min);
  }
  if (!pasado) libre(cursor, JORNADA.hasta * 60);
  const canceladas = P.citas.filter((c) => dia(c.inicio) === fecha && c.estado === "CANCELADA").length;
  return el("section", { class: "tarjeta ps-dia-lista" },
    el("div", { class: "tarjeta-cabeza" }, el("h2", { text: textoDia(fecha).replace(/^./, (x) => x.toUpperCase()) }),
      el("span", { class: "chip", text: `${cs.length} ${cs.length === 1 ? "cita" : "citas"}` })),
    items.length ? el("ol", { class: "ps-citas" }, items)
      : el("p", { class: "vacio-centro", text: pasado ? "No hubo citas este día." : "Sin espacios libres en la jornada." }),
    canceladas ? el("p", { class: "nota", text: `${canceladas} ${canceladas === 1 ? "cita cancelada" : "citas canceladas"} este día.` }) : null);
}
function tarjetaCita(c) {
  const a = aspirante(c.aspirante_id) || { nombre: "Aspirante (sin acceso)" };
  return el("li", { class: "ps-cita", dataset: { estado: c.estado, motivo: c.motivo } },
    el("button", { type: "button", class: "ps-cita-cuerpo", onclick: () => accionesCita(c), "aria-label": `Opciones de la cita con ${a.nombre}` },
      el("span", { class: "ps-cita-hora" }, el("b", { text: horaDe(c.inicio) }), el("small", { text: `${c.duracion_min} min` })),
      el("span", { class: "ps-cita-barra", "aria-hidden": "true" }),
      el("span", { class: "ps-cita-texto" }, el("b", { text: a.nombre }),
        el("small", { text: `${MOTIVOS_CITA[c.motivo]} · ${c.modalidad === "VIRTUAL" ? "virtual" : "presencial"}` }),
        c.estado !== "PENDIENTE" && el("span", { class: "chip", dataset: { tono: `CITA-${c.estado}` }, text: ESTADOS_CITA[c.estado] }))),
    c.estado === "PENDIENTE" && el("button", { type: "button", class: "ps-atender", "aria-label": `Marcar atendida la cita con ${a.nombre}`,
      onclick: () => cambiarCita(c, { estado: "ATENDIDA" }, "Cita atendida.") }, icono("check")));
}
async function cambiarCita(c, cambios, mensaje) {
  try {
    await estado.almacen.guardarCita({ id: c.id, ...cambios });
    await cargarPsicologia();
    const anterior = { estado: c.estado };
    avisar(mensaje, "exito", { duracion: 5000, accion: cambios.estado ? { texto: "Deshacer", fn: async () => { await estado.almacen.guardarCita({ id: c.id, ...anterior }); cargarPsicologia(); } } : null });
  } catch (e) { avisar(traducirError(e).message, "error"); }
}
function accionesCita(c) {
  const a = aspirante(c.aspirante_id) || { nombre: "Aspirante" }, { tel, wa } = contacto(a);
  const boton = (ic, texto, fn, tono = "") => el("button", { type: "button", class: "ps-accion", dataset: { tono }, onclick: () => { d.close(); fn(); } }, icono(ic), texto);
  const d = hoja(`${a.nombre} · ${horaDe(c.inicio)}`, el("div", { class: "ps-acciones" },
    boton("check", "Atender", () => { location.hash = `#/vocacional/${c.aspirante_id}`; }),
    wa && boton("mensaje", "WhatsApp", () => window.open(`https://wa.me/${wa}`, "_blank", "noopener")),
    tel && boton("telefono", "Llamar", () => { location.href = `tel:${tel}`; }),
    boton("calendario", "Reprogramar", () => formularioCita({ cita: c })),
    boton("usuario", "Ver aspirante", () => { location.hash = `#/vocacional/${c.aspirante_id}`; }),
    c.estado === "PENDIENTE" && boton("x", "No asistió", () => cambiarCita(c, { estado: "NO_ASISTIO" }, "Marcada como no asistió."), "alerta"),
    c.estado !== "CANCELADA" && boton("x", "Cancelar cita", () => cambiarCita(c, { estado: "CANCELADA" }, "Cita cancelada."), "peligro"),
    c.estado !== "PENDIENTE" && boton("recargar", "Volver a pendiente", () => cambiarCita(c, { estado: "PENDIENTE" }, "La cita volvió a pendiente.")),
    boton("basura", "Eliminar", async () => {
      try { await estado.almacen.borrarCita(c.id); await cargarPsicologia(); avisar("Cita eliminada.", "info", { duracion: 2500 }); }
      catch (e) { avisar(traducirError(e).message, "error"); }
    }, "peligro")));
  return d;
}

// ---------------------------------------------------------------------------- formulario de cita (nueva o reprogramar)
export function formularioCita({ fecha = null, hora = null, aspiranteId = null, cita = null } = {}) {
  if (!P.cargado) { avisar("La agenda aún está cargando.", "info", { duracion: 2000 }); return; }
  const s = { aspirante: cita ? cita.aspirante_id : aspiranteId, fecha: cita ? dia(cita.inicio) : fecha || HOY(), hora: cita ? horaDe(cita.inicio) : hora,
    dur: cita ? cita.duracion_min : 45, motivo: cita ? cita.motivo : "ENTREVISTA_VOCACIONAL", modalidad: cita ? cita.modalidad : "PRESENCIAL" };
  const lista = vocacionales().sort((x, y) => (x.nombre || "").localeCompare(y.nombre || "", "es"));
  if (!lista.length) { avisar("Todavía no hay aspirantes con entrevista vocacional enviada.", "info"); return; }
  const cuerpo = el("form", { class: "ps-form", novalidate: true });
  const chips = (opciones, clave, alCambiar) => el("div", { class: "ps-chips", role: "group" }, Object.entries(opciones).map(([v, t]) =>
    el("button", { type: "button", class: "ps-chip", "aria-pressed": String(String(s[clave]) === String(v)), onclick: () => { s[clave] = isNaN(v) ? v : Number(v); alCambiar(); } }, t)));
  const ocupado = (fecha, min) => P.citas.some((c) => c.estado !== "CANCELADA" && (!cita || c.id !== cita.id) && dia(c.inicio) === fecha
    && min < minutosDe(c.inicio) + c.duracion_min && minutosDe(c.inicio) < min + s.dur);
  const pintar = () => {
    const opcionesDia = { [HOY()]: "Hoy", [sumarDias(HOY(), 1)]: "Mañana", [sumarDias(HOY(), 2)]: "Pasado mañana" };
    const choque = s.hora && ocupado(s.fecha, Number(s.hora.slice(0, 2)) * 60 + Number(s.hora.slice(3)));
    const horas = [];
    for (let m = JORNADA.desde * 60; m < JORNADA.hasta * 60; m += 30) horas.push(m);
    const ahora = s.fecha === HOY() ? minutosDe(new Date().toISOString()) : s.fecha < HOY() ? 24 * 60 : 0;
    cuerpo.replaceChildren(
      el("div", { class: "campo" }, el("label", { for: "ps-aspirante", text: "Aspirante" }),
        el("select", { id: "ps-aspirante", required: true, onchange: (e) => { s.aspirante = e.target.value; } },
          el("option", { value: "", text: "Elija el aspirante" }),
          lista.map((a) => el("option", { value: a.id, text: `${a.nombre} · ${ESTADO_ENTREVISTA[a.estado_entrevista]}`, selected: a.id === s.aspirante })))),
      el("div", { class: "campo" }, el("span", { class: "etiqueta", text: "Día" }),
        el("div", { class: "ps-fila" }, chips(opcionesDia, "fecha", pintar),
          el("input", { type: "date", value: s.fecha, min: HOY(), "aria-label": "Otra fecha", onchange: (e) => { if (e.target.value) { s.fecha = e.target.value; pintar(); } } }))),
      el("div", { class: "campo" }, el("span", { class: "etiqueta", text: "Hora" }),
        el("div", { class: "ps-horas", role: "group", "aria-label": "Hora de inicio" }, horas.map((m) => el("button", { type: "button", class: "ps-hora",
          "aria-pressed": String(s.hora === hhmm(m)), disabled: m < ahora, dataset: { ocupado: String(ocupado(s.fecha, m)) },
          onclick: () => { s.hora = hhmm(m); pintar(); } }, hhmm(m))))),
      el("div", { class: "campo" }, el("span", { class: "etiqueta", text: "Duración" }), chips({ 30: "30 min", 45: "45 min", 60: "60 min", 90: "90 min" }, "dur", pintar)),
      el("div", { class: "campo" }, el("span", { class: "etiqueta", text: "Motivo" }), chips(MOTIVOS_CITA, "motivo", pintar)),
      el("div", { class: "campo" }, el("span", { class: "etiqueta", text: "Modalidad" }), chips({ PRESENCIAL: "Presencial", VIRTUAL: "Virtual" }, "modalidad", pintar)),
      choque && el("p", { class: "aviso-suave", role: "alert" }, icono("alerta", "ic ic-chico"), "Se cruza con otra cita de ese día. Puede guardarla igual o elegir otra hora."),
      el("div", { class: "ps-pegajoso" }, el("button", { type: "submit", class: "primario ancho" }, icono("check"), cita ? "Guardar cambios" : "Agendar cita")));
  };
  cuerpo.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (!s.aspirante) { avisar("Elija el aspirante.", "error", { duracion: 2500 }); return; }
    if (!s.hora) { avisar("Elija la hora.", "error", { duracion: 2500 }); return; }
    try {
      await conEspera(cuerpo.querySelector("[type=submit]"), "Guardando…", () => estado.almacen.guardarCita({ ...(cita ? { id: cita.id } : {}),
        aspirante_id: s.aspirante, inicio: isoBogota(s.fecha, s.hora), duracion_min: s.dur, motivo: s.motivo, modalidad: s.modalidad,
        ...(cita ? { estado: "PENDIENTE" } : {}) }));
      d.close();
      P.dia = s.fecha; P.mes = s.fecha.slice(0, 7);
      await cargarPsicologia();
      if (!cita && estado.demo) document.dispatchEvent(new CustomEvent("aspirantes", { detail: { tipo: "actualizado" } }));
      avisar(cita ? "Cita reprogramada." : "Cita agendada.", "exito", { duracion: 2500 });
    } catch (e) { avisar(traducirError(e).message, "error"); }
  });
  pintar();
  const d = hoja(cita ? "Reprogramar cita" : "Agendar cita", cuerpo, { ancho: true });
}

// ---------------------------------------------------------------------------- vista: aspirantes vocacionales
export function pintarVocacionales() {
  const v = $("vista-vocacionales");
  const todos = vocacionales();
  const grupos = {
    todos: ["Todos", () => true],
    pendientes: ["Por entrevistar", (a) => a.estado_entrevista !== "ENTREVISTADA"],
    cita: ["Con cita", (a) => Boolean(proximaDe(a.id))],
    sin: ["Sin cita", (a) => !proximaDe(a.id) && a.estado_entrevista !== "ENTREVISTADA"],
    hechos: ["Entrevistados", (a) => a.estado_entrevista === "ENTREVISTADA"],
  };
  const q = P.buscar.trim().toLowerCase();
  const lista = todos.filter(grupos[P.filtro][1]).filter((a) => !q || (a.nombre || "").toLowerCase().includes(q))
    .sort((x, y) => (proximaDe(x.id)?.inicio || "9").localeCompare(proximaDe(y.id)?.inicio || "9") || (x.nombre || "").localeCompare(y.nombre || "", "es"));
  const buscar = el("input", { type: "search", placeholder: "Buscar por nombre", value: P.buscar, "aria-label": "Buscar aspirante",
    oninput: (e) => { P.buscar = e.target.value; const pos = e.target.selectionStart; pintarVocacionales(); const i = $("ps-buscar"); i.focus(); i.setSelectionRange(pos, pos); } });
  buscar.id = "ps-buscar";
  v.replaceChildren(
    el("header", { class: "cabeza-vista" }, el("div", {}, el("p", { class: "eyebrow", text: "Entrevista vocacional" }), el("h1", { tabindex: "-1", text: "Aspirantes vocacionales" })),
      el("button", { type: "button", class: "primario", onclick: () => formularioCita({}) }, icono("mas"), "Agendar cita")),
    el("div", { class: "ps-buscador" }, icono("buscar"), buscar),
    el("div", { class: "ps-segmentos", role: "group", "aria-label": "Filtrar" }, Object.entries(grupos).map(([k, [t, f]]) =>
      el("button", { type: "button", "aria-pressed": String(P.filtro === k), onclick: () => { P.filtro = k; pintarVocacionales(); } },
        t, el("span", { class: "contador", text: String(todos.filter(f).length) })))),
    lista.length ? el("ul", { class: "ps-tarjetas" }, lista.map(tarjetaAspirante))
      : el("div", { class: "tarjeta vacio-centro" }, icono("aspirantes", "ic vacio-icono"),
        el("p", { text: todos.length ? "Ningún aspirante coincide con el filtro." : "Aún no hay aspirantes: le llegan cuando un asesor les envía la entrevista vocacional." })));
  const n = $("nav-contador-voc"); if (n) n.textContent = todos.filter(grupos.pendientes[1]).length || "";
}
function tarjetaAspirante(a) {
  const prox = proximaDe(a.id), v = P.entrevistas.get(a.id);
  return el("li", {}, el("a", { class: "ps-tarjeta", href: `#/vocacional/${a.id}` },
    avatar(a),
    el("span", { class: "persona-texto" }, el("b", { text: a.nombre }), el("small", { text: `${a.programa === "SSIA" ? "Sistemas de Software e IA" : "Analítica de Datos"} · ${a.periodo}` }),
      el("small", { class: "ps-cuando", text: prox ? `Cita ${textoDia(dia(prox.inicio))} · ${horaDe(prox.inicio)}`
        : v?.respondida_en ? `Respondió ${hace(v.respondida_en)}` : a.estado_entrevista === "ENVIADA" ? "Esperando sus respuestas" : "Sin cita" }),
      chipEstado(a.estado_entrevista))));
}

// ---------------------------------------------------------------------------- vista: ficha vocacional
export function pintarFichaVocacional(id) {
  const v = $("vista-vocacional"), a = aspirante(id);
  if (!a || !a.estado_entrevista) {
    v.replaceChildren(el("a", { class: "volver", href: "#/vocacionales" }, icono("flecha-izq"), "Volver"),
      el("div", { class: "tarjeta vacio-centro" }, el("h1", { tabindex: "-1", text: "No encontramos a este aspirante" }),
        el("p", { class: "nota", text: "Puede que no tenga entrevista vocacional o que su cuenta no tenga acceso." })));
    return true;
  }
  const { tel, wa } = contacto(a), citas = citasDe(id), resumen = P.entrevistas.get(id);
  v.dataset.sinAgenda = P.cargado ? "" : "1";       // se pintó antes de que llegaran sus citas: se repinta al llegar
  v.replaceChildren(
    el("a", { class: "volver", href: "#/vocacionales" }, icono("flecha-izq"), "Aspirantes vocacionales"),
    el("header", { class: "ps-perfil tarjeta" },
      el("div", { class: "persona grande" }, el("span", { class: "avatar grande", "aria-hidden": "true", text: iniciales(a.nombre) }),
        el("div", {}, el("h1", { tabindex: "-1", text: a.nombre }),
          el("div", { class: "chips" }, chipEstado(a.estado_entrevista), el("span", { class: "chip", text: a.programa }), el("span", { class: "chip", text: a.periodo })),
          el("p", { class: "nota", text: `Asesor: ${nombreAsesor(a.asesor_id)}` }))),
      el("div", { class: "ps-cifras" },
        cifra(String(citas.filter((c) => c.estado !== "CANCELADA").length), "citas"),
        cifra(a.puntaje_vocacional ?? resumen?.puntaje_vocacional ?? "—", "puntaje vocacional"),
        cifra(coma1(puntajeNLPDe(id) ?? a.puntaje_vocacional_nlp), "según sus palabras"),
        cifra(a.probabilidad_matricula === null || a.probabilidad_matricula === undefined ? "—" : pct(a.probabilidad_matricula), "prob. de matrícula")),
      el("div", { class: "acciones" },
        el("button", { type: "button", class: "primario", onclick: () => formularioCita({ aspiranteId: id }) }, icono("calendario"), "Agendar"),
        el("button", { type: "button", class: "secundario", onclick: () => { P.pestana = "anotaciones"; pintarFichaVocacional(id); } }, icono("editar"), "Anotación"),
        wa && el("a", { class: "boton discreto", href: `https://wa.me/${wa}`, target: "_blank", rel: "noopener noreferrer" }, icono("mensaje"), "WhatsApp"),
        tel && el("a", { class: "boton discreto", href: `tel:${tel}` }, icono("telefono"), "Llamar"),
        a.correo && el("a", { class: "boton discreto", href: `mailto:${a.correo}` }, icono("correo"), "Correo"))),
    el("nav", { class: "ps-pestanas", role: "tablist", "aria-label": "Secciones del aspirante" },
      [["entrevista", "Entrevista"], ["citas", `Citas (${citas.length})`], ["anotaciones", "Anotaciones"], ["datos", "Datos generales"]].map(([k, t]) =>
        el("button", { type: "button", role: "tab", "aria-selected": String(P.pestana === k), onclick: () => { P.pestana = k; pintarFichaVocacional(id); } }, t))),
    el("div", { id: "ps-pestana", role: "tabpanel" }));
  const panel = $("ps-pestana");
  if (P.pestana === "entrevista") pestanaEntrevista(panel, a);
  if (P.pestana === "citas") pestanaCitas(panel, a, citas);
  if (P.pestana === "anotaciones") pestanaAnotaciones(panel, a);
  if (P.pestana === "datos") pestanaDatos(panel, a);
  return true;
}
const cifra = (valor, texto) => el("div", { class: "ps-cifra" }, el("strong", { text: String(valor) }), el("small", { text: texto }));
const nlpCache = new Map();
function puntajeNLPDe(id) {
  const v = nlpCache.get(id);
  return v === undefined ? null : v;
}

async function pestanaEntrevista(panel, a) {
  panel.replaceChildren(el("div", { class: "tarjeta vacio-centro" }, el("span", { class: "giro" }), "Cargando la entrevista…"));
  let v, sm;
  try { [v, sm] = await Promise.all([estado.almacen.entrevista(a.id), estado.almacen.saludMental(a.id)]); }
  catch (e) { panel.replaceChildren(el("p", { class: "error-general", text: traducirError(e).message })); return; }
  v = v || { respuestas: {} };
  const r = v.respuestas || {}, resp = r.respuestas || {}, datos = r.datos || {};
  const tieneRespuestas = Boolean(v.respondida_en);
  const nlp = tieneRespuestas ? estado.modelo.puntajeNLP(respuestasNLP(r)) : null;
  if (nlpCache.get(a.id) !== nlp) { nlpCache.set(a.id, nlp); }
  const cerrada = Boolean(v.cerrada_en);
  // 1) Lo que respondió el aspirante (secciones 1 a 7)
  const respuestas = el("section", { class: "tarjeta" },
    el("div", { class: "tarjeta-cabeza" }, el("h2", {}, icono("mensaje"), "Lo que respondió el aspirante"),
      tieneRespuestas ? el("span", { class: "chip", text: `Respondió ${hace(v.respondida_en)}` }) : el("span", { class: "chip", dataset: { tono: "ENT-ENVIADA" }, text: "Sin responder" })),
    tieneRespuestas ? el("div", { class: "pila-chica" },
      el("dl", { class: "resumen" }, [["Nombre", datos.nombre], ["Documento", datos.tipo_documento ? `${DOCUMENTOS[datos.tipo_documento]} ${datos.numero_documento}` : "—"],
        ["Celular", datos.celular], ["Correo", datos.correo || "—"], ["Programa de interés", PROGRAMAS[r.programa] || r.programa], ["Sede", r.sede || "—"],
        ["¿Con quién vive?", [...(resp.h2 || []), resp.h2_parentesco].filter(Boolean).join(", ") || "—"]]
        .flatMap(([k, x]) => [el("dt", { text: k }), el("dd", { text: x ?? "—" })])),
      SECCIONES.map((s) => el("details", { class: "ps-seccion", open: s.id === "programa" },
        el("summary", { text: s.titulo }),
        el("dl", { class: "ps-qa" }, s.preguntas.flatMap(([k, q]) => [el("dt", { text: q }), el("dd", { text: resp[k] || "—" })])))),
      el("p", { class: "ps-nlp" }, icono("chispa"), el("span", {}, "Puntaje vocacional en sus palabras (modelo NLP): ", el("b", { text: `${coma1(nlp)} de 5` }),
        ". Se calcula con interés por el programa, historia de vida e interés por la universidad; nunca con la salud mental.")))
      : el("p", { class: "nota", text: a.estado_entrevista === "ENVIADA" ? "El asesor envió el enlace; las respuestas aparecen aquí apenas el aspirante lo envíe. Igual puede agendar y hacer la entrevista." : "Sin respuestas por enlace." }));
  // 2) Lo que completa la psicóloga (secciones 8 a 10)
  const f = { modalidad: v.modalidad || "PRESENCIAL", apariencia_actitud: v.apariencia_actitud || "", notas: v.notas || "",
    segunda_entrevista: v.segunda_entrevista ?? null, segunda_con: v.segunda_con || null, requiere_bienestar: v.requiere_bienestar ?? null,
    nota_bienestar: "", admitido: v.admitido ?? null, puntaje_vocacional: v.puntaje_vocacional ?? a.puntaje_vocacional ?? null };
  const siNo = (clave, alCambiar = () => {}) => el("div", { class: "ps-chips", role: "radiogroup" }, [[true, "Sí"], [false, "No"]].map(([val, t]) =>
    el("button", { type: "button", class: "ps-chip", role: "radio", "aria-checked": String(f[clave] === val), onclick: (e) => { f[clave] = val; marcar(e.currentTarget); alCambiar(); } }, t)));
  const marcar = (b) => b.parentElement.querySelectorAll("button").forEach((x) => x.setAttribute("aria-checked", String(x === b)));
  const segundaCon = el("div", { class: "ps-chips", hidden: f.segunda_entrevista !== true }, [["BIENESTAR", "Bienestar Institucional"], ["DIRECTOR_PROGRAMA", "Director de programa"]].map(([val, t]) =>
    el("button", { type: "button", class: "ps-chip", role: "radio", "aria-checked": String(f.segunda_con === val), onclick: (e) => { f.segunda_con = val; marcar(e.currentTarget); } }, t)));
  const notaBienestar = el("textarea", { rows: 2, maxlength: 1000, placeholder: "Nota para Bienestar (opcional, confidencial)", hidden: f.requiere_bienestar !== true,
    oninput: (e) => { f.nota_bienestar = e.target.value; } });
  const puntajes = el("div", { class: "ps-puntajes", role: "radiogroup", "aria-label": "Puntaje vocacional" }, [1, 2, 3, 4, 5].map((n) =>
    el("button", { type: "button", role: "radio", "aria-checked": String(f.puntaje_vocacional === n), onclick: (e) => { f.puntaje_vocacional = n; marcar(e.currentTarget); } },
      el("b", { text: String(n) }), el("small", { text: ["muy débil", "débil", "aceptable", "buena", "sobresaliente"][n - 1] }))));
  const texto = (clave, etiqueta, ayuda) => el("div", { class: "campo" }, el("label", { text: etiqueta }), ayuda && el("span", { class: "ayuda", text: ayuda }),
    el("textarea", { rows: 4, maxlength: 3000, oninput: (e) => { f[clave] = e.target.value; } }, f[clave]));
  const guardar = el("button", { type: "button", class: "secundario" }, icono("check"), "Guardar borrador");
  const cerrar = el("button", { type: "button", class: "primario" }, icono("chispa"), cerrada ? "Actualizar y volver a predecir" : "Cerrar entrevista y predecir");
  const conclusion = el("section", { class: "tarjeta" },
    el("div", { class: "tarjeta-cabeza" }, el("h2", {}, icono("editar"), "La entrevista"), cerrada && el("span", { class: "chip", dataset: { tono: "ENT-ENTREVISTADA" }, text: `Cerrada ${hace(v.cerrada_en)}` })),
    el("div", { class: "campo" }, el("span", { class: "etiqueta", text: "Modalidad" }),
      el("div", { class: "ps-chips", role: "radiogroup" }, [["PRESENCIAL", "Presencial"], ["VIRTUAL", "Virtual"]].map(([val, t]) =>
        el("button", { type: "button", class: "ps-chip", role: "radio", "aria-checked": String(f.modalidad === val), onclick: (e) => { f.modalidad = val; marcar(e.currentTarget); } }, t)))),
    texto("apariencia_actitud", "Apariencia y actitud", "Breve descripción: expresión verbal y corporal, comprensión y capacidad argumentativa."),
    texto("notas", "Notas", "Sugerencias y todo lo relevante que haya quedado por fuera de la entrevista estructurada."),
    el("div", { class: "ps-conclusion" },
      el("div", { class: "campo" }, el("span", { class: "etiqueta", text: "Segunda entrevista" }), siNo("segunda_entrevista", () => { segundaCon.hidden = f.segunda_entrevista !== true; }), segundaCon),
      el("div", { class: "campo" }, el("span", { class: "etiqueta", text: "¿Requiere acompañamiento y seguimiento de Bienestar Institucional?" }),
        siNo("requiere_bienestar", () => { notaBienestar.hidden = f.requiere_bienestar !== true; }), notaBienestar,
        el("span", { class: "ayuda", text: "Si marca Sí, se abre una remisión confidencial a Bienestar. No afecta la admisión ni la predicción." })),
      el("div", { class: "campo" }, el("span", { class: "etiqueta", text: "Admitido" }), siNo("admitido"),
        el("span", { class: "ayuda", text: "Decisión de la entrevistadora con el formulario institucional. El modelo no la toma." }))),
    el("div", { class: "campo" }, el("span", { class: "etiqueta", text: "Puntaje vocacional (1 a 5)" }), puntajes,
      el("span", { class: "ayuda", text: "Lo usa el modelo de matrícula junto con el puntaje de sus palabras. Mi Vocación exige 3 o más." })),
    el("p", { class: "error-general", hidden: true, id: "ps-error" }),
    el("div", { class: "acciones" }, guardar, cerrar));
  guardar.addEventListener("click", async () => {
    try {
      await conEspera(guardar, "Guardando…", () => estado.almacen.guardarEntrevista(a.id, { modalidad: f.modalidad, apariencia_actitud: f.apariencia_actitud || null,
        notas: f.notas || null, segunda_entrevista: f.segunda_entrevista, segunda_con: f.segunda_entrevista ? f.segunda_con : null,
        requiere_bienestar: f.requiere_bienestar, admitido: f.admitido }));
      avisar("Borrador guardado.", "exito", { duracion: 2000 });
    } catch (e) { avisar(traducirError(e).message, "error"); }
  });
  cerrar.addEventListener("click", async () => {
    const err = $("ps-error");
    if (!f.puntaje_vocacional) { err.textContent = "Elija el puntaje vocacional de 1 a 5."; err.hidden = false; return; }
    err.hidden = true;
    try {
      await conEspera(cerrar, "Calculando…", async () => {
        const conEnt = { ...a, puntaje_vocacional: f.puntaje_vocacional, puntaje_vocacional_nlp: nlp ?? undefined,
          respuestas_entrevista: tieneRespuestas ? respuestasNLP(r) : undefined };
        const { r: pr, precios, avisos, umbral } = await calcular(conEnt);
        const prediccion = { beca: pr.beca_que_aplica, precio_neto_primer_semestre: precios.neto, probabilidad_matricula: pr.probabilidad_matricula,
          se_matricularia: pr.probabilidad_matricula >= umbral, propension: pr.segmento_propension,
          prediccion: { ...pr, avisos, precios, umbral, modelo: estado.version } };
        await estado.almacen.cerrarEntrevista(a.id, { ...f, segunda_con: f.segunda_entrevista ? f.segunda_con : null,
          puntaje_vocacional_nlp: pr.puntaje_vocacional_nlp ?? nlp }, prediccion);
      });
      await cargarPsicologia();
      document.dispatchEvent(new CustomEvent("recargar-aspirantes"));
      avisar("Entrevista cerrada: el puntaje y la predicción quedaron en la ficha del asesor.", "exito", { duracion: 4000 });
    } catch (e) { err.textContent = traducirError(e).message; err.hidden = false; }
  });
  panel.replaceChildren(el("div", { class: "columnas" }, el("div", { class: "pila" }, respuestas), el("div", { class: "pila" }, conclusion, tarjetaSaludMental(a, sm))));
}

function tarjetaSaludMental(a, sm) {
  const s = { consentimiento: Boolean(sm?.consentimiento), proceso_previo: sm?.proceso_previo ?? null, cual: sm?.cual || "", periodo: sm?.periodo || "",
    motivo: sm?.motivo || "", estado: sm?.estado || null, por_que: sm?.por_que || "" };
  const campos = el("div", { class: "pila-chica", hidden: !s.consentimiento });
  const marcar = (b) => b.parentElement.querySelectorAll("button").forEach((x) => x.setAttribute("aria-checked", String(x === b)));
  const entrada = (clave, etiqueta, max) => el("div", { class: "campo" }, el("label", { text: etiqueta }),
    el("input", { type: "text", maxlength: max, value: s[clave], oninput: (e) => { s[clave] = e.target.value; } }));
  const proceso = el("div", { class: "pila-chica", hidden: s.proceso_previo !== true }, entrada("cual", "¿Cuál?", 300), entrada("periodo", "¿Durante qué periodo de tiempo?", 200),
    entrada("motivo", "¿Por qué inició el proceso?", 1000));
  campos.append(
    el("div", { class: "campo" }, el("span", { class: "etiqueta", text: "¿En algún momento ha estado en un proceso psicológico y/o psiquiátrico?" }),
      el("div", { class: "ps-chips", role: "radiogroup" }, [[true, "Sí"], [false, "No"]].map(([val, t]) =>
        el("button", { type: "button", class: "ps-chip", role: "radio", "aria-checked": String(s.proceso_previo === val),
          onclick: (e) => { s.proceso_previo = val; marcar(e.currentTarget); proceso.hidden = val !== true; } }, t)))),
    proceso,
    el("div", { class: "campo" }, el("span", { class: "etiqueta", text: "Considera que su estado de salud mental es" }),
      el("div", { class: "ps-chips", role: "radiogroup" }, Object.entries(ESTADO_SALUD).map(([val, t]) =>
        el("button", { type: "button", class: "ps-chip", role: "radio", "aria-checked": String(s.estado === val), onclick: (e) => { s.estado = val; marcar(e.currentTarget); } }, t)))),
    el("div", { class: "campo" }, el("label", { text: "¿Por qué?" }), el("textarea", { rows: 3, maxlength: 2000, oninput: (e) => { s.por_que = e.target.value; } }, s.por_que)));
  const consentimiento = el("input", { type: "checkbox", checked: s.consentimiento, onchange: (e) => { s.consentimiento = e.target.checked; campos.hidden = !s.consentimiento; } });
  const guardar = el("button", { type: "button", class: "secundario" }, icono("candado"), "Guardar sección");
  guardar.addEventListener("click", async () => {
    if (!s.consentimiento) { avisar("Registre primero el consentimiento del aspirante.", "error", { duracion: 3000 }); return; }
    try {
      await conEspera(guardar, "Guardando…", () => estado.almacen.guardarSaludMental(a.id, { consentimiento: true, proceso_previo: s.proceso_previo,
        cual: s.proceso_previo ? s.cual || null : null, periodo: s.proceso_previo ? s.periodo || null : null, motivo: s.proceso_previo ? s.motivo || null : null,
        estado: s.estado, por_que: s.por_que || null }));
      avisar("Sección de salud mental guardada (confidencial).", "exito", { duracion: 2500 });
    } catch (e) { avisar(traducirError(e).message, "error"); }
  });
  return el("section", { class: "tarjeta ps-confidencial" },
    el("div", { class: "tarjeta-cabeza" }, el("h2", {}, icono("candado"), "Salud mental"), el("span", { class: "chip", dataset: { tono: "CONFIDENCIAL" }, text: "Confidencial" })),
    el("p", { class: "nota", text: "Dato sensible (Ley 1581 de 2012). Solo lo ve la psicóloga vocacional. No entra al modelo, al NLP, a la predicción ni a la decisión de admisión, y no se usa para excluir a nadie. Si hace falta, la salida es la remisión a Bienestar Institucional." }),
    el("label", { class: "ps-consentimiento" }, consentimiento, el("span", { text: "El aspirante autorizó de forma expresa registrar esta sección." })),
    campos,
    el("div", { class: "acciones" }, guardar));
}

function pestanaCitas(panel, a, citas) {
  panel.replaceChildren(el("section", { class: "tarjeta" },
    el("div", { class: "tarjeta-cabeza" }, el("h2", {}, icono("calendario"), "Citas"),
      el("button", { type: "button", class: "secundario", onclick: () => formularioCita({ aspiranteId: a.id }) }, icono("mas"), "Agendar")),
    citas.length ? el("ol", { class: "ps-citas" }, citas.slice().reverse().map((c) => {
      const li = tarjetaCita(c);
      li.querySelector(".ps-cita-hora b").textContent = `${new Date(c.inicio).toLocaleDateString("es-CO", { timeZone: "America/Bogota", day: "numeric", month: "short" })} ${horaDe(c.inicio)}`;
      return li;
    })) : el("p", { class: "vacio-centro", text: "Sin citas todavía." })));
}

async function pestanaAnotaciones(panel, a) {
  const caja = el("textarea", { rows: 4, maxlength: 4000, placeholder: "¿Qué se trabajó? Acuerdos, observaciones, próximos pasos…", "aria-label": "Nueva anotación" });
  const guardar = el("button", { type: "button", class: "primario" }, icono("check"), "Guardar anotación");
  const lista = el("ol", { class: "ps-notas" });
  const pintar = async () => {
    let l = [];
    try { l = await estado.almacen.anotaciones(a.id); } catch (e) { lista.replaceChildren(el("li", { text: traducirError(e).message })); return; }
    lista.replaceChildren(...(l.length ? l.map((n) => el("li", {},
      el("div", { class: "ps-nota-cabeza" }, el("b", { text: new Date(n.creada_en).toLocaleString("es-CO", { timeZone: "America/Bogota", dateStyle: "medium", timeStyle: "short" }) }),
        el("small", { text: n.autora === estado.perfil.user_id ? "Usted" : nombreAsesor(n.autora) }),
        n.autora === estado.perfil.user_id && el("button", { type: "button", class: "enlace", "aria-label": "Borrar anotación", onclick: async () => {
          try { await estado.almacen.borrarAnotacion(n.id); pintar(); } catch (e) { avisar(traducirError(e).message, "error"); }
        } }, icono("basura", "ic ic-chico"))),
      el("p", { text: n.texto }))) : [el("li", { class: "nota", text: "Sin anotaciones todavía." })]));
  };
  guardar.addEventListener("click", async () => {
    const texto = caja.value.trim();
    if (!texto) { caja.focus(); return; }
    try { await conEspera(guardar, "Guardando…", () => estado.almacen.crearAnotacion(a.id, texto)); caja.value = ""; pintar(); avisar("Anotación guardada.", "exito", { duracion: 2000 }); }
    catch (e) { avisar(traducirError(e).message, "error"); }
  });
  panel.replaceChildren(el("section", { class: "tarjeta" }, el("div", { class: "tarjeta-cabeza" }, el("h2", {}, icono("editar"), "Anotaciones")),
    el("p", { class: "nota", text: "Solo las ve la psicóloga vocacional." }), caja, el("div", { class: "acciones" }, guardar), lista));
  pintar();
}

function pestanaDatos(panel, a) {
  const filas = [["Programa", PROGRAMAS[a.programa]], ["Periodo", a.periodo], ["ICFES", a.icfes ?? "—"], ["Estrato", a.estrato ?? "—"],
    ["Localidad o municipio", a.ubicacion || "—"], ["Distancia por vía", km(a.distancia_vial_km)], ["Colegio", a.colegio || "—"],
    ["¿Cómo conoció la Universidad?", a.canal ? CANALES[a.canal] : "—"],
    ["Becas solicitadas", [a.solicita_mi_vocacion && "Mi Vocación", a.solicita_saber11 && "Saber 11"].filter(Boolean).join(" · ") || "Ninguna"],
    ["Beca que se aplica", NOMBRE_BECA[a.beca || "NINGUNA"]],
    ["Propensión a matricularse", a.propension ? `${PROPENSION[a.propension]} (${pct(a.probabilidad_matricula)})` : "Sin predecir"],
    ["Asesor", nombreAsesor(a.asesor_id)], ["Registrado", hace(a.creado_en)]];
  panel.replaceChildren(el("section", { class: "tarjeta" }, el("div", { class: "tarjeta-cabeza" }, el("h2", {}, icono("usuario"), "Información general")),
    el("dl", { class: "resumen" }, filas.flatMap(([k, x]) => [el("dt", { text: k }), el("dd", { text: String(x ?? "—") })]))));
}

// ---------------------------------------------------------------------------- arranque
export function iniciarPsicologia() {
  $("barra-agendar")?.addEventListener("click", () => formularioCita({ fecha: P.dia || HOY() }));
}
export const estadoPsicologia = P;
