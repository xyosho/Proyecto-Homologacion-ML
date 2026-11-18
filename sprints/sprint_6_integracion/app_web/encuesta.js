// Encuesta pública del aspirante: se abre con el enlace que le envía su asesor (/encuesta/<código>), sin iniciar
// sesión. Llena sus datos por pasos, ve en vivo su beca con el precio y la ruta al campus, y al enviar queda como
// aspirante NUEVO de ese asesor. No lee nada de la base: solo llama a encuesta_info y encuesta_enviar (Supabase),
// que validan el enlace y cada dato. La predicción de matrícula la hace después la app del asesor; aquí no se muestra.
import { $, el, icono, cop, pct, avisar, conEspera, animarEntrada, animarNumero, CANALES, DETALLE_CANAL, NOMBRE_BECA, PROGRAMAS,
  MEDIOS, GENERO, REGIMEN, TIPO, LETRAS, armarDireccion } from "./ui.js";
import { crearModelo } from "./modelo.js";
import { estado, elegirBeca, ubicacionDe, ubicarDireccion, demoEncuestaInfo, demoEncuestaEnviar } from "./datos.js";
import { pintarRuta } from "./mapa.js";

const PASOS = [
  { titulo: "Tus datos", ayuda: "Quién eres y qué quieres estudiar" },
  { titulo: "Contacto", ayuda: "Cómo te contacta tu asesor" },
  { titulo: "Saber 11 y becas", ayuda: "Tu puntaje define tu beca" },
  { titulo: "Dónde vives", ayuda: "Para calcular tu ruta al campus" },
  { titulo: "Enviar", ayuda: "Revisa tus datos y envíalos" },
];
const MOTIVOS = {
  "no-existe": ["Este enlace no es válido", "Revisa que el enlace esté completo o pide a tu asesor de admisiones uno nuevo."],
  vencido: ["Este enlace ya venció", "Pide a tu asesor de admisiones un enlace nuevo."],
  usado: ["Este enlace ya se usó", "Era para una sola persona. Pide a tu asesor de admisiones un enlace nuevo."],
  lleno: ["Este enlace ya recibió todas sus respuestas", "Pide a tu asesor de admisiones un enlace nuevo."],
  inactivo: ["Este enlace ya no está activo", "Pide a tu asesor de admisiones un enlace nuevo."],
  conexion: ["No pudimos abrir la encuesta", "Revisa tu conexión a internet e intenta de nuevo en un momento."],
};

const local = ["localhost", "127.0.0.1", "[::1]"].includes(location.hostname);
const consulta = new URLSearchParams(location.search);
const demo = local && consulta.has("demo");
const token = (location.pathname.match(/\/encuesta\/([0-9a-f]{32})\/?$/) || [])[1] || consulta.get("t") || "";
let api = null, info = null, paso = 0, saber11Tocado = false, sucio = false, enviada = false;
const geo = { estado: "inactivo", clave: "", lat: null, lon: null, localidad: null };
let temporizador = null, temporizadorMapa = null;

const valor = (id) => $(id).value.trim();
const numero = (id) => { const v = valor(id).replace(",", "."); return v === "" ? null : Number(v); };
const opcion = (id, vacio = "Sin dato") => { const s = $(id); return s.value ? s.options[s.selectedIndex].text : vacio; };

// ---------------------------------------------------------------------------- Supabase (solo dos funciones, sin sesión)
async function rpc(nombre, cuerpo) {
  let r;
  try {
    r = await fetch(`${api.url}/rest/v1/rpc/${nombre}`, { method: "POST", headers: { apikey: api.key, "Content-Type": "application/json" }, body: JSON.stringify(cuerpo) });
  } catch { throw Object.assign(new Error("Sin conexión. Revisa tu internet e intenta de nuevo."), { tipo: "conexion" }); }
  const datos = await r.json().catch(() => null);
  if (!r.ok) throw Object.assign(new Error(datos?.message || "No se pudo enviar la encuesta. Intenta de nuevo."), { tipo: datos?.hint || "general" });
  return datos;
}
const pedirInfo = () => (demo ? Promise.resolve(demoEncuestaInfo(token)) : rpc("encuesta_info", { p_token: token }));
const enviarDatos = (datos) => (demo ? Promise.resolve().then(() => demoEncuestaEnviar(token, datos)) : rpc("encuesta_enviar", { p_token: token, p_datos: datos }));

