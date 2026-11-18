// Estado de la app, almacenamiento (Supabase o modo demostración), tiempo real, reglas de beca y distancia, predicción.
import { ubicarEnBogota } from "./modelo.js";

export const estado = {
  modelo: null, version: "", cliente: null, almacen: null, demo: false, usuario: null,
  perfil: null, equipo: [], avatares: new Map(),                    // perfil = { user_id, correo, nombre, rol, activo, ... }
  aspirantes: [], cargados: false, errorCarga: null, enVivo: false, actualizado: null, nuevos: new Set(),
  enlaces: [], googleMapsKey: "",
};

// ---------------------------------------------------------------------------- roles
// ASESOR: solo sus aspirantes · JEFE: todos y el asesor de cada uno · ADMIN: lo del jefe + usuarios y roles ·
// PSICOLOGA: la agenda y la entrevista vocacional de los aspirantes a los que se les envió (nada más).
// La interfaz se adapta al rol, pero quien decide qué se puede leer o cambiar es RLS en Supabase.
export const ROLES = { ASESOR: "Asesor", JEFE: "Jefe de admisiones", PSICOLOGA: "Psicóloga vocacional", ADMIN: "Administrador" };
export const esJefe = () => ["JEFE", "ADMIN"].includes(estado.perfil?.rol);
export const esAdmin = () => estado.perfil?.rol === "ADMIN";
export const esPsicologa = () => estado.perfil?.rol === "PSICOLOGA";
export const ESTADO_ENTREVISTA = { ENVIADA: "Enlace enviado", RESPONDIDA: "Respondió la entrevista", AGENDADA: "Cita agendada",
  ENTREVISTADA: "Entrevistada" };
export function nombreAsesor(id) {
  if (!id) return "Sin asesor";
  const p = estado.equipo.find((x) => x.user_id === id);
  return p ? p.nombre || p.correo : id === estado.perfil?.user_id ? (estado.perfil.nombre || estado.perfil.correo) : "Otro asesor";
}
export async function cargarEquipo() {
  try { estado.equipo = await estado.almacen.listarEquipo(); }
  catch (e) { estado.equipo = estado.perfil ? [estado.perfil] : []; console.error(e); }
  const yo = estado.equipo.find((x) => x.user_id === estado.perfil?.user_id);
  if (yo) estado.perfil = { ...estado.perfil, ...yo };
  await cargarAvatares();
  document.dispatchEvent(new CustomEvent("equipo"));
}
const avisarCambio = (detalle = {}) => document.dispatchEvent(new CustomEvent("aspirantes", { detail: detalle }));

// Origen de cada aspirante (trazabilidad): APP = registrado en la app; SIMULADO = base simulada 2024-1 a 2027-1
// (solo lectura, con su predicción del Sprint 6 y el resultado real).
export const esSimulado = (a) => a.origen === "SIMULADO";
// Un asesor ve también, en solo lectura, los aspirantes que él traspasó a otro asesor
export const traspasadoPorMi = (a) => !esJefe() && !esSimulado(a) && a.asesor_id !== estado.perfil?.user_id && a.traspasado_por === estado.perfil?.user_id;
export const enMiCartera = (a) => esJefe() || esSimulado(a) || a.asesor_id === estado.perfil?.user_id;

// Fotos de perfil (bucket privado "avatares"): URL firmada por una hora, guardada en memoria
export function urlAvatar(persona) {
  const ruta = persona?.avatar_path;
  if (!ruta) return null;
  return ruta.startsWith("data:") ? ruta : estado.avatares.get(ruta) || null;
}
export async function cargarAvatares() {
  const rutas = [...new Set([estado.perfil, ...estado.equipo].map((p) => p?.avatar_path).filter((r) => r && !r.startsWith("data:") && !estado.avatares.has(r)))];
  if (!rutas.length || !estado.almacen.urlsAvatares) return;
  try { (await estado.almacen.urlsAvatares(rutas)).forEach(([ruta, url]) => estado.avatares.set(ruta, url)); }
  catch (e) { console.error(e); }
}

// ---------------------------------------------------------------------------- errores legibles
export class ErrorApp extends Error {
  constructor(mensaje, tipo = "general") { super(mensaje); this.tipo = tipo; }
}
export function traducirError(e) {
  if (e instanceof ErrorApp) return e;
  const m = String((e && (e.message || e.error_description || e.msg)) || e);
  if (!navigator.onLine || /Failed to fetch|NetworkError|network|Load failed/i.test(m))
    return new ErrorApp("Sin conexión con la base de datos. Revise el internet e intente de nuevo.", "conexion");
  if (/JWT|session|token|not authenticated/i.test(m)) return new ErrorApp("La sesión venció. Vuelva a iniciar sesión.", "sesion");
  if (/row-level security|permission denied|42501/i.test(m)) return new ErrorApp("Su cuenta no tiene permiso para esta acción.", "permiso");
  if (/check constraint|violates|23514/i.test(m)) return new ErrorApp("Algún dato no cumple las reglas de la base (revise teléfono, correo y rangos).", "datos");
  return new ErrorApp(m, "general");
}

