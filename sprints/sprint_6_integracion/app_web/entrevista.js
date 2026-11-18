// Entrevista de admisión del aspirante (enlace personal /entrevista/<código>, sin iniciar sesión). Responde las secciones
// 1 a 7 del formulario institucional y las envía con entrevista_enviar (Supabase), que valida el enlace y cada respuesta.
// Le llegan a la psicóloga vocacional. La salud mental no se pregunta aquí (dato sensible: solo con la psicóloga).
// Mientras escribe, el borrador queda en este navegador para no perderlo si se cierra la página.
import { $, el, avisar, conEspera, animarEntrada } from "./ui.js";
import { SECCIONES, CON_QUIEN_VIVE } from "./vocacional.js";
import { demoEntrevistaInfo, demoEntrevistaEnviar } from "./datos.js";

const MOTIVOS = {
  "no-existe": ["Este enlace no es válido", "Revisa que el enlace esté completo o pide a tu asesor de admisiones uno nuevo."],
  vencido: ["Este enlace ya venció", "Pide a tu asesor de admisiones un enlace nuevo."],
  usado: ["Ya enviaste tu entrevista", "Recibimos tus respuestas con este enlace. ¡Gracias! La psicóloga vocacional te contactará."],
  cerrada: ["Tu entrevista ya se realizó", "La psicóloga vocacional ya hizo tu entrevista. Si necesitas algo, escribe a tu asesor."],
  inactivo: ["Este enlace ya no está activo", "Pide a tu asesor de admisiones un enlace nuevo."],
  conexion: ["No pudimos abrir la entrevista", "Revisa tu conexión a internet e intenta de nuevo en un momento."],
};
const local = ["localhost", "127.0.0.1", "[::1]"].includes(location.hostname);
const consulta = new URLSearchParams(location.search);
const demo = local && consulta.has("demo");
const token = (location.pathname.match(/\/entrevista\/([0-9a-f]{32})\/?$/) || [])[1] || consulta.get("t") || "";
const BORRADOR = `unicervantes-entrevista-${token}`;
let api = null, enviada = false, sucio = false;

async function rpc(nombre, cuerpo) {
  let r;
  try {
    r = await fetch(`${api.url}/rest/v1/rpc/${nombre}`, { method: "POST", headers: { apikey: api.key, "Content-Type": "application/json" }, body: JSON.stringify(cuerpo) });
  } catch { throw Object.assign(new Error("Sin conexión. Revisa tu internet e intenta de nuevo."), { tipo: "conexion" }); }
  const datos = await r.json().catch(() => null);
  if (!r.ok) throw Object.assign(new Error(datos?.message || "No se pudo enviar la entrevista. Intenta de nuevo."), { tipo: datos?.hint || "general" });
  return datos;
}
const pedirInfo = () => (demo ? Promise.resolve(demoEntrevistaInfo(token)) : rpc("entrevista_info", { p_token: token }));
const enviarDatos = (d) => (demo ? Promise.resolve().then(() => demoEntrevistaEnviar(token, d)) : rpc("entrevista_enviar", { p_token: token, p_datos: d }));