// ---------------------------------------------------------------------------- dirección y ubicación
function direccionTexto() {
  if ($("dir-libre-activa").checked) return valor("dir-libre");
  return armarDireccion({ tipo: valor("dir-tipo"), numero: valor("dir-numero"), letra: valor("dir-letra"), bis: valor("dir-bis"),
    cuadrante: valor("dir-cuadrante"), cruce: valor("dir-cruce"), letraCruce: valor("dir-letra-cruce"), placa: valor("dir-placa") });
}
const ciudad = () => valor("ciudad");
const ubicacionElegida = () => (ciudad() === "BOGOTA" ? valor("localidad") : ciudad());

function programarUbicacion() {
  clearTimeout(temporizador);
  const d = direccionTexto();
  $("dir-vista").textContent = d || "Completa tipo de vía, número y placa";
  $("dir-vista").dataset.vacia = d ? "no" : "si";
  if (ciudad() !== "BOGOTA" || !d) {
    Object.assign(geo, { estado: "inactivo", clave: "", lat: null, lon: null, localidad: null });
    pintarEstadoDireccion(); programarMapa(); return;
  }
  if (geo.clave === d && geo.estado !== "error") { programarMapa(); return; }
  temporizador = setTimeout(() => ubicar(d), 700);
}
async function ubicar(d) {
  Object.assign(geo, { estado: "buscando", clave: d });
  pintarEstadoDireccion();
  try {
    const g = await ubicarDireccion(d);
    if (geo.clave !== d) return;                                    // siguió escribiendo
    Object.assign(geo, { estado: "ok", lat: g.lat, lon: g.lon, localidad: g.localidad });
    if (g.localidad && valor("localidad") !== g.localidad) { $("localidad").value = g.localidad; $("c-localidad").dataset.auto = "si"; }
  } catch {
    if (geo.clave !== d) return;
    Object.assign(geo, { estado: "error", lat: null, lon: null, localidad: null });
  }
  pintarEstadoDireccion(); actualizarFoes(); programarMapa();
}
function pintarEstadoDireccion() {
  const caja = $("dir-estado");
  const textos = { buscando: "Ubicando tu dirección…", ok: `Encontramos tu dirección${geo.localidad ? ` en ${geo.localidad}` : ""}.`,
    error: "No encontramos esa placa; usaremos el centro de tu localidad. Puedes seguir." };
  caja.hidden = !textos[geo.estado];
  caja.dataset.tono = geo.estado;
  caja.replaceChildren(geo.estado === "buscando" ? el("span", { class: "giro", "aria-hidden": "true" }) : icono(geo.estado === "ok" ? "check" : "info"),
    el("span", { text: textos[geo.estado] || "" }));
}
function actualizarFoes() {
  const u = ubicacionDe(ubicacionElegida());
  const foes = Boolean(u && estado.modelo.reglas.fondos_municipales.includes(u.ubicacion_id));
  $("c-foes").hidden = !foes; if (!foes) $("foes").checked = false;
}

// ---------------------------------------------------------------------------- mapa de la ruta (mapa.js, el mismo de la app)
function programarMapa() {
  clearTimeout(temporizadorMapa);
  temporizadorMapa = setTimeout(() => {
    const ubic = ubicacionElegida(), u = ubicacionDe(ubic);
    if (!u) {
      $("ruta-origen").textContent = "Elige dónde vives para ver la ruta desde tu casa hasta el campus.";
      return;
    }
    const conGeo = geo.estado === "ok" && ciudad() === "BOGOTA";
    pintarRuta({ id: "encuesta", ubicacion: ubic, lat: conGeo ? geo.lat : null, lon: conGeo ? geo.lon : null, ubicada_con: conGeo ? "CATASTRO" : "CENTRO",
      distancia_ruta_km: null }).then(() => {
      $("ruta-origen").textContent = conGeo ? "Desde tu dirección hasta el campus (Calle 209, vía Arrayanes)."
        : `Desde el centro de ${u.nombre} (aproximado) hasta el campus (Calle 209, vía Arrayanes).`;
    });
  }, 400);
}

// Medio de contacto: sin celular no se ofrece WhatsApp ni llamada; sin correo, no se ofrece correo
function actualizarMedio() {
  const tel = valor("telefono") !== "", correo = valor("correo") !== "";
  const radios = [...document.querySelectorAll('input[name="medio"]')];
  radios.forEach((r) => { r.disabled = r.value === "CORREO" ? tel && !correo : correo && !tel; });
  const elegido = radios.find((r) => r.checked);
  if (!elegido || elegido.disabled) (radios.find((r) => !r.disabled) || radios[0]).checked = true;
}

