// Equipo (jefe y administrador): qué aspirantes tiene cada asesor y cómo va su seguimiento.
// Usuarios (administrador): crear cuentas como ASESOR, JEFE, PSICOLOGA o ADMIN (con la Edge Function crear-usuario),
// cambiar el rol entre ASESOR, JEFE y PSICOLOGA y dar de baja o reactivar a cualquiera menos a otro administrador (RLS
// lo impide igual).
// Mi cuenta (todos): cambiar la contraseña propia.
import { $, el, icono, pct, hace, fecha, iniciales, avisar, conEspera, animarNumero } from "./ui.js";
import { estado, ROLES, esJefe, esAdmin, nombreAsesor, cargarEquipo, traducirError, esSimulado } from "./datos.js";
import { avatarPersona } from "./perfil.js";

const activos = () => estado.equipo.filter((p) => p.activo);
const llevanAspirantes = (p) => p.rol !== "PSICOLOGA";      // la psicóloga no tiene cartera: no se le asignan aspirantes
const ordenRol = { ASESOR: 0, PSICOLOGA: 1, JEFE: 2, ADMIN: 3 };
const avatar = (nombre, clase = "avatar") => el("span", { class: clase, "aria-hidden": "true", text: iniciales(nombre || "?") });
const fotoDe = (persona, nombre) => (persona ? avatarPersona(persona) : avatar(nombre));
const chipRol = (rol) => el("span", { class: "chip", dataset: { tono: rol }, text: ROLES[rol] || rol });

// Selectores de asesor (registro, ficha y filtro de la lista)
export function llenarSelectoresAsesor() {
  if (!esJefe()) return;
  const gente = activos().filter(llevanAspirantes).sort((x, y) => ordenRol[x.rol] - ordenRol[y.rol] || (x.nombre || "").localeCompare(y.nombre || "", "es"));
  const opcion = (p) => el("option", { value: p.user_id, text: `${p.nombre || p.correo}${p.rol !== "ASESOR" ? ` · ${ROLES[p.rol].toLowerCase()}` : ""}` });
  for (const id of ["asesor"]) {
    const sel = $(id), actual = sel.value;
    sel.replaceChildren(...gente.map(opcion));
    sel.value = actual && gente.some((p) => p.user_id === actual) ? actual : estado.perfil.user_id;
  }
  const f = $("f-asesor"), actual = f.value;
  f.replaceChildren(el("option", { value: "", text: "Todos" }), ...estado.equipo.filter(llevanAspirantes).map((p) => el("option", { value: p.user_id, text: p.nombre || p.correo })),
    el("option", { value: "SIN", text: "Sin asesor" }));
  f.value = actual;
}