// ---------------------------------------------------------------------------- almacenamiento
const PERFIL = "user_id, correo, nombre, rol, activo, creado_en, telefono, cargo, avatar_path";
export function almacenSupabase(cliente) {
  const T = "aspirante_registrado";
  const ok = ({ data, error }) => { if (error) throw traducirError(error); return data; };
  return {
    // Vista unificada en vivo (la API entrega como mucho 1000 filas por consulta: se pide por páginas)
    listar: async () => {
      const filas = [];
      for (let desde = 0; ; desde += 1000) {
        const pagina = ok(await cliente.from("vista_aspirantes").select("*").order("creado_en", { ascending: false }).order("id")
          .range(desde, desde + 999));
        filas.push(...pagina);
        if (pagina.length < 1000) return filas;
      }
    },
    // Traspaso: el asesor no puede leer la fila después (ya no es suya), por eso no se pide de vuelta
    traspasar: async (id, destino, motivo) => {
      const cambios = { asesor_id: destino, motivo_traspaso: motivo || null };
      if (esJefe()) return ok(await cliente.from(T).update(cambios).eq("id", id).select().single());
      ok(await cliente.from(T).update(cambios).eq("id", id));
      return null;
    },
    historialTraspasos: async (id) => ok(await cliente.from("traspaso_aspirante").select("de_asesor, a_asesor, motivo, hecho_por, creado_en")
      .eq("aspirante_id", id).order("creado_en", { ascending: false })),
    explicaciones: async (inscripcionId) => ok(await cliente.from("explicacion_prediccion").select("orden, texto")
      .eq("inscripcion_id", inscripcionId).order("orden")).map((x) => x.texto),
    crear: async (r) => ok(await cliente.from(T).insert(r).select().single()),
    actualizar: async (id, c) => ok(await cliente.from(T).update(c).eq("id", id).select().single()),
    eliminar: async (id) => { ok(await cliente.from(T).delete().eq("id", id)); },
    perfil: async (userId) => ok(await cliente.from("personal_autorizado").select(PERFIL).eq("user_id", userId).maybeSingle()),
    listarEquipo: async () => ok(await cliente.from("personal_autorizado").select(PERFIL).order("nombre")),
    actualizarPersona: async (userId, c) => ok(await cliente.from("personal_autorizado").update(c).eq("user_id", userId).select(PERFIL).single()),
    // Foto: <user_id>/avatar-<marca>.webp (RLS de Storage: cada uno escribe solo en su carpeta)
    subirAvatar: async (blob) => {
      const ext = blob.type === "image/jpeg" ? "jpg" : blob.type === "image/png" ? "png" : "webp";
      const ruta = `${estado.perfil.user_id}/avatar-${Date.now()}.${ext}`;
      const { error } = await cliente.storage.from("avatares").upload(ruta, blob, { contentType: blob.type || "image/webp", upsert: false });
      if (error) throw traducirError(error);
      return ruta;
    },
    borrarAvatar: async (ruta) => { if (ruta && !ruta.startsWith("data:")) await cliente.storage.from("avatares").remove([ruta]); },
    urlsAvatares: async (rutas) => {
      const { data, error } = await cliente.storage.from("avatares").createSignedUrls(rutas, 3600);
      if (error) throw traducirError(error);
      return data.filter((x) => x.signedUrl).map((x) => [x.path, x.signedUrl]);
    },
    crearUsuario: async (datos) => {                               // Edge Function: la clave secreta nunca llega al navegador
      const { data, error } = await cliente.functions.invoke("crear-usuario", { body: datos });
      if (error) {
        let mensaje = error.message;
        try { mensaje = (await error.context.json()).error || mensaje; } catch { /* sin cuerpo JSON */ }
        throw new ErrorApp(mensaje, error.context?.status === 403 ? "permiso" : "datos");
      }
      return data;
    },
    cambiarContrasena: async (contrasena) => { const { error } = await cliente.auth.updateUser({ password: contrasena }); if (error) throw traducirError(error); },
    // Enlaces de encuesta: el token lo genera la base; RLS: cada uno ve los suyos, el jefe y el administrador todos
    // Entrevista vocacional: el asesor envía un enlace personal; el aspirante responde; la psicóloga la completa
    crearEnlaceEntrevista: async (aspiranteId) => {
      const e = ok(await cliente.from("enlace_entrevista").insert({ aspirante_id: aspiranteId }).select("id, token, vence_en").single());
      const a = ok(await cliente.from(T).update({ estado_entrevista: "ENVIADA" }).eq("id", aspiranteId).select().single());
      return { enlace: e, aspirante: a };
    },
    listarCitas: async () => ok(await cliente.from("cita_psicologia").select("*").order("inicio")),
    guardarCita: async (c) => {
      const { id, ...datos } = c;
      return id ? ok(await cliente.from("cita_psicologia").update({ ...datos, actualizada_en: new Date().toISOString() }).eq("id", id).select().single())
        : ok(await cliente.from("cita_psicologia").insert(datos).select().single());
    },
    borrarCita: async (id) => { ok(await cliente.from("cita_psicologia").delete().eq("id", id)); },
    listarEntrevistas: async () => ok(await cliente.from("entrevista_vocacional").select("aspirante_id, respondida_en, cerrada_en, puntaje_vocacional, puntaje_vocacional_nlp, requiere_bienestar, admitido")),
    entrevista: async (id) => ok(await cliente.from("entrevista_vocacional").select("*").eq("aspirante_id", id).maybeSingle()),
    guardarEntrevista: async (id, c) => ok(await cliente.from("entrevista_vocacional").update({ ...c, actualizado_en: new Date().toISOString() }).eq("aspirante_id", id).select().single()),
    saludMental: async (id) => ok(await cliente.from("salud_mental_entrevista").select("*").eq("aspirante_id", id).maybeSingle()),
    guardarSaludMental: async (id, c) => ok(await cliente.from("salud_mental_entrevista")
      .upsert({ aspirante_id: id, ...c, actualizada_en: new Date().toISOString() }).select().single()),
    anotaciones: async (id) => ok(await cliente.from("anotacion_psicologia").select("*").eq("aspirante_id", id).order("creada_en", { ascending: false })),
    crearAnotacion: async (id, texto, citaId = null) => ok(await cliente.from("anotacion_psicologia").insert({ aspirante_id: id, texto, cita_id: citaId }).select().single()),
    borrarAnotacion: async (anotacionId) => { ok(await cliente.from("anotacion_psicologia").delete().eq("id", anotacionId)); },
    remisiones: async () => ok(await cliente.from("remision_bienestar").select("*").order("creada_en", { ascending: false })),
    actualizarRemision: async (id, c) => ok(await cliente.from("remision_bienestar").update({ ...c, actualizada_en: new Date().toISOString() }).eq("id", id).select().single()),
    cerrarEntrevista: async (id, cierre, prediccion) => {
      const { error } = await cliente.rpc("psicologa_cerrar_entrevista", { p_aspirante: id, p_cierre: cierre, p_prediccion: prediccion });
      if (error) throw traducirError(error);
    },
    listarEnlaces: async () => ok(await cliente.from("enlace_encuesta").select(ENLACE).order("creado_en", { ascending: false })),
    crearEnlace: async (c) => ok(await cliente.from("enlace_encuesta").insert(c).select(ENLACE).single()),
    actualizarEnlace: async (id, c) => ok(await cliente.from("enlace_encuesta").update(c).eq("id", id).select(ENLACE).single()),
  };
}
const ENLACE = "id, token, asesor_id, nombre, programa, un_solo_uso, activo, creado_en, vence_en, respuestas, ultima_respuesta";

// ---------------------------------------------------------------------------- modo demostración (solo en localhost)
// Se guarda en este navegador; la encuesta de demostración (encuesta.html?demo&t=…) escribe en las mismas claves.
const DEMO = { aspirantes: "unicervantes-app-demo", equipo: "unicervantes-app-demo-equipo", traspasos: "unicervantes-app-demo-traspasos",
  enlaces: "unicervantes-app-demo-enlaces", enlacesEntrevista: "unicervantes-app-demo-enlaces-entrevista",
  entrevistas: "unicervantes-app-demo-entrevistas", citas: "unicervantes-app-demo-citas", salud: "unicervantes-app-demo-salud",
  anotaciones: "unicervantes-app-demo-anotaciones", remisiones: "unicervantes-app-demo-remisiones" };
