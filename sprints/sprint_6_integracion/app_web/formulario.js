// Registro de aspirantes por pasos: Aspirante → Contacto → Saber 11 y becas → Residencia → Colegio → Revisar.
// La dirección se arma con desplegables (tipo de vía, número, letra, Bis, Sur/Este) y en Bogotá se ubica sola en
// Catastro; el panel lateral muestra en vivo la beca, el precio y la distancia al campus (línea recta y por vías).
import { $, el, icono, cop, pct, km, avisar, conEspera, animarEntrada, CANALES, DETALLE_CANAL, NOMBRE_BECA, ZONAS, LETRAS, armarDireccion } from "./ui.js";
import { estado, elegirBeca, banda, zona, ubicacionDe, distanciasDesde, ubicarDireccion, predecirYGuardar, reemplazar, traducirError,
  esJefe, nombreAsesor } from "./datos.js";
import { tarjetaRuta } from "./mapa.js";

const PASOS = [
  { titulo: "Aspirante", ayuda: "Quién es y a qué programa aspira" },
  { titulo: "Contacto", ayuda: "Cómo comunicarse y cómo conoció la Universidad" },
  { titulo: "Saber 11 y becas", ayuda: "Puntaje ICFES, estrato y becas" },
  { titulo: "Residencia", ayuda: "Dónde vive: define la distancia al campus" },
  { titulo: "Colegio", ayuda: "Opcional" },
  { titulo: "Revisar", ayuda: "Confirme los datos y la autorización" },
];
let paso = 0, saber11Tocado = false, sucio = false;
const geo = { estado: "inactivo", clave: "", lat: null, lon: null, localidad: null, mensaje: "" };
let temporizador = null;
// Mapa de la ruta en el panel lateral: la misma tarjeta de la ficha, con sus propios elementos (prefijo "r-")
const pintarRutaRegistro = tarjetaRuta("r-", { vacio: "El mapa aparece cuando elige la ciudad o municipio." });
let temporizadorRuta = null, rutaPintada = null;