// ---------------------------------------------------------------------------- vista: equipo
export function pintarEquipo() {
  const L = estado.aspirantes.filter((a) => !esSimulado(a)), grupos = new Map();   // los de la base simulada no tienen asesor de la app
  for (const a of L) { const k = a.asesor_id || "SIN"; if (!grupos.has(k)) grupos.set(k, []); grupos.get(k).push(a); }
  for (const p of estado.equipo) if (p.rol === "ASESOR" && p.activo && !grupos.has(p.user_id)) grupos.set(p.user_id, []);
  const filas = [...grupos.entries()].map(([id, l]) => {
    const P = l.filter((a) => a.propension), si = P.filter((a) => a.se_matricularia).length;
    return { id, l, persona: estado.equipo.find((p) => p.user_id === id), n: l.length, pred: P.length,
      prob: P.length ? P.reduce((s, a) => s + a.probabilidad_matricula, 0) / P.length : null, si, pctSi: P.length ? si / P.length : null,
      nuevos: l.filter((a) => a.estado === "NUEVO").length, logrados: l.filter((a) => ["INSCRITO", "MATRICULADO"].includes(a.estado)).length,
      ultimo: l.reduce((m, a) => (!m || a.creado_en > m ? a.creado_en : m), null) };
  }).sort((x, y) => y.n - x.n || (x.id === "SIN") - (y.id === "SIN"));
  const max = Math.max(1, ...filas.map((f) => f.n));
  const conAspirantes = filas.filter((f) => f.id !== "SIN" && f.n > 0).length;
  const kpi = (id, texto) => el("div", { class: "kpi" }, el("strong", { id }), el("span", { text: texto }));
  if (!$("ek-asesores")) $("equipo-kpis").replaceChildren(kpi("ek-asesores", "asesores activos"), kpi("ek-con", "con aspirantes asignados"),
    kpi("ek-sin", "aspirantes sin asesor"), kpi("ek-promedio", "aspirantes por asesor (promedio)"));
  const asesores = estado.equipo.filter((p) => p.rol === "ASESOR" && p.activo).length;
  animarNumero($("ek-asesores"), asesores); animarNumero($("ek-con"), conAspirantes);
  animarNumero($("ek-sin"), (grupos.get("SIN") || []).length);
  animarNumero($("ek-promedio"), conAspirantes ? L.filter((a) => a.asesor_id).length / conAspirantes : 0, (v) => v.toFixed(1).replace(".", ","));
  $("equipo-filas").replaceChildren(...(filas.length ? filas.map((f) => {
    const nombre = f.id === "SIN" ? "Sin asesor" : f.persona ? f.persona.nombre || f.persona.correo : nombreAsesor(f.id);
    const ir = () => { $("f-asesor").value = f.id; location.hash = "#/aspirantes"; };
    const barra = el("span", { class: "mini-barra" }, el("i", { estilo: { width: `${(100 * f.n) / max}%`, background: "var(--rojo)" } }));
    const celda = (etiqueta, ...c) => el("td", { dataset: { etiqueta } }, ...c);
    return el("tr", { class: "fila-enlace", onclick: ir, tabindex: "0", onkeydown: (ev) => { if (ev.key === "Enter") ir(); } },
      celda("Asesor", el("div", { class: "persona" }, fotoDe(f.persona, nombre), el("span", { class: "persona-texto" }, el("b", { text: nombre }),
        el("small", { text: f.persona ? `${f.persona.correo}${f.persona.activo ? "" : " · desactivado"}` : "aspirantes por asignar" })),
        f.persona && f.persona.rol !== "ASESOR" && chipRol(f.persona.rol))),
      celda("Aspirantes", el("div", { class: "mini-prob" }, el("b", { text: f.n }), barra)),
      celda("Con predicción", String(f.pred)),
      celda("Prob. promedio", f.prob === null ? "—" : pct(f.prob)),
      celda("Se matricularían", f.pctSi === null ? "—" : `${f.si} (${pct(f.pctSi)})`),
      celda("Por contactar", f.nuevos ? el("span", { class: "chip", dataset: { tono: "NUEVO" }, text: f.nuevos }) : "0"),
      celda("Inscritos o matriculados", String(f.logrados)),
      celda("Último registro", el("small", { title: f.ultimo ? fecha(f.ultimo) : "", text: f.ultimo ? hace(f.ultimo) : "—" })));
  }) : [el("tr", {}, el("td", { colspan: "8", class: "vacio", text: "Todavía no hay asesores ni aspirantes." }))]));
}

// ---------------------------------------------------------------------------- vista: usuarios
export function pintarUsuarios() {
  const gente = estado.equipo.slice().sort((x, y) => (y.activo - x.activo) || ordenRol[y.rol] - ordenRol[x.rol] || (x.nombre || "").localeCompare(y.nombre || "", "es"));
  $("u-conteo").textContent = String(activos().length);
  $("u-lista").replaceChildren(...gente.map((p) => {
    const yo = p.user_id === estado.perfil.user_id, editable = !yo && p.rol !== "ADMIN";
    const control = editable
      ? el("label", { class: "rol-selector" }, el("span", { class: "sr", text: `Rol de ${p.nombre || p.correo}` }),
          el("select", { onchange: (ev) => cambiarRol(p, ev.target) }, ["ASESOR", "JEFE", "PSICOLOGA"].map((r) => el("option", { value: r, text: ROLES[r], selected: p.rol === r }))))
      : el("span", { class: "rol-fijo" }, chipRol(p.rol), el("small", { text: yo ? "su cuenta" : "no se puede dar de baja" }));
    return el("li", { class: "usuario-fila", dataset: { activo: String(p.activo) } },
      avatarPersona(p), el("div", { class: "persona-texto" }, el("b", { text: p.nombre || "Sin nombre" }), p.cargo && el("small", { text: p.cargo }),
        el("small", { text: `${p.correo}${p.creado_en ? ` · desde ${new Date(p.creado_en).toLocaleDateString("es-CO", { timeZone: "America/Bogota", day: "numeric", month: "short", year: "numeric" })}` : ""}` })),
      control,
      editable && el("button", { type: "button", class: `discreto ${p.activo ? "peligro" : ""}`, onclick: (ev) => cambiarActivo(p, ev.currentTarget),
        "aria-label": `${p.activo ? "Dar de baja a" : "Reactivar a"} ${p.nombre || p.correo}` }, p.activo ? "Dar de baja" : "Reactivar"),
      !p.activo && el("span", { class: "chip", dataset: { tono: "DESCARTADO" }, text: "Dado de baja" }));
  }));
}
async function cambiarRol(p, select) {
  const nuevo = select.value; select.disabled = true;
  try {
    await estado.almacen.actualizarPersona(p.user_id, { rol: nuevo });
    avisar(`${p.nombre || p.correo} ahora es ${ROLES[nuevo].toLowerCase()}.`, "exito", { duracion: 2500 });
    await cargarEquipo();
  } catch (e) { select.value = p.rol; avisar(traducirError(e).message, "error"); }
  finally { select.disabled = false; }
}
// Dar de baja pide confirmación en el mismo botón (un segundo clic antes de 4 s); reactivar no la necesita
function confirmado(boton) {
  const volver = () => { delete boton.dataset.confirmar; boton.textContent = "Dar de baja"; };
  if (boton.dataset.confirmar === "si") { volver(); return true; }
  boton.dataset.confirmar = "si"; boton.textContent = "¿Confirmar baja?";
  setTimeout(() => { if (boton.dataset.confirmar === "si") volver(); }, 4000);
  return false;
}
async function cambiarActivo(p, boton) {
  if (p.activo && !confirmado(boton)) return;
  try {
    await conEspera(boton, p.activo ? "Dando de baja…" : "Reactivando…", () => estado.almacen.actualizarPersona(p.user_id, { activo: !p.activo }));
    avisar(p.activo ? `${p.nombre || p.correo} quedó dado de baja: ya no tiene acceso. Sus aspirantes siguen guardados.` : `${p.nombre || p.correo} recuperó el acceso.`, "info");
    await cargarEquipo();
  } catch (e) { avisar(traducirError(e).message, "error"); }
}

