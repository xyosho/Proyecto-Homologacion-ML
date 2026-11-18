// Mapa de Google con la ruta y sus cifras (Maps JavaScript API + clase Route de la Routes API). Corre aislado en un
// marco (sandbox sin allow-same-origin): no ve la sesión ni los datos de la app. La app le envía por postMessage el
// origen, el destino y la clave pública; este marco dibuja la ruta y devuelve sus metros y segundos (con el tráfico de
// ahora, como Google Maps), así lo que se ve y lo que dice la app coinciden. Si algo falla, avisa y la app usa su mapa.
(() => {
  "use strict";
  const enviar = (m) => parent.postMessage(m, "*");              // el marco aislado no tiene origen propio
  let pedido = null, fallido = false;
  const fallo = (motivo) => { if (!fallido) { fallido = true; enviar({ tipo: "error", motivo }); } };

  // Clave sin la Maps JavaScript API habilitada o con otro dominio en sus restricciones
  window.gm_authFailure = () => fallo("la clave de Google Maps no tiene habilitada la Maps JavaScript API para este sitio");

  // Los demás problemas de la clave Google solo los escribe en la consola y pinta su cuadro de error en el mapa: se
  // detectan al momento, para pasar al otro mapa sin dejar ese cuadro a la vista y diciendo qué falta
  const ERRORES = {
    ApiNotActivatedMapError: "la Maps JavaScript API no está activada en el proyecto de la clave",
    ApiTargetBlockedMapError: "las restricciones de la clave no permiten la Maps JavaScript API",
    RefererNotAllowedMapError: "las restricciones de la clave no permiten este sitio",
    InvalidKeyMapError: "la clave de Google Maps no es válida",
    BillingNotEnabledMapError: "el proyecto de la clave no tiene la facturación activada",
  };
  const errorConsola = console.error.bind(console);
  console.error = (...args) => {
    const codigo = String(args[0] ?? "").match(/\b([A-Za-z]+MapError)\b/);
    if (codigo) fallo(ERRORES[codigo[1]] || `Google Maps respondió ${codigo[1]}`);
    errorConsola(...args);
  };
  const vigia = new MutationObserver(() => {
    if (document.querySelector("#mapa .gm-err-container")) { vigia.disconnect(); fallo("Google Maps mostró un error en el mapa"); }
  });
  vigia.observe(document.getElementById("mapa"), { childList: true, subtree: true });

  window.addEventListener("message", (ev) => {
    if (ev.source !== parent || pedido) return;
    const m = ev.data || {};
    const punto = (p) => p && Number.isFinite(p.lat) && Number.isFinite(p.lng);
    if (m.tipo !== "ruta" || !/^AIza[0-9A-Za-z_-]{35}$/.test(String(m.clave)) || !punto(m.origen) || !punto(m.destino)) return;
    pedido = m;
    const s = document.createElement("script");
    s.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(m.clave)}&v=weekly&loading=async&language=es&region=CO&callback=iniciarRuta`;
    s.async = true;
    s.onerror = () => fallo("no se pudo cargar Google Maps");
    document.head.append(s);
  });

  window.iniciarRuta = async () => {
    try {
      const [{ Map }, { Route }] = await Promise.all([google.maps.importLibrary("maps"), google.maps.importLibrary("routes")]);
      const mapa = new Map(document.getElementById("mapa"), { center: pedido.destino, zoom: 11, mapId: "DEMO_MAP_ID",
        mapTypeControl: false, streetViewControl: false, fullscreenControl: false, clickableIcons: false });
      const { routes } = await Route.computeRoutes({ origin: pedido.origen, destination: pedido.destino, travelMode: "DRIVING",
        routingPreference: "TRAFFIC_AWARE", language: "es", region: "co", fields: ["distanceMeters", "durationMillis", "path"] });
      const r = routes && routes[0];
      if (!r || !Number.isFinite(r.distanceMeters) || !Number.isFinite(r.durationMillis)) throw new Error("Google no encontró una ruta en carro");
      r.createPolylines().forEach((p) => { p.setOptions({ strokeColor: "#B5121B", strokeOpacity: 0.95, strokeWeight: 5 }); p.setMap(mapa); });
      (await r.createWaypointAdvancedMarkers()).forEach((mk) => { mk.map = mapa; });
      const limites = new google.maps.LatLngBounds();
      r.path.forEach((p) => limites.extend({ lat: p.lat, lng: p.lng }));
      mapa.fitBounds(limites, 28);
      // Las cifras solo se entregan si el mapa de Google de verdad se dibujó (con la Maps JavaScript API apagada, la
      // ruta sí llega pero el mapa sale en error): así la app nunca muestra cifras de Google sobre un mapa roto
      await new Promise((listo, mal) => {
        const espera = setTimeout(() => mal(new Error("el mapa de Google no terminó de cargar")), 10000);
        google.maps.event.addListenerOnce(mapa, "tilesloaded", () => { clearTimeout(espera); listo(); });
      });
      if (fallido) return;
      vigia.disconnect();
      enviar({ tipo: "ruta", metros: r.distanceMeters, segundos: r.durationMillis / 1000 });
    } catch (e) {
      fallo(e && e.message ? e.message.slice(0, 160) : "Google Maps no respondió");
    }
  };

  enviar({ tipo: "listo" });
})();