// ---------------------------------------------------------------------------- beca y precio en vivo
function notaBeca(beca, quiereVocacion) {
  if (beca === "SABER_11") return "Con tu puntaje aplicas a la beca Saber 11: 35% en toda la carrera, que conservas con promedio de 4,0 o más.";
  if (beca === "MI_VOCACION") return "Beca Mi Vocación: 30% en toda la carrera. Se confirma en la entrevista vocacional con tu asesor.";
  if (quiereVocacion) return "Escribe tu puntaje del Saber 11 para ver si también aplicas a la beca Saber 11.";
  return "Sin beca pagas la tarifa plena. Marca Mi Vocación para aplicar a una beca.";
}
function actualizarBeca() {
  const R = estado.modelo.reglas, icfes = numero("icfes");
  const cb = $("beca-saber11"), est = $("estado-saber11");
  const valido = icfes !== null && Number.isInteger(icfes) && icfes >= 0 && icfes <= 500;
  const cumple = valido && icfes >= R.umbral_icfes;
  cb.disabled = !cumple;
  if (!cumple) { cb.checked = false; saber11Tocado = false; } else if (!saber11Tocado) cb.checked = true;
  est.textContent = !valido ? "Escribe tu puntaje ICFES" : cumple ? `¡Cumples! Tienes ${R.umbral_icfes} o más` : `Te faltan ${R.umbral_icfes - icfes} puntos`;
  est.dataset.tono = cumple ? "ok" : "no";
  const mv = $("beca-mivocacion").checked;
  $("estado-mivocacion").textContent = mv ? "Se confirma en la entrevista con tu asesor" : "No la pediste";
  $("estado-mivocacion").dataset.tono = mv ? "ok" : "no";
  // Mi Vocación: se supone que aprueba la entrevista (puntaje mínimo); el asesor la confirma
  const beca = elegirBeca(valido ? icfes : null, cb.checked, mv, mv ? R.puntaje_vocacional_minimo : null);
  const p = estado.modelo.precios(valor("programa"), valor("periodo"), beca);
  $("b-nombre").textContent = NOMBRE_BECA[beca]; $("b-nombre").dataset.tono = beca;
  animarNumero($("b-pct"), p.pct_beca, (v) => pct(v));
  $("b-despues").textContent = beca === "NINGUNA" ? "sin beca" : "en toda la carrera";
  $("b-tarifa").textContent = cop(p.bruto);
  $("b-neto").textContent = cop(p.neto);
  $("b-siguientes").textContent = `${pct(p.pct_siguientes)} · ${cop(p.neto_siguientes)}`;
  $("b-nota").textContent = notaBeca(beca, mv && !valido);
  $("c-detalle-canal").hidden = !valor("canal") || !DETALLE_CANAL[valor("canal")];
  $("canal-detalle").placeholder = (DETALLE_CANAL[valor("canal")] || "").replace("lo refirió", "te refirió");
  $("c-localidad").hidden = ciudad() !== "BOGOTA";
  actualizarFoes(); actualizarMedio();
  return beca;
}

// ---------------------------------------------------------------------------- validación por paso
function marcar(id, hay) { const c = $(id); if (hay) c.dataset.error = ""; else delete c.dataset.error; return hay ? id : null; }
const VALIDAR = [
  () => [marcar("c-nombre", valor("nombre").replace(/\s+/g, " ").length < 2)],
  () => {
    const tel = valor("telefono"), correo = valor("correo");
    const telMalo = tel !== "" && !/^[0-9 +()-]{7,20}$/.test(tel), correoMalo = correo !== "" && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(correo);
    return [marcar("c-telefono", telMalo || (!tel && !correo)), marcar("c-correo", correoMalo)];
  },
  () => {
    const icfes = numero("icfes");
    return [marcar("c-icfes", icfes === null || !Number.isInteger(icfes) || icfes < 0 || icfes > 500),
      marcar("c-estrato", valor("estrato") === "")];
  },
  () => {
    const libre = $("dir-libre-activa").checked, d = direccionTexto();
    return [marcar("c-ciudad", ciudad() === ""), marcar("c-localidad", ciudad() === "BOGOTA" && valor("localidad") === ""),
      marcar("c-direccion", d.length < 5 || (!libre && !/^\d+$/.test(valor("dir-placa"))))];
  },
  () => [marcar("c-autoriza", !$("autoriza").checked)],
];
const erroresDe = (i) => VALIDAR[i]().filter(Boolean);
function enfocarError(id) {
  const c = $(id);
  c.classList.remove("sacudir"); void c.offsetWidth; c.classList.add("sacudir");
  (c.querySelector("input, select") || c).focus();
}

