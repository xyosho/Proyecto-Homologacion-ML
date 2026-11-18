// Tarea programada de Vercel (vercel.json → "crons"): todos los días a las 8:00 a. m. de Colombia (13:00 UTC) hace una
// consulta mínima a Supabase. En el plan gratuito, Supabase pausa el proyecto si pasa 7 días sin actividad, y con el
// proyecto pausado la app no puede iniciar sesión ni guardar aspirantes; esta consulta diaria lo mantiene activo.
// Solo lee 1 fila de la tabla prediccion (de solo lectura) con la clave PUBLICABLE, la misma que ya va en el navegador.
// No escribe nada ni usa la clave secreta. Si el proyecto de Vercel tiene CRON_SECRET, Vercel la envía en la cabecera
// Authorization y aquí se exige; sin ella, la ruta solo hace esa lectura pública.
const TABLA = "prediccion?select=inscripcion_id&limit=1";

module.exports = async (req, res) => {
  res.setHeader("Cache-Control", "no-store");
  const secreto = process.env.CRON_SECRET;
  if (secreto && req.headers.authorization !== `Bearer ${secreto}`) {
    res.status(401).json({ ok: false, error: "No autorizado" });
    return;
  }
  const primero = (...nombres) => nombres.map((n) => (process.env[n] || "").trim()).find(Boolean) || "";
  const url = primero("SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL").replace(/\/$/, "");
  const clave = primero("SUPABASE_KEY", "SUPABASE_PUBLISHABLE_KEY", "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY",
    "SUPABASE_ANON_KEY", "NEXT_PUBLIC_SUPABASE_ANON_KEY");
  if (!/^https:\/\/[a-z0-9]+\.supabase\.co$/.test(url) || !clave) {
    res.status(500).json({ ok: false, error: "Faltan SUPABASE_URL y SUPABASE_KEY en las variables de entorno de Vercel" });
    return;
  }
  if (clave.startsWith("sb_secret_")) {
    res.status(500).json({ ok: false, error: "SUPABASE_KEY debe ser la clave publicable, nunca la secreta" });
    return;
  }
  const inicio = Date.now();
  try {
    const r = await fetch(`${url}/rest/v1/${TABLA}`, { headers: { apikey: clave, Accept: "application/json" } });
    const filas = r.ok ? (await r.json()).length : 0;
    res.status(r.ok ? 200 : 502).json({ ok: r.ok, supabase: r.status, filas, ms: Date.now() - inicio, fecha: new Date().toISOString() });
  } catch (e) {
    res.status(502).json({ ok: false, error: `Supabase no respondió: ${e.message}`, fecha: new Date().toISOString() });
  }
};