const EQUIPO_DEMO = [{ user_id: "demo-admin", correo: "admin@demo.local", nombre: "Administración (demo)", rol: "ADMIN", activo: true },
  { user_id: "demo-jefe", correo: "jefe@demo.local", nombre: "Jefatura de Admisiones (demo)", rol: "JEFE", activo: true },
  { user_id: "demo-asesor", correo: "asesor@demo.local", nombre: "Asesor de prueba (demo)", rol: "ASESOR", activo: true },
  { user_id: "demo-asesor-2", correo: "asesora2@demo.local", nombre: "Segunda asesora (demo)", rol: "ASESOR", activo: true },
  { user_id: "demo-psicologa", correo: "psicologa@demo.local", nombre: "Psicóloga vocacional (demo)", rol: "PSICOLOGA", activo: true }];
const leerDe = (k, def) => { try { return JSON.parse(localStorage.getItem(k)) || def; } catch { return def; } };
const guardarEn = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* sin almacenamiento */ } };
// Igual que privado.motivo_enlace en Supabase: por qué un enlace no recibe respuestas (null = sí las recibe)
export function motivoEnlace(e, asesorActivo = true) {
  if (!e.activo || !asesorActivo) return "inactivo";
  if (new Date(e.vence_en) <= new Date()) return "vencido";
  if (e.un_solo_uso && e.respuestas >= 1) return "usado";
  if (e.respuestas >= 300) return "lleno";
  return null;
}
const primerNombre = (p) => (p?.nombre || "").trim().split(/\s+/)[0] || "tu asesor";
export function demoEncuestaInfo(token) {
  const e = leerDe(DEMO.enlaces, []).find((x) => x.token === token);
  if (!e) return { valida: false, motivo: "no-existe" };
  const p = leerDe(DEMO.equipo, EQUIPO_DEMO).find((x) => x.user_id === e.asesor_id);
  const motivo = motivoEnlace(e, Boolean(p && p.activo));
  return { valida: !motivo, motivo, asesor: primerNombre(p), programa: e.programa };
}
export function demoEncuestaEnviar(token, datos) {
  const enlaces = leerDe(DEMO.enlaces, []), i = enlaces.findIndex((x) => x.token === token);
  const info = demoEncuestaInfo(token);
  if (i < 0 || !info.valida) throw new ErrorApp(info.motivo === "no-existe" ? "Este enlace de encuesta no es válido." : "Este enlace ya no está activo. Pide a tu asesor uno nuevo.", "enlace");
  const ahora = new Date().toISOString(), { sitio_web: _trampa, ...limpios } = datos;
  guardarEn(DEMO.aspirantes, [{ id: crypto.randomUUID(), creado_en: ahora, actualizado_en: ahora, estado: "NUEVO", notas: null, registrado_por: null,
    asesor_id: enlaces[i].asesor_id, fuente: "ENCUESTA", enlace_id: enlaces[i].id, ubicada_con: limpios.lat != null ? "CATASTRO" : "CENTRO", ...limpios },
    ...leerDe(DEMO.aspirantes, [])]);
  enlaces[i] = { ...enlaces[i], respuestas: enlaces[i].respuestas + 1, ultima_respuesta: ahora };
  guardarEn(DEMO.enlaces, enlaces);
  return { ok: true, asesor: info.asesor };
}
// Entrevista de demostración (entrevista.html?demo&t=…): igual que entrevista_info y entrevista_enviar en Supabase
export function demoEntrevistaInfo(token) {
  const e = leerDe(DEMO.enlacesEntrevista, []).find((x) => x.token === token);
  if (!e) return { valida: false, motivo: "no-existe" };
  const a = leerDe(DEMO.aspirantes, []).find((x) => x.id === e.aspirante_id) || {};
  const cerrada = leerDe(DEMO.entrevistas, []).some((v) => v.aspirante_id === e.aspirante_id && v.cerrada_en);
  const motivo = !e.activo ? "inactivo" : e.usado_en ? "usado" : new Date(e.vence_en) <= new Date() ? "vencido" : cerrada ? "cerrada" : null;
  return { valida: !motivo, motivo, asesor: primerNombre(leerDe(DEMO.equipo, EQUIPO_DEMO).find((x) => x.user_id === e.asesor_id)),
    nombre: (a.nombre || "").trim().split(/\s+/)[0] || null, programa: a.programa || null };
}
export function demoEntrevistaEnviar(token, datos) {
  const info = demoEntrevistaInfo(token);
  if (!info.valida) throw new ErrorApp(info.motivo === "usado" ? "Ya enviaste tu entrevista con este enlace. ¡Gracias!" : "Este enlace ya no está activo. Pide a tu asesor uno nuevo.", "enlace");
  const enlaces = leerDe(DEMO.enlacesEntrevista, []), i = enlaces.findIndex((x) => x.token === token);
  const { sitio_web: _t, autoriza_datos: _a, salud_mental: _s, ...respuestas } = datos;      // la salud mental nunca viaja en el enlace
  const ahora = new Date().toISOString(), id = enlaces[i].aspirante_id;
  guardarEn(DEMO.entrevistas, [{ aspirante_id: id, enlace_id: enlaces[i].id, respuestas, respondida_en: ahora, cerrada_en: null },
    ...leerDe(DEMO.entrevistas, []).filter((v) => v.aspirante_id !== id)]);
  guardarEn(DEMO.aspirantes, leerDe(DEMO.aspirantes, []).map((a) => (a.id === id && (!a.estado_entrevista || a.estado_entrevista === "ENVIADA")
    ? { ...a, estado_entrevista: "RESPONDIDA" } : a)));
  enlaces[i] = { ...enlaces[i], usado_en: ahora }; guardarEn(DEMO.enlacesEntrevista, enlaces);
  return { ok: true, asesor: info.asesor };
}
// Aspirantes de ejemplo para la psicóloga (solo en la demostración, la primera vez): personas ficticias
const RESPUESTAS_DEMO = [
  { programa: "AD", p: ["Me gustan los datos y quiero entender qué dicen.", "Es la carrera que analiza información para tomar mejores decisiones.",
    "Lo que más me gusta es la estadística y programar en Python.", "Me veo trabajando como analista de datos en una empresa de salud.",
    "Sería ingeniería de sistemas, porque también me gusta la programación."],
    h: ["Soy una persona curiosa y disciplinada; me gusta aprender cosas nuevas.", "Mi mamá es enfermera y mi papá trabaja en una ferretería.",
      "No trabajo; mis papás me van a ayudar y voy a pedir la beca.", "Pensamiento lógico, facilidad para las matemáticas y responsabilidad.",
      "Ser más paciente, organizar mejor mi tiempo y hablar en público.", "Me fue bien; me gustaban matemáticas y física, menos sociales.",
      "Leer, jugar fútbol y hacer retos de programación."],
    u: "Elegí Unicervantes porque un familiar estudió aquí y me la recomendó; quiero estudiar aquí.",
    c: "Los datos ayudan a decidir mejor en salud y educación, que son problemas grandes del país." },
  { programa: "SSIA", p: ["Bueno, todavía no estoy segura, pero dicen que tiene buena salida.", "Creo que es algo relacionado con tecnología.",
    "Me pareció interesante.", "Todavía no sé bien.", "Quizás administración, porque también tiene buena salida."],
    h: ["No sé qué decir; soy normal, me gusta salir con mis amigos.", "Mis papás trabajan en un almacén.", "Trabajo los fines de semana en un restaurante.",
      "Soy amable, puntual y colaboradora.", "La pereza, la desmotivación y ser más ordenada.", "Regular; me costaba química.", "Salir con mis amigos y ver series."],
    u: "Mmm, la verdad no conozco mucho Unicervantes; vi el programa en internet.",
    c: "La tecnología es importante para el país." },
];
function sembrarPsicologia() {
  if (leerDe(DEMO.entrevistas, null) !== null) return;
  const hoy = new Date(), dia = (d, h, m = 0) => { const x = new Date(hoy); x.setDate(x.getDate() + d); x.setHours(h, m, 0, 0); return x.toISOString(); };
  const nombres = ["Valentina Ruiz", "Santiago Pardo", "Laura Moreno", "Juan Esteban Rojas", "Mariana Salazar", "Camilo Torres"];
  const estados = ["RESPONDIDA", "AGENDADA", "AGENDADA", "ENVIADA", "ENTREVISTADA", "RESPONDIDA"];
  const aspirantes = nombres.map((n, j) => ({ id: `demo-voc-${j + 1}`, creado_en: dia(-10 + j, 9), actualizado_en: dia(-1, 9), nombre: `${n} (ficticio)`,
    telefono: `31${String(20000000 + j * 1234567).slice(0, 8)}`, correo: `aspirante${j + 1}@correo.test`, programa: j % 3 === 1 ? "SSIA" : "AD",
    periodo: "2027-1", canal: ["REFERIDO", "EXPOESTUDIANTES", "SITIO_WEB", "INMERSION", "REDES_SOCIALES", "CAMPUS_DAY"][j], icfes: 250 + 15 * j,
    estrato: 1 + (j % 4), ubicacion: ["Suba", "Chía", "Engativá", "Usaquén", "Kennedy", "Cota"][j], solicita_mi_vocacion: true, solicita_saber11: true,
    estado: "NUEVO", notas: null, asesor_id: j % 2 ? "demo-asesor" : "demo-asesor-2", registrado_por: "demo-asesor", fuente: "APP",
    estado_entrevista: estados[j], puntaje_vocacional: estados[j] === "ENTREVISTADA" ? 4 : null,
    puntaje_vocacional_nlp: estados[j] === "ENTREVISTADA" ? 3.9 : null, entrevistada_en: estados[j] === "ENTREVISTADA" ? dia(-2, 10) : null }));
  guardarEn(DEMO.aspirantes, [...aspirantes, ...leerDe(DEMO.aspirantes, []).filter((a) => !String(a.id).startsWith("demo-voc-"))]);
  const resp = (j) => {
    const r = RESPUESTAS_DEMO[j % 2];
    return { datos: { nombre: nombres[j], celular: aspirantes[j].telefono, correo: aspirantes[j].correo, tipo_documento: "CC", numero_documento: `10${j}23456` },
      programa: r.programa, sede: "Bogotá", respuestas: { p1: r.p[0], p2: r.p[1], p3: r.p[2], p4: r.p[3], p5: r.p[4], h1: r.h[0], h2: ["Madre", "Padre"],
        h2_parentesco: "", h3: r.h[1], h4: r.h[2], h5: r.h[3], h6: r.h[4], h7: r.h[5], h8: r.h[6], u1: r.u, c1: r.c } };
  };
  guardarEn(DEMO.entrevistas, aspirantes.filter((a) => a.estado_entrevista !== "ENVIADA").map((a, k) => {
    const j = Number(a.id.split("-").pop()) - 1;
    return { aspirante_id: a.id, respuestas: resp(j), respondida_en: dia(-3 + k % 2, 20), cerrada_en: a.estado_entrevista === "ENTREVISTADA" ? dia(-2, 11) : null,
      puntaje_vocacional: a.puntaje_vocacional, puntaje_vocacional_nlp: a.puntaje_vocacional_nlp, modalidad: "PRESENCIAL" };
  }));
  guardarEn(DEMO.citas, [
    { id: crypto.randomUUID(), aspirante_id: "demo-voc-2", psicologa_id: "demo-psicologa", inicio: dia(0, 9), duracion_min: 45, motivo: "ENTREVISTA_VOCACIONAL", modalidad: "PRESENCIAL", estado: "ATENDIDA" },
    { id: crypto.randomUUID(), aspirante_id: "demo-voc-3", psicologa_id: "demo-psicologa", inicio: dia(0, 11), duracion_min: 45, motivo: "ENTREVISTA_VOCACIONAL", modalidad: "VIRTUAL", estado: "PENDIENTE" },
    { id: crypto.randomUUID(), aspirante_id: "demo-voc-5", psicologa_id: "demo-psicologa", inicio: dia(0, 15, 30), duracion_min: 30, motivo: "SEGUIMIENTO", modalidad: "PRESENCIAL", estado: "PENDIENTE" },
    { id: crypto.randomUUID(), aspirante_id: "demo-voc-1", psicologa_id: "demo-psicologa", inicio: dia(1, 10), duracion_min: 60, motivo: "ENTREVISTA_VOCACIONAL", modalidad: "PRESENCIAL", estado: "PENDIENTE" },
    { id: crypto.randomUUID(), aspirante_id: "demo-voc-6", psicologa_id: "demo-psicologa", inicio: dia(3, 14), duracion_min: 45, motivo: "ENTREVISTA_VOCACIONAL", modalidad: "VIRTUAL", estado: "PENDIENTE" },
  ]);
  guardarEn(DEMO.anotaciones, [{ id: crypto.randomUUID(), aspirante_id: "demo-voc-5", autora: "demo-psicologa", creada_en: dia(-2, 11, 30),
    texto: "Entrevista presencial. Muestra interés claro por el análisis de datos; acordamos seguimiento antes de la matrícula.", cita_id: null }]);
}
export function almacenDemo() {
  const CLAVE = DEMO.aspirantes, CLAVE_EQUIPO = DEMO.equipo;
  const leer = () => leerDe(CLAVE, []), guardar = (l) => guardarEn(CLAVE, l);
  const equipo = () => leerDe(CLAVE_EQUIPO, EQUIPO_DEMO);
  const pausa = () => new Promise((r) => setTimeout(r, 250));     // se siente como una base de datos real
  const visible = (a) => (estado.perfil.rol === "PSICOLOGA" ? Boolean(a.estado_entrevista)
    : estado.perfil.rol !== "ASESOR" || a.asesor_id === estado.perfil.user_id || a.traspasado_por === estado.perfil.user_id);
  const soloPsicologa = () => { if (estado.perfil.rol !== "PSICOLOGA") throw new ErrorApp("Su cuenta no tiene permiso para esta acción.", "permiso"); };
  const CLAVE_TRASPASOS = DEMO.traspasos;
  // Base simulada de ejemplo (en Supabase es la real: 2.991 inscritos), solo para jefe y administrador
  const simulados = () => {
    let semilla = 7;
    const azar = () => { semilla = (semilla * 16807) % 2147483647; return semilla / 2147483647; };
    const lugares = ["Suba", "Engativá", "Kennedy", "Usaquén", "Chía", "Bosa", "Teusaquillo", "Cota", "Zipaquirá", "Ciudad Bolívar"];
    const l = [];
    ["2024-1", "2024-2", "2025-1", "2025-2", "2026-1", "2026-2", "2027-1"].forEach((per, k) => {
      for (let j = 0; j < 14 + 3 * k; j++) {
        const prob = Math.min(0.95, Math.max(0.05, 0.2 + 0.6 * azar())), via = 4 + 40 * azar();
        const real = per === "2027-1" ? null : azar() < prob;
        const [anio, sem] = per.split("-").map(Number);
        l.push({ id: `sim-${k}${j}`, origen: "SIMULADO", inscripcion_id: 1000 * k + j, asesor_simulado: ["Laura Ríos", "Andrés Mora", "Paula Gil"][j % 3],
          creado_en: new Date(Date.UTC(anio - (sem === 1 ? 1 : 0), sem === 1 ? 9 : 4, 1 + (j % 28), 17)).toISOString(),
          nombre: `Aspirante simulado ${per} · ${j + 1}`, telefono: `3${String(100000000 + j * 7919).slice(0, 9)}`, correo: `simulado${k}${j}@correo.test`,
          programa: j % 4 === 0 && per >= "2026-2" ? "SSIA" : "AD", periodo: per, canal: ["SITIO_WEB", "REFERIDO", "EXPOESTUDIANTES", "REDES_SOCIALES"][j % 4],
          icfes: Math.round(220 + 140 * azar()), estrato: 1 + Math.floor(5 * azar()), ubicacion: lugares[j % lugares.length],
          distancia_vial_km: Math.round(via * 100) / 100, distancia_campus_km: Math.round(via * 0.78 * 100) / 100, beca: ["NINGUNA", "MI_VOCACION", "SABER_11"][j % 3],
          solicita_mi_vocacion: j % 4 !== 3, puntaje_vocacional: j % 4 !== 3 ? 1 + ((j + k) % 5) : null,
          probabilidad_matricula: prob, se_matricularia: prob >= 0.5, propension: prob >= 0.6 ? "ALTA" : prob < 0.35 ? "BAJA" : "MEDIA",
          estado: real === null ? "INSCRITO" : real ? "MATRICULADO" : "NO_MATRICULADO", matriculado_real: real });
      }
    });
    return l;
  };
  return {
    listar: async () => { await pausa(); return [...leer().filter(visible).map((a) => ({ origen: "APP", ...a })), ...(esJefe() ? simulados() : [])]; },
    explicaciones: async () => ["Beca y precio (beca Saber 11, descuento 35%): aumenta la probabilidad de matricularse.",
      "Distancia al campus (vive a 12 km por vía): aumenta la probabilidad de matricularse.", "Puntaje Saber 11 (puntaje global 300): reduce la probabilidad de matricularse."],
    subirAvatar: async (blob) => new Promise((ok) => { const r = new FileReader(); r.onload = () => ok(r.result); r.readAsDataURL(blob); }),
    borrarAvatar: async () => {},
    traspasar: async (id, destino, motivo) => {
      await pausa();
      const l = leer(), i = l.findIndex((x) => x.id === id), dest = equipo().find((p) => p.user_id === destino);
      if (i < 0) throw new ErrorApp("Ese aspirante ya no existe.", "no-existe");
      if (!esJefe()) {
        if (l[i].asesor_id !== estado.perfil.user_id) throw new ErrorApp("Su cuenta no tiene permiso para esta acción.", "permiso");
        if (!dest || dest.rol !== "ASESOR" || !dest.activo || destino === estado.perfil.user_id) throw new ErrorApp("Solo puede traspasar el aspirante a otro asesor activo", "permiso");
        if ((motivo || "").trim().length < 5) throw new ErrorApp("Escriba el motivo del traspaso", "datos");
      }
      const ahora = new Date().toISOString();
      guardarEn(CLAVE_TRASPASOS, [{ aspirante_id: id, de_asesor: l[i].asesor_id, a_asesor: destino, motivo: motivo || null, hecho_por: estado.perfil.user_id, creado_en: ahora },
        ...leerDe(CLAVE_TRASPASOS, [])]);
      l[i] = { ...l[i], asesor_id: destino, motivo_traspaso: motivo || null, traspasado_por: estado.perfil.user_id, traspasado_en: ahora, actualizado_en: ahora };
      guardar(l);
      return esJefe() ? { origen: "APP", ...l[i] } : null;
    },
    historialTraspasos: async (id) => leerDe(CLAVE_TRASPASOS, []).filter((t) => t.aspirante_id === id),
    perfil: async (userId) => {
      const yo = equipo().find((p) => p.user_id === userId) || null;
      if (yo?.rol === "PSICOLOGA") sembrarPsicologia();          // sus aspirantes, citas y anotaciones de ejemplo
      return yo;
    },
    listarEquipo: async () => { await pausa(); return esJefe() ? equipo() : equipo().filter((p) => p.user_id === estado.perfil.user_id || (p.activo && p.rol === "ASESOR")); },
    actualizarPersona: async (userId, c) => {
      await pausa();
      const l = equipo(), i = l.findIndex((p) => p.user_id === userId);
      const propio = userId === estado.perfil.user_id && !("rol" in c) && !("activo" in c);   // como RLS: cada uno edita su perfil
      if (!propio && (!esAdmin() || l[i].rol === "ADMIN" || userId === estado.perfil.user_id || (c.rol && !["ASESOR", "JEFE"].includes(c.rol))))
        throw new ErrorApp("Su cuenta no tiene permiso para esta acción.", "permiso");
      l[i] = { ...l[i], ...c }; guardarEn(CLAVE_EQUIPO, l); return l[i];
    },
    crearUsuario: async ({ nombre, correo, rol = "ASESOR" }) => {                // como la Edge Function crear-usuario
      await pausa();
      if (!esAdmin()) throw new ErrorApp("Solo un administrador puede crear usuarios.", "permiso");
      if (!ROLES[rol]) throw new ErrorApp("Elija un rol válido: asesor, jefe de admisiones o administrador.", "datos");
      const l = equipo();
      if (l.some((p) => p.correo === correo.toLowerCase())) throw new ErrorApp("Ya existe una cuenta con ese correo.", "datos");
      const p = { user_id: crypto.randomUUID(), correo: correo.toLowerCase(), nombre, rol, activo: true, creado_en: new Date().toISOString() };
      guardarEn(CLAVE_EQUIPO, [...l, p]); return p;
    },
    cambiarContrasena: async () => { await pausa(); },
    crearEnlaceEntrevista: async (aspiranteId) => {
      await pausa();
      const a = leer().find((x) => x.id === aspiranteId);
      if (!a || !visible(a) || estado.perfil.rol === "PSICOLOGA") throw new ErrorApp("Su cuenta no tiene permiso para esta acción.", "permiso");
      const ahora = new Date();
      const e = { id: crypto.randomUUID(), token: crypto.randomUUID().replace(/-/g, ""), aspirante_id: aspiranteId, asesor_id: estado.perfil.user_id,
        creado_en: ahora.toISOString(), vence_en: new Date(ahora.getTime() + 30 * 864e5).toISOString(), usado_en: null, activo: true };
      guardarEn(DEMO.enlacesEntrevista, [e, ...leerDe(DEMO.enlacesEntrevista, [])]);
      const l = leer(), i = l.findIndex((x) => x.id === aspiranteId);
      if (!l[i].estado_entrevista) l[i] = { ...l[i], estado_entrevista: "ENVIADA" };
      guardar(l);
      return { enlace: e, aspirante: l[i] };
    },
    listarCitas: async () => { soloPsicologa(); return leerDe(DEMO.citas, []).sort((x, y) => x.inicio.localeCompare(y.inicio)); },
    guardarCita: async (c) => {
      await pausa(); soloPsicologa();
      const l = leerDe(DEMO.citas, []), ahora = new Date().toISOString();
      if (c.id) { const i = l.findIndex((x) => x.id === c.id); l[i] = { ...l[i], ...c, actualizada_en: ahora }; guardarEn(DEMO.citas, l); return l[i]; }
      const n = { id: crypto.randomUUID(), psicologa_id: estado.perfil.user_id, estado: "PENDIENTE", creada_en: ahora, actualizada_en: ahora, ...c };
      guardarEn(DEMO.citas, [...l, n]);
      guardar(leer().map((a) => (a.id === c.aspirante_id && ["ENVIADA", "RESPONDIDA"].includes(a.estado_entrevista) ? { ...a, estado_entrevista: "AGENDADA" } : a)));
      return n;
    },
    borrarCita: async (id) => { await pausa(); soloPsicologa(); guardarEn(DEMO.citas, leerDe(DEMO.citas, []).filter((x) => x.id !== id)); },
    listarEntrevistas: async () => { soloPsicologa(); return leerDe(DEMO.entrevistas, []); },
    entrevista: async (id) => { soloPsicologa(); return leerDe(DEMO.entrevistas, []).find((v) => v.aspirante_id === id) || null; },
    guardarEntrevista: async (id, c) => {
      await pausa(); soloPsicologa();
      const l = leerDe(DEMO.entrevistas, []), i = l.findIndex((v) => v.aspirante_id === id);
      const v = { ...(i >= 0 ? l[i] : { aspirante_id: id, respuestas: {} }), ...c };
      guardarEn(DEMO.entrevistas, i >= 0 ? l.map((x, k) => (k === i ? v : x)) : [...l, v]); return v;
    },
    saludMental: async (id) => { soloPsicologa(); return leerDe(DEMO.salud, []).find((s) => s.aspirante_id === id) || null; },
    guardarSaludMental: async (id, c) => {
      await pausa(); soloPsicologa();
      if (!c.consentimiento) throw new ErrorApp("Registre el consentimiento del aspirante antes de guardar esta sección.", "datos");
      const s = { aspirante_id: id, ...c, actualizada_en: new Date().toISOString() };
      guardarEn(DEMO.salud, [s, ...leerDe(DEMO.salud, []).filter((x) => x.aspirante_id !== id)]); return s;
    },
    anotaciones: async (id) => { soloPsicologa(); return leerDe(DEMO.anotaciones, []).filter((x) => x.aspirante_id === id).sort((x, y) => y.creada_en.localeCompare(x.creada_en)); },
    crearAnotacion: async (id, texto, citaId = null) => {
      await pausa(); soloPsicologa();
      const n = { id: crypto.randomUUID(), aspirante_id: id, cita_id: citaId, autora: estado.perfil.user_id, creada_en: new Date().toISOString(), texto };
      guardarEn(DEMO.anotaciones, [n, ...leerDe(DEMO.anotaciones, [])]); return n;
    },
    borrarAnotacion: async (anotacionId) => { await pausa(); soloPsicologa(); guardarEn(DEMO.anotaciones, leerDe(DEMO.anotaciones, []).filter((x) => x.id !== anotacionId)); },
    remisiones: async () => { soloPsicologa(); return leerDe(DEMO.remisiones, []); },
    actualizarRemision: async (id, c) => {
      soloPsicologa();
      const l = leerDe(DEMO.remisiones, []), i = l.findIndex((x) => x.id === id);
      l[i] = { ...l[i], ...c }; guardarEn(DEMO.remisiones, l); return l[i];
    },
    cerrarEntrevista: async (id, cierre, prediccion) => {                 // como psicologa_cerrar_entrevista en Supabase
      await pausa(); soloPsicologa();
      const ahora = new Date().toISOString(), l = leerDe(DEMO.entrevistas, []), i = l.findIndex((v) => v.aspirante_id === id);
      const v = { ...(i >= 0 ? l[i] : { aspirante_id: id, respuestas: {} }), ...cierre, cerrada_en: (i >= 0 && l[i].cerrada_en) || ahora, entrevistadora: estado.perfil.user_id };
      delete v.nota_bienestar;
      guardarEn(DEMO.entrevistas, i >= 0 ? l.map((x, k) => (k === i ? v : x)) : [...l, v]);
      guardar(leer().map((a) => (a.id === id ? { ...a, puntaje_vocacional: cierre.puntaje_vocacional, puntaje_vocacional_nlp: cierre.puntaje_vocacional_nlp,
        estado_entrevista: "ENTREVISTADA", entrevistada_en: a.entrevistada_en || ahora, beca: prediccion.beca, precio_neto_primer_semestre: prediccion.precio_neto_primer_semestre,
        probabilidad_matricula: prediccion.probabilidad_matricula, se_matricularia: prediccion.se_matricularia, propension: prediccion.propension,
        prediccion: prediccion.prediccion, predicho_en: ahora } : a)));
      if (cierre.requiere_bienestar && !leerDe(DEMO.remisiones, []).some((r) => r.aspirante_id === id && r.estado !== "CERRADA"))
        guardarEn(DEMO.remisiones, [{ id: crypto.randomUUID(), aspirante_id: id, creada_por: estado.perfil.user_id, creada_en: ahora, estado: "PENDIENTE",
          nota: cierre.nota_bienestar || null }, ...leerDe(DEMO.remisiones, [])]);
    },
    listarEnlaces: async () => { await pausa(); return leerDe(DEMO.enlaces, []).filter((e) => esJefe() || e.asesor_id === estado.perfil.user_id); },
    crearEnlace: async (c) => {
      await pausa();
      const ahora = new Date();
      const e = { id: crypto.randomUUID(), token: crypto.randomUUID().replace(/-/g, ""), asesor_id: estado.perfil.user_id, nombre: c.nombre || null,
        programa: c.programa || null, un_solo_uso: Boolean(c.un_solo_uso), activo: true, creado_en: ahora.toISOString(),
        vence_en: c.vence_en || new Date(ahora.getTime() + 30 * 864e5).toISOString(), respuestas: 0, ultima_respuesta: null };
      guardarEn(DEMO.enlaces, [e, ...leerDe(DEMO.enlaces, [])]); return e;
    },
    actualizarEnlace: async (id, c) => {
      await pausa();
      const l = leerDe(DEMO.enlaces, []), i = l.findIndex((x) => x.id === id);
      if (i < 0 || (!esJefe() && l[i].asesor_id !== estado.perfil.user_id)) throw new ErrorApp("Su cuenta no tiene permiso para esta acción.", "permiso");
      l[i] = { ...l[i], ...("activo" in c ? { activo: c.activo } : {}), ...("nombre" in c ? { nombre: c.nombre } : {}) };
      guardarEn(DEMO.enlaces, l); return l[i];
    },
    crear: async (r) => {
      await pausa();
      const ahora = new Date().toISOString();
      const a = { id: crypto.randomUUID(), creado_en: ahora, actualizado_en: ahora, estado: "NUEVO", notas: null,
        registrado_por: estado.perfil.user_id, asesor_id: estado.perfil.user_id, ...r };
      guardar([a, ...leer()]); return a;
    },
    actualizar: async (id, c) => {
      await pausa();
      const l = leer(), i = l.findIndex((x) => x.id === id);
      if (i < 0) throw new ErrorApp("Ese aspirante ya no existe.", "no-existe");
      l[i] = { ...l[i], ...c, actualizado_en: new Date().toISOString() }; guardar(l); return l[i];
    },
    eliminar: async (id) => {
      await pausa();
      if (!esJefe()) throw new ErrorApp("Su cuenta no tiene permiso para esta acción.", "permiso");
      guardar(leer().filter((x) => x.id !== id));
    },
  };
}

