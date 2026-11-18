// Mi perfil: cada persona del equipo cambia sus datos (nombre, teléfono, cargo), su foto y su contraseña.
// La foto se recorta cuadrada a 256 px en el navegador (sin metadatos de ubicación) y se guarda en el bucket privado
// "avatares" de Supabase Storage, en la carpeta del usuario; el resto del equipo la ve con una URL firmada.
// También dibuja el botón de usuario de la barra lateral (foto, nombre y rol).
import { $, el, avisar, conEspera, iniciales } from "./ui.js";
import { estado, ROLES, traducirError, urlAvatar, cargarEquipo, cargarAvatares } from "./datos.js";

// Foto o iniciales de una persona del equipo
export function avatarPersona(persona, clase = "avatar") {
  const nombre = persona?.nombre || persona?.correo || "?";
  const url = urlAvatar(persona);
  return url ? el("span", { class: `${clase} con-foto`, "aria-hidden": "true" }, el("img", { src: url, alt: "", loading: "lazy" }))
    : el("span", { class: clase, "aria-hidden": "true", text: iniciales(nombre) });
}
const nombreVisible = (p) => p.nombre || p.correo.replace(/@.*/, "").replace(/[._-]/g, " ");

export function pintarUsuarioMenu() {
  const p = estado.perfil; if (!p) return;
  $("usuario-avatar").replaceWith(Object.assign(avatarPersona(p, "avatar chico"), { id: "usuario-avatar" }));
  $("usuario-nombre").textContent = nombreVisible(p);
  $("usuario").textContent = p.correo;
  $("usuario-rol").textContent = ROLES[p.rol]; $("usuario-rol").dataset.tono = p.rol;
}

// ---------------------------------------------------------------------------- vista
export function pintarPerfil() {
  const p = estado.perfil;
  $("p-avatar").replaceWith(Object.assign(avatarPersona(p, "avatar enorme"), { id: "p-avatar" }));
  $("p-nombre-vista").textContent = nombreVisible(p);
  $("p-correo-vista").textContent = p.correo;
  $("p-rol").textContent = ROLES[p.rol]; $("p-rol").dataset.tono = p.rol;
  $("p-desde").textContent = p.creado_en ? `Con acceso desde el ${new Date(p.creado_en).toLocaleDateString("es-CO", { timeZone: "America/Bogota", day: "numeric", month: "long", year: "numeric" })}` : "";
  $("p-quitar-foto").hidden = !p.avatar_path;
  if (!$("form-perfil").dataset.sucio) {
    $("pf-nombre").value = p.nombre || ""; $("pf-telefono").value = p.telefono || ""; $("pf-cargo").value = p.cargo || "";
    $("pf-correo").value = p.correo; $("pf-rol").value = ROLES[p.rol];
  }
}

function marcar(id, hay) { if (hay) $(id).dataset.error = ""; else delete $(id).dataset.error; return hay; }
async function refrescar(persona) {
  estado.perfil = { ...estado.perfil, ...persona };
  const i = estado.equipo.findIndex((x) => x.user_id === persona.user_id);
  if (i >= 0) estado.equipo[i] = { ...estado.equipo[i], ...persona };
  await cargarAvatares();
  pintarUsuarioMenu(); pintarPerfil();
  document.dispatchEvent(new CustomEvent("equipo"));
}

async function guardarDatos(ev) {
  ev.preventDefault();
  const nombre = $("pf-nombre").value.trim().replace(/\s+/g, " "), telefono = $("pf-telefono").value.trim(), cargo = $("pf-cargo").value.trim();
  const malos = [marcar("c-pf-nombre", nombre.length < 3 || nombre.length > 80), marcar("c-pf-telefono", telefono !== "" && !/^[0-9 +()-]{7,20}$/.test(telefono))];
  if (malos.some(Boolean)) { document.querySelector("#form-perfil [data-error] input")?.focus(); return; }
  $("pf-error").hidden = true;
  try {
    const p = await conEspera($("pf-guardar"), "Guardando…", () => estado.almacen.actualizarPersona(estado.perfil.user_id, { nombre, telefono: telefono || null, cargo: cargo || null }));
    delete $("form-perfil").dataset.sucio;
    await refrescar(p);
    avisar("Sus datos quedaron guardados.", "exito", { duracion: 2500 });
  } catch (e) { $("pf-error").textContent = traducirError(e).message; $("pf-error").hidden = false; }
}