// ---------------------------------------------------------------------------- formulario
function pintarSecciones() {
  let n = 3;
  $("ent-secciones").replaceChildren(...SECCIONES.map((s) => el("section", { class: "tarjeta ent-seccion" },
    el("h2", {}, el("span", { class: "ent-num", text: String(n++) }), s.titulo),
    s.preguntas.flatMap(([clave, texto]) => [
      el("div", { class: "campo", id: `c-${clave}` }, el("label", { for: clave, text: texto }),
        el("textarea", { id: clave, rows: 3, maxlength: 2000, required: true, "data-respuesta": "" }),
        el("span", { class: "mensaje-error", text: "Responde esta pregunta." })),
      clave === "h1" && el("fieldset", { class: "campo ent-vive" }, el("legend", { class: "etiqueta", text: "¿Con quién vive?" }),
        el("div", { class: "opciones-chip" }, CON_QUIEN_VIVE.map((v) => el("label", {}, el("input", { type: "checkbox", name: "vive", value: v }), el("span", { text: v })))),
        el("input", { id: "parentesco", maxlength: 80, placeholder: "Parentesco (si eligió Otro)", "aria-label": "Parentesco" })),
    ]))));
}
const valor = (id) => $(id).value.trim();
function leer() {
  const respuestas = {};
  SECCIONES.forEach((s) => s.preguntas.forEach(([k]) => { respuestas[k] = valor(k); }));
  respuestas.h2 = [...document.querySelectorAll("input[name=vive]:checked")].map((x) => x.value);
  respuestas.h2_parentesco = valor("parentesco");
  return { datos: { nombre: valor("nombre").replace(/\s+/g, " "), celular: valor("celular").replace(/\D/g, ""), correo: valor("correo").toLowerCase(),
    tipo_documento: valor("tipo-documento"), numero_documento: valor("numero-documento") }, programa: valor("programa"), sede: valor("sede"),
    respuestas, autoriza_datos: $("autoriza").checked, sitio_web: valor("sitio_web") };
}
function validar(d) {
  const marcar = (id, mal) => { if (mal) $(id).dataset.error = ""; else delete $(id).dataset.error; return mal ? id : null; };
  const errores = [
    marcar("c-nombre", d.datos.nombre.length < 3),
    marcar("c-celular", !/^3\d{9}$/.test(d.datos.celular)),
    marcar("c-documento", !d.datos.tipo_documento || !/^[0-9A-Za-z]{4,15}$/.test(d.datos.numero_documento)),
    marcar("c-programa", !d.programa),
    ...SECCIONES.flatMap((s) => s.preguntas.map(([k]) => marcar(`c-${k}`, d.respuestas[k].length < 2))),
  ].filter(Boolean);
  $("autoriza-error").hidden = d.autoriza_datos;
  if (!d.autoriza_datos) errores.push("c-autoriza");
  return errores;
}
function guardarBorrador() {
  try { const { autoriza_datos: _a, sitio_web: _s, ...b } = leer(); localStorage.setItem(BORRADOR, JSON.stringify(b)); $("ent-guardado").textContent = "Borrador guardado en este navegador."; }
  catch { /* sin almacenamiento: no pasa nada */ }
}
function cargarBorrador(info) {
  let b = null;
  try { b = JSON.parse(localStorage.getItem(BORRADOR)); } catch { b = null; }
  if (info.programa) $("programa").value = info.programa;
  if (!b) return;
  for (const [k, id] of [["nombre", "nombre"], ["celular", "celular"], ["correo", "correo"], ["tipo_documento", "tipo-documento"], ["numero_documento", "numero-documento"]])
    if (b.datos?.[k]) $(id).value = b.datos[k];
  if (b.programa) $("programa").value = b.programa;
  if (b.sede) $("sede").value = b.sede;
  Object.entries(b.respuestas || {}).forEach(([k, v]) => { if (typeof v === "string" && $(k)) $(k).value = v; });
  (b.respuestas?.h2 || []).forEach((v) => { const c = document.querySelector(`input[name=vive][value="${v}"]`); if (c) c.checked = true; });
  if (b.respuestas?.h2_parentesco) $("parentesco").value = b.respuestas.h2_parentesco;
  avisar("Recuperamos el borrador que habías empezado.", "info", { duracion: 3000 });
}
async function enviar(ev) {
  ev.preventDefault();
  const d = leer(), errores = validar(d);
  if (errores.length) {
    const c = $(errores[0]); c.scrollIntoView({ block: "center", behavior: "smooth" }); (c.querySelector("input, textarea, select") || c).focus({ preventScroll: true });
    avisar("Revisa los campos marcados.", "error", { duracion: 2500 }); return;
  }
  $("ent-error").hidden = true;
  try {
    const r = await conEspera($("ent-enviar"), "Enviando…", () => enviarDatos(d));
    enviada = true;
    try { localStorage.removeItem(BORRADOR); } catch { /* nada */ }
    $("ent-contenido").hidden = true; $("ent-gracias").hidden = false;
    if (r?.asesor) $("ent-gracias-texto").textContent = `La psicóloga vocacional de Unicervantes revisará tus respuestas y te contactará para agendar la entrevista. Si tienes dudas, escribe a ${r.asesor}, tu asesor.`;
    animarEntrada($("ent-gracias")); window.scrollTo(0, 0);
  } catch (e) {
    if (["no-existe", "vencido", "usado", "cerrada", "inactivo", "enlace"].includes(e.tipo)) { mostrarInvalido(e.tipo === "enlace" ? "inactivo" : e.tipo); return; }
    $("ent-error").textContent = e.message; $("ent-error").hidden = false;
  }
}
function mostrarInvalido(motivo) {
  const [titulo, texto] = MOTIVOS[motivo] || MOTIVOS["no-existe"];
  $("ent-cargando").hidden = true; $("ent-contenido").hidden = true; $("ent-invalido").hidden = false;
  $("ent-invalido-titulo").textContent = titulo; $("ent-invalido-texto").textContent = texto;
  document.title = `${titulo} · Unicervantes`;
}

async function iniciar() {
  if (!/^[0-9a-f]{32}$/.test(token)) { mostrarInvalido("no-existe"); return; }
  let info = null;
  try {
    const config = demo ? {} : await import("./config.js");
    api = { url: config.SUPABASE_URL, key: config.SUPABASE_KEY };
    if (!demo && (!api.url || !api.key)) throw new Error("sin configuración");
    info = await pedirInfo();
  } catch (e) { mostrarInvalido(e.tipo === "conexion" || !info ? "conexion" : "no-existe"); return; }
  if (!info.valida) { mostrarInvalido(info.motivo); return; }
  pintarSecciones();
  $("ent-asesor").textContent = info.asesor || "de admisiones";
  if (info.nombre) $("ent-titulo").textContent = `Hola, ${info.nombre}: cuéntanos sobre ti`;
  cargarBorrador(info);
  let temporizador = null;
  $("ent-form").addEventListener("input", (ev) => {
    sucio = true;
    const c = ev.target.closest("[data-error]"); if (c) delete c.dataset.error;
    clearTimeout(temporizador); temporizador = setTimeout(guardarBorrador, 800);
  });
  $("ent-form").addEventListener("submit", enviar);
  window.addEventListener("beforeunload", (ev) => { if (sucio && !enviada) { guardarBorrador(); ev.preventDefault(); ev.returnValue = ""; } });
  $("ent-cargando").hidden = true; $("ent-contenido").hidden = false;
  animarEntrada($("ent-contenido"));
  if (demo) avisar("Modo demostración: la respuesta se guarda en este navegador.", "info", { duracion: 3500 });
}

iniciar();