export async function cargarAspirantes() {
  try {
    estado.aspirantes = await estado.almacen.listar();
    estado.cargados = true; estado.errorCarga = null; estado.actualizado = new Date();
  } catch (e) {
    estado.errorCarga = traducirError(e);
  }
  avisarCambio({ tipo: "carga" });
}
export function reemplazar(fila, { remoto = false } = {}) {
  const a = { origen: "APP", ...fila };                            // lo que llega de aspirante_registrado es de la app
  const i = estado.aspirantes.findIndex((x) => x.id === a.id);
  if (i >= 0) estado.aspirantes[i] = a;
  else { estado.aspirantes.unshift(a); if (remoto) estado.nuevos.add(a.id); }
  estado.actualizado = new Date();
  avisarCambio({ tipo: i >= 0 ? "actualizado" : "nuevo", id: a.id, remoto });
}
export function quitar(id, { remoto = false } = {}) {
  estado.aspirantes = estado.aspirantes.filter((x) => x.id !== id);
  estado.actualizado = new Date();
  avisarCambio({ tipo: "eliminado", id, remoto });
}

// Tiempo real: Supabase avisa cada alta, cambio o borrado (RLS: solo llega lo que el usuario puede leer).
// Si el canal se cae, se vuelve a leer la tabla cada minuto.
let canal = null, respaldo = null;
export function escucharCambios() {
  if (!estado.cliente || canal) return;
  canal = estado.cliente.channel("aspirantes-en-vivo")
    .on("postgres_changes", { event: "*", schema: "public", table: "aspirante_registrado" }, (p) => {
      if (p.eventType === "DELETE") quitar(p.old.id, { remoto: true }); else reemplazar(p.new, { remoto: true });
    })
    .on("postgres_changes", { event: "INSERT", schema: "public", table: "traspaso_aspirante" }, (p) => {
      document.dispatchEvent(new CustomEvent("traspaso", { detail: p.new }));
    })
    .on("postgres_changes", { event: "*", schema: "public", table: "enlace_encuesta" }, () => {
      document.dispatchEvent(new CustomEvent("enlaces"));
    })
    .subscribe((s) => {
      estado.enVivo = s === "SUBSCRIBED";
      clearInterval(respaldo);
      if (!estado.enVivo) respaldo = setInterval(cargarAspirantes, 60000);
      avisarCambio({ tipo: "vivo" });
    });
}
// Demostración: la encuesta abierta en otra pestaña escribe en localStorage; aquí llega como si fuera tiempo real
export function escucharDemo() {
  window.addEventListener("storage", async (ev) => {
    if (ev.key === DEMO.enlaces) document.dispatchEvent(new CustomEvent("enlaces"));
    if (ev.key !== DEMO.aspirantes || !estado.almacen) return;
    const conocidos = new Set(estado.aspirantes.map((a) => a.id));
    for (const a of await estado.almacen.listar()) if (a.origen === "APP" && !conocidos.has(a.id)) reemplazar(a, { remoto: true });
  });
}

