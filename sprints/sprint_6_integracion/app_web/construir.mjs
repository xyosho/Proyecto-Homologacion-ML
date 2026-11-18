// Arma la carpeta publico/ que sirve Vercel: copia la app y escribe config.js con la URL y la clave PUBLICABLE de Supabase.
//   - En Vercel (build en la nube) las lee de las variables de entorno del proyecto: SUPABASE_URL y SUPABASE_KEY
//     (también acepta los nombres que crea la integración de Supabase: NEXT_PUBLIC_SUPABASE_URL,
//     SUPABASE_PUBLISHABLE_KEY, NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY, SUPABASE_ANON_KEY, NEXT_PUBLIC_SUPABASE_ANON_KEY).
//   - En este computador, si no están en el entorno, las lee del .env del proyecto.
// La clave publicable es visible en el navegador por diseño: RLS no le deja leer ni escribir los aspirantes.
// Rechaza cualquier clave secreta (sb_secret_ o service_role) y nunca usa SUPABASE_SERVICE_ROLE_KEY.
// Uso: node sprints/sprint_6_integracion/app_web/construir.mjs
import { cpSync, existsSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const AQUI = dirname(fileURLToPath(import.meta.url));
const RAIZ = join(AQUI, "..", "..", "..");
const SALIDA = process.env.CONSTRUIR_SALIDA || join(AQUI, "publico");          // otra carpeta solo para las pruebas
const ARCHIVOS = ["index.html", "404.html", "estilos.css", "app.js", "ui.js", "datos.js", "formulario.js", "analitica.js", "equipo.js", "perfil.js", "mapa.js", "encuestas.js", "qr.js", "modelo.js", "modelo.json",
  "encuesta.html", "encuesta.js", "encuesta.css", "ruta-google.html", "ruta-google.js",
  "psicologia.js", "psicologia.css", "vocacional.js", "entrevista.html", "entrevista.js", "entrevista.css",
  "logo_unicervantes.png", "icono_unicervantes.png"];
const EN_VERCEL = process.env.VERCEL === "1";

function leerEnv() {
  const ruta = join(RAIZ, ".env"), valores = {};
  if (!EN_VERCEL && existsSync(ruta)) {
    for (const linea of readFileSync(ruta, "utf8").split(/\r?\n/)) {
      const m = linea.match(/^\s*([A-Z_]+)\s*=\s*(.*?)\s*$/);
      if (m) valores[m[1]] = m[2].replace(/^["']|["']$/g, "");
    }
  }
  return valores;
}
const env = { ...leerEnv(), ...Object.fromEntries(Object.entries(process.env).filter(([, v]) => v)) };
const primero = (...nombres) => nombres.map((n) => env[n]).find(Boolean) || "";
const url = primero("SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL").trim();
const clave = primero("SUPABASE_KEY", "SUPABASE_PUBLISHABLE_KEY", "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "SUPABASE_ANON_KEY", "NEXT_PUBLIC_SUPABASE_ANON_KEY").trim();

function falla(texto) { console.error(`ERROR: ${texto}`); process.exit(1); }
if (!url || !clave) falla(EN_VERCEL
  ? "Faltan las variables de entorno en Vercel: SUPABASE_URL y SUPABASE_KEY (Settings → Environment Variables)."
  : "Faltan SUPABASE_URL y SUPABASE_KEY (en el .env del proyecto o en el entorno).");
const m = url.match(/^https:\/\/([a-z0-9]+)\.supabase\.co\/?$/);
if (!m) falla("SUPABASE_URL no es la URL de un proyecto (https://<ref>.supabase.co).");
if (clave.startsWith("sb_secret_")) falla("Esa es la clave SECRETA de Supabase: nunca va en una página web. Use la clave publicable (sb_publishable_…).");
if (!clave.startsWith("sb_publishable_")) {
  let rol = null;
  try { rol = JSON.parse(Buffer.from(clave.split(".")[1], "base64url").toString()).role; } catch { /* no es JWT */ }
  if (rol !== "anon") falla("SUPABASE_KEY debe ser la clave publicable (sb_publishable_…) o la anon heredada, nunca la service_role.");
}

// Opcional: clave de Google Maps (Embed API) para el mapa de la ruta en la ficha. Va al navegador por diseño (el iframe
// la lleva en la URL): en Google Cloud se restringe a la Maps Embed API y a los dominios de la app.
let google = primero("GOOGLE_MAPS_KEY", "NEXT_PUBLIC_GOOGLE_MAPS_KEY", "GOOGLE_MAPS_API_KEY").trim();
if (google && !/^AIza[0-9A-Za-z_-]{35}$/.test(google)) {
  console.warn("AVISO: GOOGLE_MAPS_KEY no parece una clave de Google (AIza…, 39 caracteres); el mapa usará OpenStreetMap.");
  google = "";
}

if (existsSync(SALIDA)) for (const f of readdirSync(SALIDA)) if (f !== ".vercel") rmSync(join(SALIDA, f), { recursive: true, force: true });
mkdirSync(SALIDA, { recursive: true });
for (const f of ARCHIVOS) cpSync(join(AQUI, f), join(SALIDA, f));
writeFileSync(join(SALIDA, "config.js"),
  `// Generado por construir.mjs. Clave PUBLICABLE: RLS solo deja trabajar al personal autorizado.\n`
  + `export const SUPABASE_URL = ${JSON.stringify(url.replace(/\/$/, ""))};\nexport const SUPABASE_KEY = ${JSON.stringify(clave)};\n`
  + `export const GOOGLE_MAPS_KEY = ${JSON.stringify(google)};\n`);
if (!EN_VERCEL) {
  // Despliegue de publico/ ya construida (vercel deploy publico): lleva las mismas cabeceras de seguridad que vercel.json
  const { headers, rewrites } = JSON.parse(readFileSync(join(AQUI, "vercel.json"), "utf8"));
  writeFileSync(join(SALIDA, "vercel.json"), JSON.stringify({ rewrites, headers }, null, 2));
  writeFileSync(join(SALIDA, ".vercelignore"), ".env*\n.gitignore\n");     // `vercel link` deja aquí un .env.local con un token
}
console.log(`Listo: publico/ (${ARCHIVOS.length + 1} archivos, Supabase ${m[1]}, mapa ${google ? "Google Maps" : "OpenStreetMap"}${EN_VERCEL ? ", build en Vercel" : ""}).`);