const valor = (id) => $(id).value.trim();
// "BOGOTÁ D.C." -> "Bogotá D.C.", "SAN JOSÉ DEL GUAVIARE" -> "San José Del Guaviare"
const titulo = (s) => String(s).toLowerCase().replace(/(^|[\s(.])(\p{L})/gu, (_, a, b) => a + b.toUpperCase());
const numero = (id) => { const v = valor(id).replace(",", "."); return v === "" ? null : Number(v); };

// ---------------------------------------------------------------------------- dirección guiada
function direccionTexto() {
  if ($("dir-libre-activa").checked) return valor("dir-libre");
  return armarDireccion({ tipo: valor("dir-tipo"), numero: valor("dir-numero"), letra: valor("dir-letra"), bis: valor("dir-bis"),
    cuadrante: valor("dir-cuadrante"), cruce: valor("dir-cruce"), letraCruce: valor("dir-letra-cruce"), placa: valor("dir-placa") });
}
function ciudad() { return valor("ciudad"); }
function ubicacionElegida() { return ciudad() === "BOGOTA" ? valor("localidad") : ciudad(); }

function programarUbicacion() {
  clearTimeout(temporizador);
  const d = direccionTexto();
  $("dir-vista").textContent = d || "Complete tipo de vía, número y placa";
  $("dir-vista").dataset.vacia = d ? "no" : "si";
  if (ciudad() !== "BOGOTA" || !d) {
    Object.assign(geo, { estado: "inactivo", clave: "", lat: null, lon: null, localidad: null, mensaje: "" });
    pintarDistancia(); return;
  }
  if (geo.clave === d && geo.estado !== "error") { pintarDistancia(); return; }
  temporizador = setTimeout(() => ubicar(d), 700);
}
async function ubicar(d) {
  Object.assign(geo, { estado: "buscando", clave: d, mensaje: "Buscando la placa en Catastro…" });
  pintarDistancia();
  try {
    const g = await ubicarDireccion(d);
    if (geo.clave !== d) return;                                  // el usuario siguió escribiendo
    Object.assign(geo, { estado: "ok", lat: g.lat, lon: g.lon, localidad: g.localidad, mensaje: "" });
    if (g.localidad && valor("localidad") !== g.localidad) {
      $("localidad").value = g.localidad; $("c-localidad").dataset.auto = "si";
      geo.mensaje = `Localidad detectada por Catastro: ${g.localidad}.`;
    }
  } catch (e) {
    if (geo.clave !== d) return;
    Object.assign(geo, { estado: "error", lat: null, lon: null, localidad: null,
      mensaje: `${e.message}. Se usará el centro de la localidad.` });
  }
  actualizarPanel();
}

// ---------------------------------------------------------------------------- panel lateral en vivo
function pintarDistancia() {
  const u = ubicacionDe(ubicacionElegida());
  const caja = $("panel-distancia");
  let d = null, origen = "";
  if (geo.estado === "ok") { d = distanciasDesde(geo.lat, geo.lon); origen = "Desde la placa ubicada en Catastro"; }
  else if (u) { d = distanciasDesde(u.lat, u.lon); origen = `Aproximada, desde el centro de ${u.nombre}`; }
  $("dist-recta").textContent = d ? km(d.recta) : "—";
  $("dist-via").textContent = d ? km(d.via) : "—";
  const z = d ? zona(d.via) : null;
  $("dist-zona").textContent = z ? `Zona ${ZONAS[z].toLowerCase()}` : "Sin ubicación";
  $("dist-zona").dataset.tono = z || "";
  $("dist-origen").textContent = d ? origen : "Elija la ciudad o municipio y escriba la dirección.";
  const estadoGeo = $("dist-estado");
  estadoGeo.hidden = !geo.mensaje && geo.estado !== "buscando";
  estadoGeo.dataset.tono = geo.estado;
  estadoGeo.replaceChildren(geo.estado === "buscando" ? el("span", { class: "giro", "aria-hidden": "true" }) : icono(geo.estado === "error" ? "alerta" : "pin"),
    el("span", { text: geo.estado === "buscando" ? "Buscando la placa en Catastro…" : geo.mensaje }));
  $("dist-extrapola").hidden = !(u && u.fuera_de_entrenamiento);
  $("dist-extrapola").textContent = u && u.fuera_de_entrenamiento
    ? `${u.nombre} no está en los datos de entrenamiento: el modelo la calcula por su distancia (extrapolación).` : "";
  caja.dataset.lleno = d ? "si" : "no";
  programarRuta();
}

// Se vuelve a trazar solo cuando cambia el punto de partida (la placa de Catastro o el centro de la localidad o
// municipio), no con cada tecla, y se espera a que Catastro termine de buscar la placa
function programarRuta() {
  if (geo.estado === "buscando") return;
  const ubic = ubicacionElegida(), conGeo = geo.estado === "ok";
  const clave = conGeo ? `${geo.lat.toFixed(3)},${geo.lon.toFixed(3)}` : ubic;
  if (clave === rutaPintada) return;
  rutaPintada = clave;
  clearTimeout(temporizadorRuta);
  temporizadorRuta = setTimeout(() => pintarRutaRegistro({ id: "registro", ubicacion: ubic, lat: conGeo ? geo.lat : null, lon: conGeo ? geo.lon : null,
    ubicada_con: conGeo ? "CATASTRO" : "CENTRO", distancia_ruta_km: null }), 400);
}


function notaBeca(beca, pideMiVocacion) {
  if (beca === "SABER_11" && pideMiVocacion) return "Saber 11: 35% en toda la carrera. Da más que Mi Vocación (30%) y las becas no se suman, así que esa queda sin efecto.";
  if (beca === "SABER_11") return "Saber 11: 35% en toda la carrera, que se conserva con promedio de 4,0 o más.";
  if (pideMiVocacion) return "Por ahora no tiene beca. Si la psicóloga le da 3 o más en la entrevista vocacional, recibe Mi Vocación: 30% en toda la carrera.";
  return "Sin beca: paga la tarifa plena del semestre, menos el descuento si tiene uno.";
}

// Descuento institucional elegido ("PERSONAL:0.15" -> { tipo: "PERSONAL", pct: 0.15 }) y municipio del colegio
function descuentoElegido() {
  const v = valor("descuento");
  if (!v) return { tipo: null, pct: 0 };
  const [tipo, p] = v.split(":");
  return { tipo, pct: Number(p) };
}
function municipioColegio() {
  const u = ubicacionDe(ubicacionElegida());
  return valor("municipio-colegio") || (u ? u.municipio : null);
}
function estadoIcetex(icfes) {
  const R = estado.modelo.reglas, m = municipioColegio();
  if (icfes === null) return { texto: "Escriba el puntaje ICFES", tono: "no" };
  if (!m) return { texto: "Elija dónde vive o el municipio del colegio", tono: "no" };
  const minimo = R.icetex.merito_minimo[m.toUpperCase()], nombre = titulo(m);
  if (minimo === undefined) return { texto: `ICETEX no publica el mérito mínimo de ${nombre}`, tono: "no" };
  return icfes >= minimo ? { texto: `Cumple el mérito mínimo de ${nombre} (${minimo})`, tono: "ok" }
    : { texto: `No cumple: el mérito mínimo en ${nombre} es ${minimo}`, tono: "no" };
}

function actualizarPanel() {
  const R = estado.modelo.reglas, icfes = numero("icfes");
  const cb = $("beca-saber11"), est = $("estado-saber11");
  const cumple = icfes !== null && icfes >= R.umbral_icfes && icfes <= 500;
  cb.disabled = !cumple;
  if (!cumple) { cb.checked = false; saber11Tocado = false; } else if (!saber11Tocado) cb.checked = true;
  est.textContent = icfes === null ? "Escriba el puntaje ICFES" : cumple ? `Cumple: ${R.umbral_icfes} o más` : `Le faltan ${Math.max(0, R.umbral_icfes - icfes)} puntos`;
  est.dataset.tono = cumple ? "ok" : "no";
  const b = banda(icfes);
  $("icfes-banda").textContent = b ? `Nivel ${b.toLowerCase()}` : "";
  $("icfes-banda").hidden = !b;
  const mv = $("beca-mivocacion").checked;
  $("c-vocacional").hidden = !mv;
  // Mi Vocación se confirma después, con el puntaje que da la psicóloga en la entrevista vocacional (3 o más)
  $("estado-mivocacion").textContent = !mv ? "No solicitada" : `Se confirma en la entrevista vocacional (puntaje ${R.puntaje_vocacional_minimo} o más)`;
  $("estado-mivocacion").dataset.tono = mv ? "ok" : "no";

  const esBogota = ciudad() === "BOGOTA";
  $("c-localidad").hidden = !esBogota;
  const u = ubicacionDe(ubicacionElegida());
  const foes = Boolean(u && R.fondos_municipales.includes(u.ubicacion_id));
  $("c-foes").hidden = !foes; if (!foes) $("foes").checked = false;
  $("c-detalle-canal").hidden = !valor("canal") || !DETALLE_CANAL[valor("canal")];
  $("canal-detalle").placeholder = DETALLE_CANAL[valor("canal")] || "";

  const beca = elegirBeca(icfes, cb.checked, false, null);       // Mi Vocación se suma después de la entrevista
  const desc = descuentoElegido();
  const p = estado.modelo.precios(valor("programa"), valor("periodo"), beca, desc.pct);
  const ice = estadoIcetex(icfes);
  $("estado-icetex").textContent = ice.texto;
  $("estado-icetex").dataset.tono = ice.tono;
  $("r-beca").textContent = NOMBRE_BECA[beca];
  $("r-beca").dataset.tono = beca;
  $("r-tarifa").textContent = cop(p.bruto);
  $("r-descuento").textContent = desc.pct ? `${pct(p.pct_beca)} + ${pct(desc.pct)} = ${pct(p.pct_total)}` : pct(p.pct_total);
  $("r-neto").textContent = cop(p.neto);
  $("r-siguientes").textContent = `${pct(p.pct_siguientes)} · ${cop(p.neto_siguientes)}`;
  $("r-nota").textContent = notaBeca(beca, mv);
  pintarDistancia();
}

// ---------------------------------------------------------------------------- validación por paso
function marcar(id, hay) { const c = $(id); if (hay) c.dataset.error = ""; else delete c.dataset.error; return hay ? id : null; }
const VALIDAR = [
  () => [marcar("c-nombre", valor("nombre").length < 2)],
  () => {
    const tel = valor("telefono"), correo = valor("correo");
    $("aviso-sin-contacto").hidden = Boolean(tel || correo);
    return [marcar("c-telefono", tel !== "" && !/^[0-9 +()-]{7,20}$/.test(tel)),
      marcar("c-correo", correo !== "" && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(correo))];
  },
  () => {
    const icfes = numero("icfes");
    return [marcar("c-icfes", icfes === null || !Number.isInteger(icfes) || icfes < 0 || icfes > 500),
      marcar("c-estrato", valor("estrato") === "")];
  },
  () => {
    const libre = $("dir-libre-activa").checked;
    return [marcar("c-ciudad", ciudad() === ""), marcar("c-localidad", ciudad() === "BOGOTA" && valor("localidad") === ""),
      marcar("c-direccion", direccionTexto() === "" || (!libre && !/^\d+$/.test(valor("dir-placa"))))];
  },
  () => [],
  () => [marcar("c-autoriza", !$("autoriza").checked)],
];
const erroresDe = (i) => VALIDAR[i]().filter(Boolean);

// ---------------------------------------------------------------------------- navegación entre pasos
function irA(i, { enfocar = true } = {}) {
  paso = Math.max(0, Math.min(PASOS.length - 1, i));
  document.querySelectorAll("#formulario .paso").forEach((f, j) => {
    f.hidden = j !== paso;
    if (j === paso) animarEntrada(f);
  });
  document.querySelectorAll("#pasos li").forEach((li, j) => {
    li.dataset.estado = j < paso ? "hecho" : j === paso ? "actual" : "pendiente";
    const b = li.querySelector("button");
    if (j === paso) b.setAttribute("aria-current", "step"); else b.removeAttribute("aria-current");
  });
  $("progreso-relleno").style.width = `${((paso + 1) / PASOS.length) * 100}%`;
  $("paso-texto").textContent = `Paso ${paso + 1} de ${PASOS.length} · ${PASOS[paso].ayuda}`;
  $("paso-anterior").hidden = paso === 0;
  $("paso-siguiente").hidden = paso === PASOS.length - 1;
  $("acciones-registro").hidden = paso !== PASOS.length - 1;
  if (paso === PASOS.length - 1) pintarRevision();
  if (enfocar) {
    const f = document.querySelector(`#formulario .paso[data-paso="${paso}"]`);
    (f.querySelector("input:not([type=hidden]):not(:disabled), select") || f).focus({ preventScroll: true });
    $("vista-registrar").scrollIntoView({ block: "start", behavior: "smooth" });
  }
}
function siguiente() {
  const e = erroresDe(paso);
  if (e.length) { enfocarError(e[0]); return; }
  irA(paso + 1);
}
function enfocarError(id) {
  const c = $(id);
  c.classList.remove("sacudir"); void c.offsetWidth; c.classList.add("sacudir");
  (c.querySelector("input, select") || c).focus();
}

// ---------------------------------------------------------------------------- lectura del formulario
function leerFormulario() {
  const icfes = numero("icfes"), miVoc = $("beca-mivocacion").checked, s11 = $("beca-saber11").checked;
  const beca = elegirBeca(icfes, s11, false, null);           // Mi Vocación: después de la entrevista vocacional
  const desc = descuentoElegido();
  const p = estado.modelo.precios(valor("programa"), valor("periodo"), beca, desc.pct);
  const ubic = ubicacionElegida(), u = ubicacionDe(ubic);
  const conGeo = geo.estado === "ok" && ciudad() === "BOGOTA";
  const d = conGeo ? distanciasDesde(geo.lat, geo.lon) : u ? distanciasDesde(u.lat, u.lon) : null;
  const texto = (id) => valor(id) || null;
  const entero = (id) => (valor(id) === "" ? null : Number(valor(id)));
  return {
    nombre: valor("nombre").replace(/\s+/g, " "), telefono: texto("telefono"), correo: texto("correo") && valor("correo").toLowerCase(),
    medio_contacto: texto("medio"), genero: texto("genero"), edad: entero("edad"), autoriza_datos: $("autoriza").checked,
    programa: valor("programa"), periodo: valor("periodo"), canal: texto("canal"), canal_detalle: $("c-detalle-canal").hidden ? null : texto("canal-detalle"),
    icfes, anios_desde_saber11: entero("anios"), estrato: Number(valor("estrato")),
    solicita_mi_vocacion: miVoc, solicita_saber11: s11,
    direccion: direccionTexto(), direccion_complemento: texto("dir-complemento"), ubicacion: ubic,
    lat: conGeo ? geo.lat : u ? u.lat : null, lon: conGeo ? geo.lon : u ? u.lon : null, ubicada_con: conGeo ? "CATASTRO" : "CENTRO",
    distancia_campus_km: d ? d.recta : null, distancia_vial_km: d ? d.via : null,
    apoyo_foes: $("foes").checked, regimen_salud: texto("regimen"), colegio: texto("colegio"), tipo_colegio: texto("tipo-colegio"),
    tipo_descuento: desc.tipo, pct_descuento_adicional: desc.pct, solicita_icetex: $("icetex").checked,
    municipio_colegio: texto("municipio-colegio"),
    beca, precio_neto_primer_semestre: p.neto,
    asesor_id: esJefe() && valor("asesor") ? valor("asesor") : estado.perfil.user_id,   // el asesor siempre se asigna a sí mismo
  };
}

function pintarRevision() {
  const r = leerFormulario();
  const opcion = (id) => { const s = $(id); return s.value ? s.options[s.selectedIndex].text : "Sin dato"; };
  const grupos = [
    [0, "Aspirante", [["Nombre", r.nombre], ["Programa", opcion("programa")], ["Periodo", r.periodo], ["Género", opcion("genero")], ["Edad", r.edad ?? "Sin dato"],
      ["Asesor asignado", nombreAsesor(r.asesor_id)]]],
    [1, "Contacto", [["Teléfono", r.telefono || "Sin dato"], ["Correo", r.correo || "Sin dato"], ["Prefiere", opcion("medio")],
      ["¿Cómo conoció la Universidad?", [r.canal ? CANALES[r.canal] : "Sin dato", r.canal_detalle].filter(Boolean).join(" · ")]]],
    [2, "Saber 11 y becas", [["ICFES", `${r.icfes}${banda(r.icfes) ? ` (nivel ${banda(r.icfes).toLowerCase()})` : ""}`], ["Estrato", r.estrato],
      ["Años desde el Saber 11", opcion("anios")],
      ["Entrevista vocacional", r.solicita_mi_vocacion ? "Solicita Mi Vocación: después de registrarlo, envíele la entrevista vocacional desde su ficha" : "No solicita Mi Vocación"],
      ["Beca que se aplica", NOMBRE_BECA[r.beca]], ["Descuento institucional", r.tipo_descuento ? opcion("descuento") : "Ninguno"],
      ["Crédito ICETEX", r.solicita_icetex ? `Lo solicitará · ${estadoIcetex(r.icfes).texto}` : "No lo solicitará"]]],
    [3, "Residencia", [["Dirección", [r.direccion, r.direccion_complemento].filter(Boolean).join(", ")], ["Ubicación", r.ubicacion],
      ["Distancia al campus", r.distancia_vial_km === null ? "—" : `${km(r.distancia_vial_km)} por vía · ${km(r.distancia_campus_km)} en línea recta`],
      ["Ubicada con", r.ubicada_con === "CATASTRO" ? "Catastro Bogotá (placa)" : "Centro de la localidad o municipio"],
      r.apoyo_foes && ["Fondo municipal", "Solicitará FOES/FOEST"], ["Régimen de salud", opcion("regimen")]]],
    [4, "Colegio", [["Nombre", r.colegio || "Sin dato"], ["Tipo", opcion("tipo-colegio")],
      ["Municipio", r.municipio_colegio ? titulo(r.municipio_colegio) : "El mismo donde vive"]]],
  ];
  $("revision").replaceChildren(...grupos.map(([i, titulo, filas]) => el("section", { class: "revision-grupo" },
    el("header", {}, el("h3", { text: titulo }), el("button", { type: "button", class: "enlace", onclick: () => irA(i) }, icono("editar"), "Editar")),
    el("dl", { class: "resumen" }, filas.filter(Boolean).flatMap(([k, v]) => [el("dt", { text: k }), el("dd", { text: String(v) })])))));
}

// ---------------------------------------------------------------------------- registrar
async function registrar(predecir) {
  for (let i = 0; i < PASOS.length; i++) {
    const e = erroresDe(i);
    if (e.length) { if (i !== paso) irA(i); setTimeout(() => enfocarError(e[0]), 50); return; }
  }
  const boton = predecir ? $("registrar-predecir") : $("registrar-solo");
  const otro = predecir ? $("registrar-solo") : $("registrar-predecir");
  $("error-registro").hidden = true; otro.disabled = true;
  try {
    const a = await conEspera(boton, predecir ? "Guardando y prediciendo…" : "Guardando…", async () => {
      let nuevo = await estado.almacen.crear(leerFormulario());
      reemplazar(nuevo);
      if (predecir) nuevo = await predecirYGuardar(nuevo);
      return nuevo;
    });
    avisar(predecir ? `${a.nombre}: registrado y predicho (${pct(a.probabilidad_matricula)}).` : `${a.nombre}: registrado.`, "exito");
    limpiar();
    location.hash = `#/aspirante/${a.id}`;
  } catch (e) {
    const err = traducirError(e);
    $("error-registro").textContent = err.message; $("error-registro").hidden = false;
    avisar("No se pudo guardar el aspirante.", "error");
  } finally { otro.disabled = false; }
}

function limpiar() {
  $("formulario").reset();
  saber11Tocado = false; sucio = false;
  Object.assign(geo, { estado: "inactivo", clave: "", lat: null, lon: null, localidad: null, mensaje: "" });
  document.querySelectorAll("#formulario [data-error]").forEach((c) => delete c.dataset.error);
  delete $("c-localidad").dataset.auto;
  $("dir-guiada").hidden = false; $("c-dir-libre").hidden = true;
  setTimeout(() => { actualizarPanel(); programarUbicacion(); irA(0, { enfocar: false }); }, 0);
}

export const formularioSucio = () => sucio;
export function mostrarFormulario() { actualizarPanel(); irA(paso, { enfocar: false }); }

export function iniciarFormulario() {
  const R = estado.modelo.reglas;
  // Desplegables
  $("pasos").replaceChildren(...PASOS.map((p, i) => el("li", { dataset: { estado: "pendiente" } },
    el("button", { type: "button", onclick: () => { if (i <= paso || erroresDe(paso).length === 0) irA(i); else siguiente(); } },
      el("span", { class: "paso-num" }, el("b", { text: i + 1 }), icono("check")), el("span", { class: "paso-titulo", text: p.titulo })))));
  $("periodo").replaceChildren(...R.periodos.map((p) => el("option", { value: p, text: p })));
  $("canal").append(...Object.entries(CANALES).map(([k, v]) => el("option", { value: k, text: v })));
  $("edad").append(...Array.from({ length: 27 }, (_, i) => el("option", { value: 14 + i, text: `${14 + i} años` })), el("option", { value: 41, text: "Más de 40 años" }));
  $("anios").append(el("option", { value: 0, text: "Este año (sale del colegio)" }),
    ...[1, 2, 3, 4, 5].map((n) => el("option", { value: n, text: n === 1 ? "Hace 1 año" : `Hace ${n} años` })), el("option", { value: 6, text: "Hace 6 años o más" }));
  const municipios = estado.modelo.ubicaciones.filter((u) => u.tipo === "MUNICIPIO");
  $("ciudad").append(el("option", { value: "BOGOTA", text: "Bogotá D.C." }),
    el("optgroup", { label: "Sabana Centro" }, municipios.filter((u) => !u.fuera_de_entrenamiento).map((u) => el("option", { value: u.nombre, text: u.nombre }))),
    el("optgroup", { label: "Municipios vecinos" }, municipios.filter((u) => u.fuera_de_entrenamiento).map((u) => el("option", { value: u.nombre, text: u.nombre }))));
  $("localidad").append(...estado.modelo.ubicaciones.filter((u) => u.tipo === "LOCALIDAD").map((u) => el("option", { value: u.nombre, text: u.nombre })));
  $("descuento").append(...Object.entries(R.descuentos.tipos).flatMap(([k, t]) => t.pct.map((p) =>
    el("option", { value: `${k}:${p}`, text: `${t.nombre} (${pct(p)})` }))));
  $("municipio-colegio").append(...Object.keys(R.icetex.merito_minimo).sort((a, b) => a.localeCompare(b, "es"))
    .map((m) => el("option", { value: m, text: titulo(m) })));
  for (const id of ["dir-letra", "dir-letra-cruce"]) $(id).replaceChildren(...LETRAS.map((l) => el("option", { value: l, text: l || "—" })));

  // Eventos
  const f = $("formulario");
  f.addEventListener("input", (ev) => {
    sucio = true;
    const c = ev.target.closest("[data-error]");
    if (c) VALIDAR[paso]();
    if (ev.target.id === "localidad") delete $("c-localidad").dataset.auto;
    actualizarPanel();
    if (ev.target.closest("#c-direccion") || ev.target.id === "ciudad" || ev.target.id === "localidad") programarUbicacion();
  });
  f.addEventListener("change", (ev) => { if (ev.target.id === "beca-saber11") saber11Tocado = true; actualizarPanel(); });
  f.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" && ev.target.matches("input:not([type=checkbox])")) { ev.preventDefault(); if (paso < PASOS.length - 1) siguiente(); }
  });
  f.addEventListener("submit", (ev) => { ev.preventDefault(); registrar(true); });
  $("registrar-solo").addEventListener("click", () => registrar(false));
  $("paso-siguiente").addEventListener("click", siguiente);
  $("paso-anterior").addEventListener("click", () => irA(paso - 1));
  $("limpiar").addEventListener("click", () => { limpiar(); avisar("Formulario limpio.", "info", { duracion: 2000 }); });
  $("dir-libre-activa").addEventListener("change", () => {
    const libre = $("dir-libre-activa").checked;
    $("dir-guiada").hidden = libre; $("c-dir-libre").hidden = !libre;
    if (libre && !valor("dir-libre")) $("dir-libre").value = direccionTexto();
    programarUbicacion();
  });
  window.addEventListener("beforeunload", (ev) => { if (sucio) { ev.preventDefault(); ev.returnValue = ""; } });
  actualizarPanel(); programarUbicacion(); irA(0, { enfocar: false });
}