// Dirección pública de la encuesta (en Vercel, /encuesta/<código>; aquí, el archivo con el código en la consulta)
export function urlEncuesta(token) {
  const local = ["localhost", "127.0.0.1", "[::1]"].includes(location.hostname);
  return local ? `${location.origin}/encuesta.html?${estado.demo ? "demo&" : ""}t=${token}` : `${location.origin}/encuesta/${token}`;
}

// Dirección pública de la entrevista vocacional (en Vercel, /entrevista/<código>)
export function urlEntrevista(token) {
  const local = ["localhost", "127.0.0.1", "[::1]"].includes(location.hostname);
  return local ? `${location.origin}/entrevista.html?${estado.demo ? "demo&" : ""}t=${token}` : `${location.origin}/entrevista/${token}`;
}

export async function dejarDeEscuchar() {
  clearInterval(respaldo);
  if (canal) { await estado.cliente.removeChannel(canal); canal = null; }
  estado.enVivo = false;
}

// ---------------------------------------------------------------------------- reglas: beca, banda, zona
export function elegirBeca(icfes, saber11, miVocacion, vocacional) {
  const R = estado.modelo.reglas, cand = [];
  if (saber11 && icfes !== null && icfes >= R.umbral_icfes) cand.push("SABER_11");
  if (miVocacion && vocacional !== null && vocacional >= R.puntaje_vocacional_minimo) cand.push("MI_VOCACION");
  if (!cand.length) return "NINGUNA";
  return cand.sort((x, y) => R.becas[y].pct_siguientes - R.becas[x].pct_siguientes || R.becas[y].pct_primer - R.becas[x].pct_primer)[0];
}
// Entrevista vocacional: la hace la psicóloga. Da el puntaje vocacional de 1 a 5 (el que exige Mi Vocación, ≥ 3) y el
// modelo NLP lee otro puntaje de 1 a 5 en las respuestas abiertas del aspirante. Sin entrevista, los dos quedan vacíos.
export const conEntrevista = (a) => a.puntaje_vocacional !== null && a.puntaje_vocacional !== undefined;
export function banda(icfes) {
  if (icfes === null || icfes === undefined || icfes === "") return null;
  const b = estado.modelo.reglas.bandas_icfes.find((x) => icfes >= x.desde && icfes < x.hasta);
  return b ? { BAJO: "Bajo", MEDIO: "Medio", ALTO: "Alto", SUPERIOR: "Superior" }[b.segmento] : null;
}
export function zona(kmVia) {
  if (kmVia === null || kmVia === undefined) return null;
  const z = estado.modelo.reglas.zonas_distancia_km;
  return kmVia <= z.CERCA ? "CERCA" : kmVia <= z.MEDIA ? "MEDIA" : "LEJOS";
}
export const ubicacionDe = (nombre) => estado.modelo.ubicaciones.find((u) => u.nombre === nombre);