// ---------------------------------------------------------------------------- pasos
function irA(i, { enfocar = true } = {}) {
  paso = Math.max(0, Math.min(PASOS.length - 1, i));
  document.querySelectorAll("#enc-form .paso").forEach((f, j) => { f.hidden = j !== paso; if (j === paso) animarEntrada(f); });
  document.querySelectorAll("#enc-pasos li").forEach((li, j) => {
    li.dataset.estado = j < paso ? "hecho" : j === paso ? "actual" : "pendiente";
    const b = li.querySelector("button");
    if (j === paso) b.setAttribute("aria-current", "step"); else b.removeAttribute("aria-current");
  });
  $("enc-progreso").style.width = `${((paso + 1) / PASOS.length) * 100}%`;
  $("paso-texto").textContent = `Paso ${paso + 1} de ${PASOS.length} · ${PASOS[paso].ayuda}`;
  $("paso-anterior").hidden = paso === 0;
  $("paso-siguiente").hidden = paso === PASOS.length - 1;
  $("enviar").hidden = paso !== PASOS.length - 1;
  if (paso === PASOS.length - 1) pintarRevision();
  if (paso === 3) programarMapa();
  if (enfocar) {
    const f = document.querySelector(`#enc-form .paso[data-paso="${paso}"]`);
    (f.querySelector("input:not([type=hidden]):not(:disabled):not([type=radio]), select") || f).focus({ preventScroll: true });
    $("enc-pasos").scrollIntoView({ block: "start", behavior: "smooth" });
  }
}
function siguiente() {
  const e = erroresDe(paso);
  if (e.length) { enfocarError(e[0]); return; }
  irA(paso + 1);
}

// ---------------------------------------------------------------------------- lectura y revisión
function leerFormulario() {
  const R = estado.modelo.reglas, icfes = numero("icfes"), ubic = ubicacionElegida();
  const conGeo = geo.estado === "ok" && ciudad() === "BOGOTA";
  const texto = (id) => valor(id) || null, entero = (id) => (valor(id) === "" ? null : Number(valor(id)));
  return {
    nombre: valor("nombre").replace(/\s+/g, " "), telefono: texto("telefono"), correo: texto("correo") && valor("correo").toLowerCase(),
    medio_contacto: document.querySelector('input[name="medio"]:checked')?.value || null, genero: texto("genero"), edad: entero("edad"),
    autoriza_datos: $("autoriza").checked, programa: valor("programa"), periodo: valor("periodo"),
    canal: texto("canal"), canal_detalle: $("c-detalle-canal").hidden ? null : texto("canal-detalle"),
    icfes, anios_desde_saber11: entero("anios"), estrato: Number(valor("estrato")),
    solicita_mi_vocacion: $("beca-mivocacion").checked, solicita_saber11: $("beca-saber11").checked && icfes >= R.umbral_icfes,
    direccion: direccionTexto(), direccion_complemento: $("dir-libre-activa").checked ? null : texto("dir-complemento"), ubicacion: ubic,
    lat: conGeo ? geo.lat : null, lon: conGeo ? geo.lon : null,
    apoyo_foes: $("foes").checked, regimen_salud: texto("regimen"), colegio: texto("colegio"), tipo_colegio: texto("tipo-colegio"),
    sitio_web: $("sitio-web").value,                                  // campo trampa: vacío para las personas
  };
}
function pintarRevision() {
  const r = leerFormulario(), beca = actualizarBeca();
  const grupos = [
    [0, "Tus datos", [["Nombre", r.nombre], ["Programa", PROGRAMAS[r.programa]], ["Empiezas en", r.periodo], ["Edad", opcion("edad", "Sin dato")], ["Género", GENERO[r.genero] || "Sin dato"]]],
    [1, "Contacto", [["Celular", r.telefono || "Sin dato"], ["Correo", r.correo || "Sin dato"], ["Prefieres", MEDIOS[r.medio_contacto] || "Sin preferencia"],
      ["Cómo conociste la Universidad", [r.canal ? CANALES[r.canal] : "Sin dato", r.canal_detalle].filter(Boolean).join(" · ")]]],
    [2, "Saber 11 y becas", [["Puntaje ICFES", r.icfes], ["Estrato", r.estrato], ["Colegio", [r.colegio, TIPO[r.tipo_colegio]].filter(Boolean).join(" · ") || "Sin dato"],
      ["Tu beca", NOMBRE_BECA[beca]]]],
    [3, "Dónde vives", [["Dirección", [r.direccion, r.direccion_complemento].filter(Boolean).join(", ")], ["Ubicación", r.ubicacion],
      ["Régimen de salud", REGIMEN[r.regimen_salud] || "Sin dato"], r.apoyo_foes && ["Fondo municipal", "Solicitarás el FOES/FOEST"]]],
  ];
  $("revision").replaceChildren(...grupos.map(([i, titulo, filas]) => el("section", { class: "revision-grupo" },
    el("header", {}, el("h3", { text: titulo }), el("button", { type: "button", class: "enlace", onclick: () => irA(i) }, icono("editar"), "Editar")),
    el("dl", { class: "resumen" }, filas.filter(Boolean).flatMap(([k, v]) => [el("dt", { text: k }), el("dd", { text: String(v) })])))));
}