// Contraseña temporal: 14 caracteres sin ambiguos (0/O, 1/l), con letras y números
function contrasenaTemporal() {
  const letras = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz", numeros = "23456789", todos = letras + numeros;
  const r = (conj) => conj[crypto.getRandomValues(new Uint32Array(1))[0] % conj.length];
  const c = [r(letras), r(numeros), ...Array.from({ length: 12 }, () => r(todos))];
  for (let i = c.length - 1; i > 0; i--) { const j = crypto.getRandomValues(new Uint32Array(1))[0] % (i + 1); [c[i], c[j]] = [c[j], c[i]]; }
  return c.join("");
}
const claveValida = (c) => c.length >= 10 && /[A-Za-z]/.test(c) && /\d/.test(c);
function marcar(id, hay) { if (hay) $(id).dataset.error = ""; else delete $(id).dataset.error; return hay; }

const rolElegido = () => document.querySelector('input[name="u-rol"]:checked')?.value || "ASESOR";
function pintarRolElegido() {
  const rol = rolElegido();
  $("u-rol-chip").textContent = `Rol: ${ROLES[rol].toLowerCase()}`; $("u-rol-chip").dataset.tono = rol;
  $("u-aviso-admin").hidden = rol !== "ADMIN";
}

async function crearUsuario(ev) {
  ev.preventDefault();
  const nombre = $("u-nombre").value.trim().replace(/\s+/g, " "), correo = $("u-correo").value.trim().toLowerCase(), contrasena = $("u-clave").value;
  const rol = rolElegido();
  const malos = [marcar("c-u-nombre", nombre.length < 3), marcar("c-u-correo", !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(correo)), marcar("c-u-clave", !claveValida(contrasena))];
  if (malos.some(Boolean)) { document.querySelector("#form-usuario [data-error] input")?.focus(); return; }
  $("u-error").hidden = true;
  try {
    const p = await conEspera($("u-crear"), "Creando…", () => estado.almacen.crearUsuario({ nombre, correo, contrasena, rol }));
    avisar(`Cuenta creada para ${p.nombre} (${ROLES[p.rol || rol].toLowerCase()}). Comparta la contraseña temporal por un medio seguro.`, "exito", { duracion: 6000 });
    $("form-usuario").reset(); pintarRolElegido();
    await cargarEquipo();
  } catch (e) {
    const err = traducirError(e); $("u-error").textContent = err.message; $("u-error").hidden = false;
  }
}

export function iniciarEquipo() {
  $("form-usuario").addEventListener("submit", crearUsuario);
  $("form-usuario").addEventListener("input", (ev) => { const c = ev.target.closest("[data-error]"); if (c) delete c.dataset.error; });
  $("form-usuario").addEventListener("change", (ev) => { if (ev.target.name === "u-rol") pintarRolElegido(); });
  $("u-generar").addEventListener("click", () => { $("u-clave").value = contrasenaTemporal(); delete $("c-u-clave").dataset.error; });
  $("u-copiar").addEventListener("click", async () => {
    if (!$("u-clave").value) return;
    try { await navigator.clipboard.writeText($("u-clave").value); avisar("Contraseña copiada.", "info", { duracion: 1800 }); }
    catch { avisar("No se pudo copiar; selecciónela y cópiela a mano.", "error"); }
  });
}
export { esAdmin };
