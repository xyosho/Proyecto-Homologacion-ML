// Enlaces de encuesta: el asesor crea un enlace y lo envía al aspirante (WhatsApp, correo o compartir del celular).
// El aspirante llena sus datos en /encuesta/<código> sin iniciar sesión y aparece en la lista del asesor como NUEVO.
// El código lo genera Supabase; RLS: cada asesor ve y desactiva sus enlaces, el jefe y el administrador todos.
import { $, el, icono, fecha, hace, avisar, conEspera, animarEntrada, PROGRAMAS } from "./ui.js";
import { estado, esJefe, nombreAsesor, urlEncuesta, motivoEnlace, traducirError } from "./datos.js";
import { bloqueQR, botonQR, nombreArchivoQR } from "./qr.js";

const ESTADO_ENLACE = { activo: ["Recibe respuestas", "ACTIVO"], vencido: ["Vencido", "VENCIDO"], usado: ["Ya se usó", "USADO"],
  lleno: ["Completo", "USADO"], inactivo: ["Desactivado", "INACTIVO"] };
let cargados = false, recarga = null;

export async function cargarEnlaces() {
  try { estado.enlaces = await estado.almacen.listarEnlaces(); cargados = true; $("e-lista-error").hidden = true; }
  catch (e) { $("e-lista-error").textContent = traducirError(e).message; $("e-lista-error").hidden = false; }
}

const mensaje = (url) => `Hola, soy ${(estado.perfil?.nombre || "").trim().split(/\s+/)[0] || "tu asesor"}, de Admisiones de Unicervantes. `
  + `Llena esta encuesta (3 minutos): ahí ves tu beca, tu precio y tu ruta al campus. ${url}`;
async function copiar(texto, campo) {
  try { await navigator.clipboard.writeText(texto); }
  catch { campo?.select(); document.execCommand?.("copy"); }                // navegadores sin acceso al portapapeles
  avisar("Enlace copiado. Péguelo en WhatsApp, correo o mensaje.", "exito", { duracion: 2500 });
}
// Las dos formas de compartir un enlace listo: el enlace (copiar, WhatsApp, correo) y su código QR.
// conQR: el enlace recién creado muestra el QR de una vez; en la lista sale con el botón «Código QR».
function botonesCompartir(url, { nombre = null, conQR = false } = {}) {
  const campo = el("input", { type: "text", readonly: true, value: url, "aria-label": "Enlace de la encuesta", onfocus: (ev) => ev.target.select() });
  const qr = { titulo: nombre ? `Encuesta de admisiones · ${nombre}` : "Encuesta de admisiones · Unicervantes", archivo: nombreArchivoQR("qr-encuesta", nombre) };
  return [
    el("div", { class: "con-botones" }, campo,
      el("button", { type: "button", class: "icono-boton", title: "Copiar enlace", "aria-label": "Copiar enlace", onclick: () => copiar(url, campo) }, icono("copiar"))),
    el("div", { class: "acciones enlace-acciones" },
      el("a", { class: "boton secundario", href: `https://wa.me/?text=${encodeURIComponent(mensaje(url))}`, target: "_blank", rel: "noopener noreferrer" }, icono("mensaje"), "WhatsApp"),
      el("a", { class: "boton discreto", href: `mailto:?subject=${encodeURIComponent("Encuesta de admisiones · Unicervantes")}&body=${encodeURIComponent(mensaje(url))}` }, icono("correo"), "Correo"),
      navigator.share && el("button", { type: "button", class: "discreto", onclick: () => navigator.share({ title: "Encuesta de admisiones · Unicervantes", text: mensaje(url) }).catch(() => {}) },
        icono("compartir"), "Compartir"),
      !conQR && botonQR(url, "li.enlace", qr),
      el("a", { class: "boton discreto", href: url, target: "_blank", rel: "noopener" }, icono("sube"), "Ver encuesta")),
    conQR ? bloqueQR(url, qr) : null,
  ];
}