// Recorta al centro y reduce a 256×256 (webp; jpeg si el navegador no codifica webp)
function recortar(archivo) {
  return new Promise((resolver, rechazar) => {
    const lector = new FileReader();
    lector.onerror = () => rechazar(new Error("No se pudo leer la imagen."));
    lector.onload = () => {
      const img = new Image();
      img.onerror = () => rechazar(new Error("El archivo no es una imagen válida."));
      img.onload = () => {
        const lado = Math.min(img.width, img.height), c = document.createElement("canvas");
        c.width = c.height = 256;
        c.getContext("2d").drawImage(img, (img.width - lado) / 2, (img.height - lado) / 2, lado, lado, 0, 0, 256, 256);
        c.toBlob((b) => {
          if (b && b.type === "image/webp") resolver(b);
          else c.toBlob((j) => (j ? resolver(j) : rechazar(new Error("No se pudo preparar la imagen."))), "image/jpeg", 0.88);
        }, "image/webp", 0.86);
      };
      img.src = lector.result;
    };
    lector.readAsDataURL(archivo);
  });
}
async function cambiarFoto() {
  const archivo = $("p-foto").files[0]; $("p-foto").value = "";
  if (!archivo) return;
  if (!/^image\/(png|jpe?g|webp)$/.test(archivo.type)) { avisar("Use una imagen JPG, PNG o WEBP.", "error"); return; }
  if (archivo.size > 8 * 1024 * 1024) { avisar("La imagen pesa más de 8 MB.", "error"); return; }
  const anterior = estado.perfil.avatar_path;
  try {
    await conEspera($("p-cambiar-foto"), "Subiendo…", async () => {
      const ruta = await estado.almacen.subirAvatar(await recortar(archivo));
      const p = await estado.almacen.actualizarPersona(estado.perfil.user_id, { avatar_path: ruta });
      if (anterior && anterior !== ruta) await estado.almacen.borrarAvatar(anterior).catch(() => {});
      await refrescar(p);
    });
    avisar("Foto de perfil actualizada.", "exito", { duracion: 2500 });
  } catch (e) { avisar(traducirError(e).message, "error"); }
}
async function quitarFoto() {
  const anterior = estado.perfil.avatar_path; if (!anterior) return;
  try {
    const p = await conEspera($("p-quitar-foto"), "Quitando…", () => estado.almacen.actualizarPersona(estado.perfil.user_id, { avatar_path: null }));
    await estado.almacen.borrarAvatar(anterior).catch(() => {});
    await refrescar(p);
    avisar("Se quitó la foto de perfil.", "info", { duracion: 2000 });
  } catch (e) { avisar(traducirError(e).message, "error"); }
}

const claveValida = (c) => c.length >= 10 && /[A-Za-z]/.test(c) && /\d/.test(c);
async function cambiarContrasena(ev) {
  ev.preventDefault();
  const c1 = $("clave1").value, c2 = $("clave2").value;
  if (marcar("c-clave1", !claveValida(c1)) | marcar("c-clave2", c1 !== c2)) return;
  $("clave-error").hidden = true;
  try {
    await conEspera($("clave-guardar"), "Guardando…", () => estado.almacen.cambiarContrasena(c1));
    $("form-clave").reset();
    avisar("Contraseña actualizada.", "exito", { duracion: 2500 });
  } catch (e) { $("clave-error").textContent = traducirError(e).message; $("clave-error").hidden = false; }
}

export function iniciarPerfil() {
  $("form-perfil").addEventListener("submit", guardarDatos);
  $("form-perfil").addEventListener("input", (ev) => { $("form-perfil").dataset.sucio = "si"; ev.target.closest("[data-error]")?.removeAttribute("data-error"); });
  $("form-perfil").addEventListener("reset", () => { delete $("form-perfil").dataset.sucio; setTimeout(pintarPerfil, 0); });
  $("p-foto").addEventListener("change", cambiarFoto);
  $("p-quitar-foto").addEventListener("click", quitarFoto);
  $("form-clave").addEventListener("submit", cambiarContrasena);
  $("form-clave").addEventListener("input", (ev) => ev.target.closest("[data-error]")?.removeAttribute("data-error"));
}
export { cargarEquipo };