// Distancia al campus desde una coordenada (o el centro de la ubicación): en línea recta y por vías (la usa el modelo)
export function distanciasDesde(lat, lon) {
  const [recta, via] = estado.modelo.distancias(lat, lon);
  return { recta: Math.round(recta * 100) / 100, via: Math.round(via * 100) / 100 };
}

// Ubica una dirección de Bogotá en Catastro (con límite de 20 s y memoria para no repetir consultas)
const memoria = new Map();
async function buscarConTiempo(url) {
  const control = new AbortController(), t = setTimeout(() => control.abort(), 20000);
  try { return await fetch(url, { signal: control.signal }); }
  catch (e) { throw new Error(e.name === "AbortError" ? "Catastro no respondió a tiempo" : "sin conexión con Catastro"); }
  finally { clearTimeout(t); }
}
export async function ubicarDireccion(direccion) {
  const clave = direccion.trim().toUpperCase();
  if (!memoria.has(clave)) memoria.set(clave, ubicarEnBogota(direccion, buscarConTiempo).catch((e) => { memoria.delete(clave); throw e; }));
  const g = await memoria.get(clave);
  const loc = estado.modelo.ubicaciones.find((x) => x.tipo === "LOCALIDAD" && x.ubicacion_id === g.localidad);
  return { ...g, localidad: loc ? loc.nombre : null };
}