// ---------------------------------------------------------------------------- enviar
async function enviar(ev) {
  ev.preventDefault();
  for (let i = 0; i < PASOS.length; i++) {
    const e = erroresDe(i);
    if (e.length) { if (i !== paso) irA(i); setTimeout(() => enfocarError(e[0]), 50); return; }
  }
  $("enc-error").hidden = true;
  const datos = leerFormulario(), beca = actualizarBeca();
  try {
    const r = await conEspera($("enviar"), "Enviando…", () => enviarDatos(datos));
    enviada = true; sucio = false;
    const p = estado.modelo.precios(datos.programa, datos.periodo, beca);
    $("enc-contenido").hidden = true; $("enc-gracias").hidden = false;
    $("gracias-titulo").textContent = `¡Gracias, ${datos.nombre.split(" ")[0]}!`;
    $("gracias-texto").textContent = `${r.asesor || info.asesor} recibió tus datos y te contactará pronto${datos.medio_contacto ? ` por ${MEDIOS[datos.medio_contacto]}` : ""}.`;
    $("gracias-resumen").replaceChildren(el("dl", { class: "resumen" },
      el("dt", { text: "Programa" }), el("dd", { text: PROGRAMAS[datos.programa] }),
      el("dt", { text: "Tu beca" }), el("dd", { text: NOMBRE_BECA[beca] }),
      el("dt", { text: "Tu 1er semestre" }), el("dd", { text: `${pct(p.pct_beca)} de descuento · ${cop(p.neto)}` }),
      el("dt", { text: "Distancia al campus" }), el("dd", { text: $("ruta-km").textContent === "—" ? "Te la cuenta tu asesor" : `${$("ruta-km").textContent} en carro` })));
    animarEntrada($("enc-gracias"));
    $("gracias-titulo").focus();
    window.scrollTo({ top: 0, behavior: "smooth" });
  } catch (e) {
    if (["no-existe", "vencido", "usado", "lleno", "inactivo", "enlace"].includes(e.tipo)) { mostrarInvalido(e.tipo === "enlace" ? "inactivo" : e.tipo); return; }
    $("enc-error").textContent = e.message; $("enc-error").hidden = false;
    avisar("No se pudo enviar la encuesta.", "error");
  }
}

