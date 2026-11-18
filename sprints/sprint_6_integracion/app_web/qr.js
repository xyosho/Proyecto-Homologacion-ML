// Código QR de un enlace listo para enviar: el aspirante lo escanea con la cámara del celular (en una feria, en el
// colegio o frente al asesor) o el asesor descarga la imagen para mandarla por WhatsApp o imprimirla.
// La matriz la calcula qrcode-generator (cdnjs, licencia MIT) aquí mismo, en el navegador: el enlace no se envía a
// ningún servicio externo. Corrección de errores M (15%): se lee bien aunque la imagen quede algo borrosa.
import { el, icono, avisar } from "./ui.js";

const SVG = "http://www.w3.org/2000/svg";
const MARGEN = 4;                                     // zona en blanco de 4 módulos que pide la norma del QR

function matriz(texto) {
  if (typeof window.qrcode !== "function") return null;      // la librería no cargó (sin red o bloqueada)
  const q = window.qrcode(0, "M");                            // 0 = la versión más pequeña en la que cabe el enlace
  q.addData(texto, "Byte");
  q.make();
  const n = q.getModuleCount(), m = [];
  for (let f = 0; f < n; f++) { m.push([]); for (let c = 0; c < n; c++) m[f].push(q.isDark(f, c)); }
  return m;
}

// El QR como SVG: un solo trazo con un cuadro por módulo oscuro, nítido a cualquier tamaño
function dibujarSVG(m, descripcion) {
  const n = m.length, lado = n + 2 * MARGEN;
  let d = "";
  m.forEach((fila, f) => fila.forEach((oscuro, c) => { if (oscuro) d += `M${c + MARGEN} ${f + MARGEN}h1v1h-1z`; }));
  const s = document.createElementNS(SVG, "svg");
  s.setAttribute("viewBox", `0 0 ${lado} ${lado}`); s.setAttribute("class", "qr-imagen");
  s.setAttribute("role", "img"); s.setAttribute("aria-label", descripcion); s.setAttribute("shape-rendering", "crispEdges");
  const fondo = document.createElementNS(SVG, "rect");
  fondo.setAttribute("width", lado); fondo.setAttribute("height", lado); fondo.setAttribute("fill", "#FFFFFF");
  const trazo = document.createElementNS(SVG, "path");
  trazo.setAttribute("d", d); trazo.setAttribute("fill", "#1A1A1A");
  s.append(fondo, trazo);
  return s;
}

// La imagen para descargar: PNG de unos 600 px con el título debajo, para enviarla o imprimirla
function descargarPNG(m, titulo, archivo) {
  const n = m.length, px = Math.max(8, Math.floor(600 / (n + 2 * MARGEN))), lado = (n + 2 * MARGEN) * px, pie = 64;
  const lienzo = document.createElement("canvas");
  lienzo.width = lado; lienzo.height = lado + pie;
  const g = lienzo.getContext("2d");
  g.fillStyle = "#FFFFFF"; g.fillRect(0, 0, lienzo.width, lienzo.height);
  g.fillStyle = "#1A1A1A";
  m.forEach((fila, f) => fila.forEach((oscuro, c) => { if (oscuro) g.fillRect((c + MARGEN) * px, (f + MARGEN) * px, px, px); }));
  g.fillStyle = "#791734"; g.textAlign = "center"; g.textBaseline = "middle";
  g.font = "700 24px 'Open Sans', Arial, sans-serif";
  g.fillText(titulo, lado / 2, lado + pie / 2 - 8, lado - 32);
  lienzo.toBlob((blob) => {
    if (!blob) { avisar("No se pudo crear la imagen del QR.", "error"); return; }
    const url = URL.createObjectURL(blob), a = el("a", { href: url, download: archivo });
    document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 4000);
    avisar("QR descargado. Envíelo por WhatsApp o imprímalo.", "exito", { duracion: 2500 });
  }, "image/png");
}

// Bloque con el QR, la instrucción y el botón para descargarlo. titulo: lo que se imprime bajo el QR descargado.
export function bloqueQR(url, { titulo = "Unicervantes · Admisiones", archivo = "qr-unicervantes.png" } = {}) {
  const m = matriz(url);
  if (!m) return el("p", { class: "nota", text: "No se pudo cargar el generador de códigos QR. Revise la conexión y recargue la página; mientras tanto, envíe el enlace." });
  return el("div", { class: "qr-bloque" },
    dibujarSVG(m, `Código QR del enlace ${url}`),
    el("div", { class: "qr-texto" },
      el("p", { class: "etiqueta" }, icono("qr"), " Código QR"),
      el("p", { class: "texto-suave", text: "El aspirante lo escanea con la cámara del celular y le abre el mismo enlace." }),
      el("button", { type: "button", class: "secundario", onclick: () => descargarPNG(m, titulo, archivo) }, icono("descargar"), "Descargar QR")));
}

// Botón que muestra u oculta el QR al final del elemento que contiene al botón (selector), p. ej. la fila del enlace
export function botonQR(url, selector, opciones) {
  let bloque = null;
  const b = el("button", { type: "button", class: "discreto", "aria-expanded": "false", onclick: () => {
    if (bloque) { bloque.remove(); bloque = null; b.setAttribute("aria-expanded", "false"); b.lastChild.textContent = "Código QR"; return; }
    bloque = bloqueQR(url, opciones);
    (b.closest(selector) || b.parentElement).append(bloque);
    b.setAttribute("aria-expanded", "true"); b.lastChild.textContent = "Ocultar QR";
  } }, icono("qr"), "Código QR");
  return b;
}

// Nombre de archivo seguro a partir del nombre del enlace o del aspirante
export const nombreArchivoQR = (prefijo, nombre) => `${prefijo}-${(nombre || "enlace").normalize("NFD").replace(/[̀-ͯ]/g, "")
  .toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 40) || "enlace"}.png`;
