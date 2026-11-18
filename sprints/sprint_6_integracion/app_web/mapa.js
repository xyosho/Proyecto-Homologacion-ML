// Ruta al campus en la ficha del aspirante, en el registro del asesor y en la encuesta: mapa con la ruta por calles desde
// su dirección (punto de partida) hasta la Universidad (punto de llegada) y la distancia y el tiempo en carro.
//   - Con GOOGLE_MAPS_KEY (variable de Vercel): mapa de Google con su ruta y SUS km y minutos (Maps JavaScript API y
//     Routes API), en un marco aislado (ruta-google.html). Lo que se ve y las cifras salen de la misma ruta.
//   - Si Google no responde (clave sin esas APIs, sin red): mapa de OpenStreetMap (Leaflet) con la ruta de OSRM y SUS
//     cifras. Nunca se mezcla el mapa de un servicio con las cifras de otro.
//   - Siempre: botón para abrir la misma ruta en Google Maps.
// A los servicios externos se envía la coordenada redondeada a ~100 m (3 decimales), no la placa exacta.
import { $, el, icono, km } from "./ui.js";
import { estado, ubicacionDe } from "./datos.js";

const LEAFLET = {
  js: { src: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js",
    integrity: "sha512-puJW3E/qXDqYp9IfhAI54BJEaWIfloJ7JWs7OeD5i6ruC9JZL1gERT1wjtwXFlh7CjE7ZJ+/vcRZRkIYIb6p4g==" },
  css: { href: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css",
    integrity: "sha512-h9FcoyWjHcOcmEVkxOfTLnmZFWIH0iZhZT1H2TbOq55xssQGEJHEaIm+PgoUaZbRvQTNTluNOEfb1ZRy6D3BOw==" },
};
const OSRM = "https://router.project-osrm.org/route/v1/driving";
const redondear = (v) => Math.round(v * 1000) / 1000;

let promesaLeaflet = null;
function cargarLeaflet() {
  if (window.L) return Promise.resolve(window.L);
  if (promesaLeaflet) return promesaLeaflet;
  promesaLeaflet = new Promise((resolver, rechazar) => {
    const css = Object.assign(document.createElement("link"), { rel: "stylesheet", href: LEAFLET.css.href, integrity: LEAFLET.css.integrity, crossOrigin: "anonymous" });
    const js = Object.assign(document.createElement("script"), { src: LEAFLET.js.src, integrity: LEAFLET.js.integrity, crossOrigin: "anonymous" });
    js.onload = () => resolver(window.L);
    js.onerror = () => { promesaLeaflet = null; rechazar(new Error("no se pudo cargar el mapa")); };
    document.head.append(css, js);
  });
  return promesaLeaflet;
}

// Punto de partida: la placa de Catastro si la hay; si no, el centro de la localidad o municipio
export function origenDe(a) {
  if (a.lat != null && a.lon != null) {
    return { lat: a.lat, lon: a.lon, texto: a.ubicada_con === "CATASTRO" ? "la dirección del aspirante (placa de Catastro)" : `el centro de ${a.ubicacion}` };
  }
  const u = ubicacionDe(a.ubicacion);
  return u ? { lat: u.lat, lon: u.lon, texto: `el centro de ${u.nombre} (aproximado)` } : null;
}
export function enlaceGoogle(o) {
  const c = estado.modelo.reglas.campus;
  return `https://www.google.com/maps/dir/?api=1&origin=${redondear(o.lat)},${redondear(o.lon)}&destination=${c.lat},${c.lon}&travelmode=driving`;
}

const memoria = new Map();
export function calcularRuta(o) {
  const c = estado.modelo.reglas.campus, clave = `${redondear(o.lat)},${redondear(o.lon)}`;
  if (!memoria.has(clave)) {
    const control = new AbortController(), t = setTimeout(() => control.abort(), 15000);
    const promesa = fetch(`${OSRM}/${redondear(o.lon)},${redondear(o.lat)};${c.lon},${c.lat}?overview=full&geometries=geojson`, { signal: control.signal })
      .then((r) => { if (!r.ok) throw new Error(`el servicio de rutas respondió ${r.status}`); return r.json(); })
      .then((d) => {
        if (d.code !== "Ok" || !d.routes?.length) throw new Error("no se encontró una ruta por calles");
        const r = d.routes[0];
        return { km: r.distance / 1000, min: r.duration / 60, linea: r.geometry.coordinates.map(([lon, lat]) => [lat, lon]) };
      })
      .catch((e) => { memoria.delete(clave); throw e.name === "AbortError" ? new Error("el servicio de rutas no respondió a tiempo") : e; })
      .finally(() => clearTimeout(t));
    memoria.set(clave, promesa);
  }
  return memoria.get(clave);
}