// ---------------------------------------------------------------------------- predicción
export async function calcular(a) {
  const M = estado.modelo, avisos = [];
  const miVoc = Boolean(a.solicita_mi_vocacion), hecha = conEntrevista(a);
  const voc = hecha ? Number(a.puntaje_vocacional) : null;
  if (miVoc && !hecha) avisos.push("Aún no presenta la entrevista vocacional con la psicóloga: el modelo lo toma como sin entrevista y la beca Mi Vocación queda pendiente.");
  if (hecha && (a.puntaje_vocacional_nlp === null || a.puntaje_vocacional_nlp === undefined) && !a.respuestas_entrevista)
    avisos.push("La entrevista no tiene respuestas en texto: el modelo usó el puntaje de la psicóloga como puntaje NLP.");
  const beca = elegirBeca(a.icfes, a.solicita_saber11, miVoc && hecha, voc);
  const entrada = { punt_global: a.icfes, estrato: a.estrato, programa: a.programa, periodo: a.periodo, ubicacion: a.ubicacion,
    entrevista: hecha, puntaje_vocacional: voc ?? undefined, puntaje_vocacional_nlp: a.puntaje_vocacional_nlp ?? undefined,
    respuestas_entrevista: a.respuestas_entrevista ?? undefined, beca,
    tipo_colegio: a.tipo_colegio || undefined, genero: a.genero || undefined, edad: a.edad ?? undefined,
    anios_desde_saber11: a.anios_desde_saber11 ?? undefined, apoyo_foes: Boolean(a.apoyo_foes), regimen_salud: a.regimen_salud || undefined,
    canal: a.canal && a.canal !== "OTRO" ? a.canal : undefined,
    tipo_descuento: a.tipo_descuento || undefined, pct_descuento_adicional: a.tipo_descuento ? Number(a.pct_descuento_adicional) : undefined,
    solicita_icetex: Boolean(a.solicita_icetex), municipio_colegio: a.municipio_colegio || undefined };
  if (!entrada.canal) avisos.push("Sin canal de captación conocido: el modelo usó «Sitio web», su canal de referencia.");
  const u = ubicacionDe(a.ubicacion);
  const cambios = {};
  if (a.ubicada_con === "CATASTRO" && a.lat !== null && a.lon !== null) {
    Object.assign(entrada, { lat: a.lat, lon: a.lon, direccion: a.direccion });
  } else if (u && u.tipo === "LOCALIDAD" && a.direccion) {
    try {
      const g = await ubicarDireccion(a.direccion);
      Object.assign(entrada, { lat: g.lat, lon: g.lon, direccion: a.direccion });
      Object.assign(cambios, { lat: g.lat, lon: g.lon, ubicada_con: "CATASTRO" });
      if (g.localidad && g.localidad !== a.ubicacion) {
        entrada.ubicacion = g.localidad; cambios.ubicacion = g.localidad;
        avisos.push(`Según la dirección, el aspirante vive en ${g.localidad} (se usó esa localidad).`);
      }
    } catch (e) {
      avisos.push(`No se pudo ubicar la dirección en Catastro (${e.message}). La distancia se calculó desde el centro de ${a.ubicacion}.`);
    }
  } else if (u && u.tipo === "MUNICIPIO") {
    avisos.push(`Catastro solo cubre Bogotá: en ${a.ubicacion} la distancia se calcula desde el centro del municipio.`);
  }
  if (u && u.fuera_de_entrenamiento)
    avisos.push(`${u.nombre} no estaba en los datos de entrenamiento (Bogotá y Sabana Centro): la predicción se apoya en su distancia al campus y es una extrapolación.`);
  const r = M.predecir(entrada);
  return { r, precios: M.precios(a.programa, a.periodo, r.beca_que_aplica, Number(a.pct_descuento_adicional || 0)), avisos, umbral: M.reglas.umbral_clasificacion, cambios };
}

export async function predecirYGuardar(a) {
  const { r, precios, avisos, umbral, cambios } = await calcular(a);
  const nuevo = await estado.almacen.actualizar(a.id, {
    ...cambios, beca: r.beca_que_aplica, precio_neto_primer_semestre: precios.neto,
    probabilidad_matricula: r.probabilidad_matricula, se_matricularia: r.probabilidad_matricula >= umbral,
    propension: r.segmento_propension,
    distancia_campus_km: r.distancia_campus_km, distancia_vial_km: r.distancia_vial_km,
    prediccion: { ...r, avisos, precios, umbral, modelo: estado.version }, predicho_en: new Date().toISOString(),
  });
  reemplazar(nuevo);
  return nuevo;
}