function filaEnlace(e) {
  const motivo = motivoEnlace(e) || "activo", [textoEstado, tono] = ESTADO_ENLACE[motivo], url = urlEncuesta(e.token);
  const respuestas = e.respuestas === 1 ? "1 respuesta" : `${e.respuestas} respuestas`;
  return el("li", { class: "enlace", dataset: { estado: motivo, id: e.id } },
    el("div", { class: "enlace-cabeza" },
      el("b", { text: e.nombre || `Enlace del ${fecha(e.creado_en).split(",")[0]}` }),
      el("span", { class: "chip chico", dataset: { tono }, text: textoEstado }),
      e.un_solo_uso && el("span", { class: "chip chico", dataset: { tono: "" }, text: "Un solo aspirante" }),
      e.programa && el("span", { class: "chip chico", dataset: { tono: "" }, text: e.programa })),
    el("small", { class: "texto-suave" }, `${respuestas}${e.ultima_respuesta ? ` · la última ${hace(e.ultima_respuesta)}` : ""} · `,
      motivo === "vencido" ? `venció ${hace(e.vence_en)}` : `vence el ${fecha(e.vence_en).split(",")[0]}`,
      esJefe() && e.asesor_id !== estado.perfil.user_id ? ` · de ${nombreAsesor(e.asesor_id)}` : ""),
    motivo === "activo" ? botonesCompartir(url, { nombre: e.nombre }) : null,
    el("div", { class: "acciones" },
      (motivo === "activo" || motivo === "inactivo") && el("button", { type: "button", class: motivo === "activo" ? "discreto peligro" : "secundario",
        onclick: (ev) => cambiarActivo(e, motivo !== "activo", ev.currentTarget) }, icono(motivo === "activo" ? "x" : "check"), motivo === "activo" ? "Desactivar" : "Activar de nuevo")));
}

export async function pintarEncuestas() {
  $("e-titulo-lista").lastChild.textContent = esJefe() ? "Enlaces del equipo" : "Mis enlaces";
  if (!cargados) { $("e-lista").replaceChildren(el("li", { class: "nota", text: "Cargando enlaces…" })); await cargarEnlaces(); }
  const l = estado.enlaces;
  $("e-conteo").textContent = l.length || "";
  $("e-lista").replaceChildren(...(l.length ? l.map(filaEnlace)
    : [el("li", { class: "vacio-grande" }, icono("enlace", "ic vacio-icono"), el("p", { text: "Todavía no tiene enlaces. Cree uno y envíelo a un aspirante." }))]));
}

async function cambiarActivo(e, activo, boton) {
  try {
    const nuevo = await conEspera(boton, activo ? "Activando…" : "Desactivando…", () => estado.almacen.actualizarEnlace(e.id, { activo }));
    estado.enlaces = estado.enlaces.map((x) => (x.id === e.id ? nuevo : x));
    pintarEncuestas();
    avisar(activo ? "El enlace recibe respuestas otra vez." : "Enlace desactivado: ya no recibe respuestas.", "info", { duracion: 2500 });
  } catch (err) { avisar(traducirError(err).message, "error"); }
}

async function crearEnlace(ev) {
  ev.preventDefault();
  $("e-error").hidden = true;
  const dias = Number($("e-vence").value);
  const datos = { nombre: $("e-nombre").value.trim() || null, programa: $("e-programa").value || null, un_solo_uso: $("e-un-uso").checked,
    vence_en: new Date(Date.now() + dias * 864e5).toISOString() };
  try {
    const e = await conEspera($("e-crear"), "Creando…", () => estado.almacen.crearEnlace(datos));
    estado.enlaces = [e, ...estado.enlaces.filter((x) => x.id !== e.id)];
    $("form-enlace").reset(); $("e-vence").value = "30";
    $("e-nuevo").replaceChildren(el("p", { class: "etiqueta" }, icono("check"), " Enlace listo: envíe el enlace o muestre el código QR"),
      ...botonesCompartir(urlEncuesta(e.token), { nombre: e.nombre, conQR: true }));
    $("e-nuevo").hidden = false; animarEntrada($("e-nuevo"));
    $("e-nuevo").querySelector("input").focus();
    pintarEncuestas();
  } catch (err) { $("e-error").textContent = traducirError(err).message; $("e-error").hidden = false; }
}

export function iniciarEncuestas() {
  $("form-enlace").addEventListener("submit", crearEnlace);
  // Tiempo real: una respuesta nueva cambia el conteo del enlace (o llega un enlace creado en otra sesión)
  document.addEventListener("enlaces", () => {
    clearTimeout(recarga);
    recarga = setTimeout(async () => { await cargarEnlaces(); if (!$("vista-encuestas").hidden) pintarEncuestas(); }, 400);
  });
}