// ---------------------------------------------------------------------------- pantallas
function mostrarInvalido(motivo) {
  const [titulo, texto] = MOTIVOS[motivo] || MOTIVOS["no-existe"];
  $("enc-cargando").hidden = true; $("enc-contenido").hidden = true; $("enc-invalido").hidden = false;
  $("enc-invalido-titulo").textContent = titulo; $("enc-invalido-texto").textContent = texto;
  animarEntrada($("enc-invalido"));
  document.title = `${titulo} · Unicervantes`;
}
function prepararFormulario() {
  const R = estado.modelo.reglas;
  $("enc-pasos").replaceChildren(...PASOS.map((p, i) => el("li", { dataset: { estado: "pendiente" } },
    el("button", { type: "button", onclick: () => { if (i <= paso || erroresDe(paso).length === 0) irA(Math.min(i, paso + 1)); else siguiente(); } },
      el("span", { class: "paso-num" }, el("b", { text: i + 1 }), icono("check")), el("span", { class: "paso-titulo", text: p.titulo })))));
  $("periodo").replaceChildren(...R.periodos.map((p) => el("option", { value: p, text: `${p.endsWith("-1") ? "Primer" : "Segundo"} semestre de ${p.slice(0, 4)}` })));
  if (info.programa) $("programa").value = info.programa;
  $("canal").append(...Object.entries(CANALES).filter(([k]) => k !== "LLAMADA_WHATSAPP").map(([k, v]) => el("option", { value: k, text: v })));
  $("edad").append(...Array.from({ length: 27 }, (_, i) => el("option", { value: 14 + i, text: `${14 + i} años` })), el("option", { value: 41, text: "Más de 40 años" }));
  $("anios").append(el("option", { value: 0, text: "Este año (salgo del colegio)" }),
    ...[1, 2, 3, 4, 5].map((n) => el("option", { value: n, text: n === 1 ? "Hace 1 año" : `Hace ${n} años` })), el("option", { value: 6, text: "Hace 6 años o más" }));
  const municipios = estado.modelo.ubicaciones.filter((u) => u.tipo === "MUNICIPIO");
  $("ciudad").append(el("option", { value: "BOGOTA", text: "Bogotá D.C." }),
    el("optgroup", { label: "Sabana Centro" }, municipios.filter((u) => !u.fuera_de_entrenamiento).map((u) => el("option", { value: u.nombre, text: u.nombre }))),
    el("optgroup", { label: "Municipios vecinos" }, municipios.filter((u) => u.fuera_de_entrenamiento).map((u) => el("option", { value: u.nombre, text: u.nombre }))));
  $("localidad").append(...estado.modelo.ubicaciones.filter((u) => u.tipo === "LOCALIDAD").map((u) => el("option", { value: u.nombre, text: u.nombre })));
  for (const id of ["dir-letra", "dir-letra-cruce"]) $(id).replaceChildren(...LETRAS.map((l) => el("option", { value: l, text: l || "—" })));
  $("enc-asesor").textContent = info.asesor || "tu asesor";

  const f = $("enc-form");
  f.addEventListener("input", (ev) => {
    sucio = true;
    if (ev.target.closest("[data-error]")) VALIDAR[paso]();
    if (ev.target.id === "localidad") delete $("c-localidad").dataset.auto;
    actualizarBeca();
    if (ev.target.closest("#c-direccion") || ev.target.id === "ciudad" || ev.target.id === "localidad") programarUbicacion();
  });
  f.addEventListener("change", (ev) => { if (ev.target.id === "beca-saber11") saber11Tocado = true; actualizarBeca(); });
  f.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" && ev.target.matches("input:not([type=checkbox]):not([type=radio])")) { ev.preventDefault(); if (paso < PASOS.length - 1) siguiente(); }
  });
  f.addEventListener("submit", enviar);
  $("paso-siguiente").addEventListener("click", siguiente);
  $("paso-anterior").addEventListener("click", () => irA(paso - 1));
  $("dir-libre-activa").addEventListener("change", () => {
    const libre = $("dir-libre-activa").checked;
    $("dir-guiada").hidden = libre; $("c-dir-libre").hidden = !libre;
    if (libre && !valor("dir-libre")) $("dir-libre").value = direccionTexto();
    programarUbicacion();
  });
  window.addEventListener("beforeunload", (ev) => { if (sucio && !enviada) { ev.preventDefault(); ev.returnValue = ""; } });
  actualizarBeca(); irA(0, { enfocar: false });
}

async function iniciar() {
  if (!/^[0-9a-f]{32}$/.test(token)) { mostrarInvalido("no-existe"); return; }
  try {
    const [M, config] = await Promise.all([
      fetch("/modelo.json", { cache: "no-cache" }).then((r) => { if (!r.ok) throw new Error(); return r.json(); }),
      demo ? Promise.resolve({}) : import("./config.js"),
    ]);
    estado.modelo = crearModelo(M);
    estado.googleMapsKey = config.GOOGLE_MAPS_KEY || "";
    api = { url: config.SUPABASE_URL, key: config.SUPABASE_KEY };
    if (!demo && (!api.url || !api.key)) throw new Error("sin configuración");
    info = await pedirInfo();
  } catch (e) {
    mostrarInvalido(e.tipo === "conexion" || !info ? "conexion" : "no-existe"); return;
  }
  if (!info.valida) { mostrarInvalido(info.motivo); return; }
  prepararFormulario();
  $("enc-cargando").hidden = true; $("enc-contenido").hidden = false;
  animarEntrada($("enc-contenido"));
  if (demo) avisar("Modo demostración: la respuesta se guarda en este navegador.", "info", { duracion: 3500 });
}

iniciar();