// ---------------------------------------------------------------------------- dibujo
const minutos = (m) => (m < 60 ? `${Math.round(m)} min` : `${Math.floor(m / 60)} h ${String(Math.round(m % 60)).padStart(2, "0")} min`);

// Una tarjeta de ruta por vista, cada una con su propio mapa. Sus elementos llevan los mismos id con un prefijo ("" en
// la ficha y en la encuesta, "r-" en el registro del asesor), así abrir una ficha no le borra el mapa al registro.
export function tarjetaRuta(prefijo = "", { vacio = "Sin ubicación para trazar la ruta." } = {}) {
  const $p = (id) => $(`${prefijo}${id}`);
  let mapa = null, capa = null, limites = null, observador = null, turno = 0;
  // Antes de poner otro contenido en la caja: Leaflet no deja crear un mapa sobre un contenedor ya usado
  const quitarMapa = () => { observador?.disconnect(); observador = null; if (mapa) { mapa.remove(); mapa = null; capa = null; } };
  // Encuadra la ruta completa; se repite cuando la caja cambia de tamaño (la vista estaba oculta, giro del celular)
  const encuadrar = () => { if (mapa && limites) { mapa.invalidateSize(); mapa.fitBounds(limites, { padding: [30, 30] }); } };

  async function mapaLeaflet(o, ruta) {
    const L = await cargarLeaflet(), c = estado.modelo.reglas.campus, caja = $p("mapa-ruta");
    if (!mapa) {
      caja.replaceChildren();
      mapa = L.map(caja, { scrollWheelZoom: false, zoomControl: true, attributionControl: true });
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, referrerPolicy: "strict-origin-when-cross-origin",
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> · ruta: OSRM' }).addTo(mapa);
      capa = L.layerGroup().addTo(mapa);
      observador = new ResizeObserver(() => encuadrar());
      observador.observe(caja);
    }
    capa.clearLayers();
    const inicio = [o.lat, o.lon], fin = [c.lat, c.lon];
    if (ruta) {
      L.polyline(ruta.linea, { color: "#FFFFFF", weight: 9, opacity: 0.9 }).addTo(capa);
      L.polyline(ruta.linea, { color: "#B5121B", weight: 5, opacity: 0.95 }).addTo(capa);
    } else {
      L.polyline([inicio, fin], { color: "#791734", weight: 3, dashArray: "6 8", opacity: 0.8 }).addTo(capa);
    }
    const pin = (clase) => L.divIcon({ className: `pin-mapa ${clase}`, html: "<span></span>", iconSize: [26, 26], iconAnchor: [13, 13] });
    L.marker(inicio, { icon: pin("pin-aspirante"), title: "Aspirante", alt: "Punto de partida: aspirante" }).bindTooltip("Aspirante", { direction: "top", offset: [0, -10] }).addTo(capa);
    L.marker(fin, { icon: pin("pin-campus"), title: "Campus Unicervantes", alt: "Llegada: campus Unicervantes" }).bindTooltip("Campus Unicervantes", { direction: "top", offset: [0, -10] }).addTo(capa);
    limites = L.latLngBounds(ruta ? ruta.linea : [inicio, fin]).extend(inicio).extend(fin);
    encuadrar();
  }

  // Google: el marco aislado dibuja la ruta y responde con sus metros y segundos (o con el motivo si falla)
  function rutaGoogle(o) {
    return new Promise((resolver, rechazar) => {
      quitarMapa();
      const c = estado.modelo.reglas.campus;
      const marco = el("iframe", { src: "/ruta-google.html", title: "Mapa de Google con la ruta al campus",
        sandbox: "allow-scripts allow-popups allow-popups-to-escape-sandbox", referrerpolicy: "strict-origin-when-cross-origin" });
      const terminar = (fn, v) => { clearTimeout(espera); window.removeEventListener("message", oir); fn(v); };
      const oir = (ev) => {
        if (ev.source !== marco.contentWindow) return;
        const m = ev.data || {};
        if (m.tipo === "listo") {
          marco.contentWindow.postMessage({ tipo: "ruta", clave: estado.googleMapsKey, origen: { lat: redondear(o.lat), lng: redondear(o.lon) },
            destino: { lat: c.lat, lng: c.lon } }, "*");              // el marco aislado no tiene origen propio
        } else if (m.tipo === "ruta" && Number.isFinite(m.metros) && Number.isFinite(m.segundos)) {
          terminar(resolver, { km: m.metros / 1000, min: m.segundos / 60 });
        } else if (m.tipo === "error") {
          terminar(rechazar, new Error(String(m.motivo || "Google Maps no respondió").slice(0, 160)));
        }
      };
      const espera = setTimeout(() => terminar(rechazar, new Error("Google Maps no respondió a tiempo")), 15000);
      window.addEventListener("message", oir);
      $p("mapa-ruta").replaceChildren(marco);
    });
  }

  function pintarFuente(fuente) {
    const nota = $p("ruta-fuente"), leyenda = $p("mapa-ruta")?.closest(".tarjeta")?.querySelector(".leyenda-ruta");
    if (leyenda) leyenda.hidden = fuente === "google";             // Google marca la partida con A y el campus con B
    if (!nota) return;
    nota.hidden = !fuente;
    nota.textContent = fuente === "google" ? "Ruta, distancia y tiempo de Google Maps, con el tráfico de este momento (A: partida · B: campus)."
      : "Ruta, distancia y tiempo calculados con OpenStreetMap (OSRM), sin contar el tráfico. Para ver el tráfico, ábrala en Google Maps.";
  }

  // Pinta la tarjeta; si se puede, guarda la distancia por calles en Supabase (una vez por aspirante)
  return async function pintarRuta(a, { guardar = null } = {}) {
    const mio = ++turno, o = origenDe(a);
    $p("ruta-estado").hidden = true;
    pintarFuente(null);
    if (!o) {
      quitarMapa();
      $p("mapa-ruta").replaceChildren(el("div", { class: "mapa-vacio" }, icono("pin", "ic vacio-icono"), el("p", { text: vacio })));
      $p("ruta-km").textContent = "—"; $p("ruta-min").textContent = "—"; $p("ruta-google").hidden = true; $p("ruta-origen").textContent = "";
      return;
    }
    $p("ruta-google").hidden = false; $p("ruta-google").href = enlaceGoogle(o);
    $p("ruta-origen").textContent = `Desde ${o.texto} hasta el campus (Calle 209, vía Arrayanes).`;
    const guardada = a.distancia_ruta_km != null;
    $p("ruta-km").textContent = guardada ? km(a.distancia_ruta_km) : "…";
    $p("ruta-min").textContent = guardada ? minutos(a.duracion_ruta_min) : "…";
    let ruta = null, fuente = null;
    if (estado.googleMapsKey) {
      try { ruta = await rutaGoogle(o); fuente = "google"; }
      catch (e) { console.warn(`Google Maps: ${e.message}. Se usa OpenStreetMap.`); }
      if (mio !== turno) return;
    }
    if (!ruta) {
      try { ruta = await calcularRuta(o); fuente = "osrm"; }
      catch (e) {
        if (mio !== turno) return;
        $p("ruta-estado").hidden = false;
        $p("ruta-estado").replaceChildren(icono("alerta"), el("span", { text: `No se pudo calcular la ruta por calles (${e.message}). Ábrala en Google Maps.` }));
        if (!guardada) { $p("ruta-km").textContent = "—"; $p("ruta-min").textContent = "—"; }
      }
      if (mio !== turno) return;
      try { await mapaLeaflet(o, ruta); }
      catch (e) {
        if (mio === turno) { quitarMapa(); $p("mapa-ruta").replaceChildren(el("div", { class: "mapa-vacio" }, icono("alerta", "ic vacio-icono"), el("p", { text: `No se pudo mostrar el mapa (${e.message}).` }))); }
      }
    }
    if (mio !== turno) return;
    if (ruta) { $p("ruta-km").textContent = km(ruta.km); $p("ruta-min").textContent = minutos(ruta.min); pintarFuente(fuente); }
    if (ruta && guardar && (!guardada || Math.abs(a.distancia_ruta_km - ruta.km) > 0.05 || Math.abs(a.duracion_ruta_min - ruta.min) > 1)) {
      try { await guardar({ distancia_ruta_km: Math.round(ruta.km * 100) / 100, duracion_ruta_min: Math.round(ruta.min * 10) / 10, ruta_calculada_en: new Date().toISOString() }); }
      catch (e) { console.error(e); }
    }
  };
}

// La ficha del aspirante y la encuesta: cada página tiene una sola tarjeta, sin prefijo
export const pintarRuta = tarjetaRuta();
