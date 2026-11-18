// SPRINT 6 — El modelo del proyecto en JavaScript (para la app web en Vercel, sin servidor Python).
//
// Es una traducción línea a línea de src/prediccion.py, src/caracteristicas.py (columnas del Sprint 2),
// src/nlp_vocacion.py (puntaje vocacional que se lee en las respuestas de la entrevista), src/modelado.py
// (preparar_X) y src/explicabilidad.py (SHAP y razones en español). Los parámetros aprendidos vienen
// de modelo.json, que genera exportar_modelo.py. pruebas/verificar_modelo.mjs comprueba que da lo mismo que Python.
//
// Explicaciones (SHAP):
//   - regresión logística: contribución lineal = coeficiente × (valor − media de la muestra de referencia);
//   - Random Forest: valores de Shapley exactos por árbol, con la misma muestra de 100 casos del Sprint 4
//     (cada árbol usa como mucho 7 variables, así que se pueden recorrer todas las combinaciones).

export const CATASTRO = "https://serviciosgis.catastrobogota.gov.co/arcgis/rest/services";
const VIAS = { CALLE: "CL", CLL: "CL", CL: "CL", CARRERA: "KR", CRA: "KR", KRA: "KR", CR: "KR", KR: "KR",
  DIAGONAL: "DG", DG: "DG", TRANSVERSAL: "TV", TV: "TV", AC: "AC", AK: "AK" };
const NOMBRE_TIPO_COLEGIO = { OFICIAL: "público", PRIVADO: "privado", TECNICO: "técnico" };

// ---------------------------------------------------------------------------- redondeos iguales a Python
// numpy / pandas .round(d): rint(x · 10^d) / 10^d, con empate al par
function rint(x) {
  const f = Math.floor(x), d = x - f;
  return d === 0.5 ? (f % 2 === 0 ? f : f + 1) : Math.round(x);
}
export const npRound = (x, d) => rint(x * 10 ** d) / 10 ** d;

// round(x, d) y f"{x:.{d}f}" de Python: el decimal más cercano al valor binario exacto, empate al par
export function pyFixed(x, d) {
  const neg = x < 0, s = Math.abs(x).toFixed(Math.min(100, d + 60));   // expansión decimal exacta
  const [ent, frac = ""] = s.split(".");
  let cuerpo = ent + frac.slice(0, d);
  const resto = frac.slice(d);
  const sube = resto[0] > "5" || (resto[0] === "5" && (/[1-9]/.test(resto.slice(1)) || Number(cuerpo.at(-1)) % 2 === 1));
  if (sube) cuerpo = (BigInt(cuerpo) + 1n).toString().padStart(cuerpo.length, "0");
  const e = cuerpo.slice(0, cuerpo.length - d) || "0", f = cuerpo.slice(cuerpo.length - d);
  const txt = d ? `${e}.${f}` : e;
  return neg && Number(txt) !== 0 ? "-" + txt : txt;
}
export const pyRound = (x, d) => Number(pyFixed(x, d));
const titulo = (t) => t.toLowerCase().replace(/(^|[^a-záéíóúñü])([a-záéíóúñü])/g, (_, a, b) => a + b.toUpperCase());

// ---------------------------------------------------------------------------- direcciones de Bogotá (Catastro)
// 'Carrera 69B # 37A-35 Sur' -> ['KR 69B', '37A 35 S']: formato de la Placa Domiciliaria de Catastro Bogotá
export function direccionACatastro(texto) {
  let t = String(texto).toUpperCase().replaceAll("AVENIDA CALLE", "AC").replaceAll("AVENIDA CARRERA", "AK");
  t = t.replace(/\bN[O°º]\.?|#|-/g, " ").replaceAll("SUR", "S").replaceAll("ESTE", "E");
  const tokens = t.split(/\s+/).filter(Boolean);
  const error = () => new Error(`Dirección no reconocida: '${texto}'. Use el formato 'Calle 26 # 57-41'.`);
  if (tokens.length < 4 || !(tokens[0] in VIAS) || !/^\d/.test(tokens[1])) throw error();
  const sufijo = ["S", "E"].includes(tokens.at(-1)) ? " " + tokens.pop() : "";
  const resto = tokens.slice(1, -1);
  let i = 1;                                       // vía | cruce: el cruce empieza en el siguiente token con dígito
  while (i < resto.length && !/^\d/.test(resto[i])) i++;
  const via = resto.slice(0, i), cruce = resto.slice(i);
  if (!cruce.length || !/^\d+$/.test(tokens.at(-1))) throw error();
  const viaTxt = via[0] + via.slice(1).map((x) => (["S", "E"].includes(x) || (x.length === 1 && x !== "BIS") ? " " + x : x)).join("");
  return [`${VIAS[tokens[0]]} ${viaTxt}`, `${cruce.join(" ")} ${tokens.at(-1)}${sufijo}`];
}

// Coordenada y código de localidad de una dirección de Bogotá con los servicios abiertos de Catastro (UAECD)
export async function ubicarEnBogota(direccion, fetchFn = fetch) {
  const [via, placa] = direccionACatastro(direccion);
  const avenida = { CL: "AC", KR: "AK" }[via.split(" ")[0]];      // "Calle 26" suele estar como "Avenida Calle 26"
  const vias = [via, ...(avenida ? [`${avenida} ${via.split(" ").slice(1).join(" ")}`] : [])];
  const consultar = async (ruta, params) => {
    const r = await fetchFn(`${CATASTRO}/${ruta}/query?${new URLSearchParams({ ...params, f: "json" })}`);
    if (!r.ok) throw new Error(`Catastro respondió ${r.status}`);
    return r.json();
  };
  let r = null;
  for (const v of vias) {
    r = await consultar("catastro/placadomiciliaria/MapServer/0", { where: `PDONVIAL='${v}' AND PDOTEXTO='${placa}'`,
      outFields: "PDONVIAL", returnGeometry: "true", outSR: "4326" });
    if (r.features && r.features.length) break;
  }
  if (!r || !r.features || !r.features.length) throw new Error(`Catastro no tiene la placa '${via} ${placa}'. Revise la dirección.`);
  const p = r.features[0].geometry;
  const loc = await consultar("ordenamientoterritorial/localidad/MapServer/0", { geometry: `${p.x},${p.y}`,
    geometryType: "esriGeometryPoint", inSR: "4326", spatialRel: "esriSpatialRelIntersects", outFields: "LOCCODIGO",
    returnGeometry: "false" });
  return { lat: Number(p.y), lon: Number(p.x), localidad: Number(loc.features[0].attributes.LOCCODIGO) };
}

// ---------------------------------------------------------------------------- NLP de la entrevista (Sprint 2)
// nlp_vocacion.analizar: minúsculas y sin tildes, se parte en frases, se quitan las palabras vacías y se forman palabras
// y pares de palabras DENTRO de cada frase (un par nunca mezcla dos respuestas).
export function analizar(texto, vacias, ngramas = [1, 2]) {
  const t = String(texto).toLowerCase().normalize("NFKD").replace(/\p{M}/gu, "");
  const salida = [];
  for (const frase of t.split(/[.;:!?¡¿]+/)) {
    const palabras = (frase.match(/[\p{L}\p{N}_]{2,}/gu) || []).filter((w) => !vacias.has(w));
    for (let n = ngramas[0]; n <= ngramas[1]; n++)
      for (let i = 0; i + n <= palabras.length; i++) salida.push(palabras.slice(i, i + n).join(" "));
  }
  return salida;
}

// prediccion.textos_entrevista: las respuestas abiertas unidas por sección (cada respuesta termina en punto)
export const SECCIONES_ENTREVISTA = ["texto_interes_programa", "texto_historia_vida", "texto_interes_universidad"];
export function textosEntrevista(respuestas) {
  const salida = {};
  for (const col of SECCIONES_ENTREVISTA) {
    const partes = ((respuestas || {})[col] || []).map((x) => String(x).trim()).filter(Boolean);
    salida[col] = partes.map((x) => (".;:!?".includes(x.at(-1)) ? x : x + ".")).join(" ") || null;
  }
  return salida;
}

// ---------------------------------------------------------------------------- el modelo
export function crearModelo(M) {
  const R = M.reglas, ref = M.referencias;

  // Distancia al campus en línea recta (Haversine) y por vías (tramo norte-sur + tramo oriente-occidente, S-44)
  function distancias(lat, lon) {
    const r = 6371.0, rad = Math.PI / 180;
    const p1 = lat * rad, p2 = R.campus.lat * rad, dp = p2 - p1, dl = (R.campus.lon - lon) * rad;
    const a = Math.sin(dp / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) ** 2;
    return [2 * r * Math.asin(Math.sqrt(a)), r * Math.abs(dp) + r * Math.abs(dl) * Math.cos((p1 + p2) / 2)];
  }

  // Regla institucional: Saber 11 si el global es >= 310; si no, Mi Vocación con entrevista y puntaje >= 3
  function becaQueAplica(global, entrevista, vocacional) {
    if (global >= R.umbral_icfes) return "SABER_11";
    if (entrevista && vocacional !== null && vocacional !== undefined && vocacional >= R.puntaje_vocacional_minimo) return "MI_VOCACION";
    return "NINGUNA";
  }

  // prediccion.puntaje_entrevista: puntaje vocacional de 1 a 5 que da la psicóloga (vacío si no hubo entrevista)
  function puntajeEntrevista(entrevista, vocacional) {
    if (!entrevista) return null;
    const v = Math.trunc(Number(vocacional));
    if (!(v >= 1 && v <= 5)) throw new Error("El puntaje vocacional de la entrevista va de 1 a 5.");
    return v;
  }

  // Modelo NLP (TF-IDF por sección con tf sublineal y norma L2 + Ridge), como nlp_vocacion.puntuar
  const N = M.nlp, vacias = new Set(N.palabras_vacias);
  const indices = N.secciones.map((s) => new Map(s.terminos.map((term, j) => [term, j])));
  function puntajeNLPTextos(textos) {
    if (N.secciones.some((s) => !textos[s.columna])) return null;        // con_texto: las tres secciones
    let y = N.intercepto;
    N.secciones.forEach((s, k) => {
      const cuenta = new Map();
      for (const term of analizar(textos[s.columna], vacias, N.ngramas)) {
        const j = indices[k].get(term);
        if (j !== undefined) cuenta.set(j, (cuenta.get(j) || 0) + 1);
      }
      const v = [...cuenta].map(([j, c]) => [j, (s.sublineal ? 1 + Math.log(c) : c) * s.idf[j]]);
      const norma = Math.sqrt(v.reduce((a, [, x]) => a + x * x, 0));
      if (norma > 0) for (const [j, x] of v) y += (x / norma) * s.pesos[j];
    });
    return npRound(Math.min(N.maximo, Math.max(N.minimo, y)), N.decimales);
  }
  // Para la app: puntaje NLP directo de las respuestas por pregunta ({texto_interes_programa: [...], ...})
  const puntajeNLP = (respuestas) => puntajeNLPTextos(textosEntrevista(respuestas));

  function tipoColegioCodigo(v) {
    const t = String(v).trim().toUpperCase().replaceAll("Ú", "U").replaceAll("É", "E");
    return t === "PUBLICO" ? "OFICIAL" : t;
  }

  // prediccion.descuento_institucional: un solo descuento por persona (familiar, egresado o personal 5/10/15%)
  function descuentoInstitucional(tipo, pct) {
    if (tipo === null || tipo === undefined) return 0.0;
    const t = R.descuentos.tipos[tipo];
    if (!t) throw new Error(`Descuento no válido: ${tipo}.`);
    const v = pct === null || pct === undefined ? t.pct[0] : Number(pct);
    if (!t.pct.some((o) => Math.abs(v - o) < 1e-9)) throw new Error(`El descuento ${t.nombre} no puede ser de ${v}.`);
    return v;
  }
  // prediccion.elegible_icetex: Plan Talento STEM, Saber 11 >= mérito mínimo del municipio del colegio
  function elegibleIcetex(puntaje, municipio) {
    const m = R.icetex.merito_minimo[String(municipio).toUpperCase()];
    return m !== undefined && puntaje >= m;
  }

  // prediccion.completar: una fila con las columnas de dataset_matricula
  function completar(entrada) {
    const e = { ...R.defectos };
    for (const [k, v] of Object.entries(entrada)) if (v !== null && v !== undefined) e[k] = v;
    e.tipo_colegio = tipoColegioCodigo(e.tipo_colegio);
    if (e.punt_global === undefined || e.estrato === undefined) throw new Error("Faltan datos obligatorios: puntaje ICFES y estrato.");
    if (!["AD", "SSIA"].includes(e.programa) || !R.canales.includes(e.canal) || !(e.tipo_colegio in NOMBRE_TIPO_COLEGIO))
      throw new Error("Programa, canal o tipo de colegio no válido.");
    const g = Math.trunc(Number(e.punt_global)), est = Math.trunc(Number(e.estrato));
    if (!(g >= 0 && g <= 500) || !(est >= 1 && est <= 6))
      throw new Error("Valores fuera de rango: ICFES 0-500, estrato 1-6.");
    const u = M.ubicaciones.find((x) => x.nombre.toLowerCase() === String(e.ubicacion).toLowerCase());
    if (!u) throw new Error(`Ubicación desconocida: ${e.ubicacion}.`);
    let { lat, lon } = e, origen;
    if (lat === undefined || lon === undefined) { lat = u.lat; lon = u.lon; origen = `el centro de ${u.nombre}`; }
    else origen = e.direccion || `la coordenada (${pyFixed(Number(lat), 5)}, ${pyFixed(Number(lon), 5)})`;
    const [recta, vial] = distancias(Number(lat), Number(lon));
    const entrevista = Boolean(e.entrevista);
    const vocacional = puntajeEntrevista(entrevista, e.puntaje_vocacional);      // Mi Vocación exige >= 3
    const textos = textosEntrevista(entrevista ? e.respuestas_entrevista : null);
    const beca = e.beca === "auto" ? becaQueAplica(g, entrevista, vocacional) : e.beca;
    const bruto = R.tarifas[e.programa][e.periodo.slice(0, 4)];
    const desc = descuentoInstitucional(e.tipo_descuento, e.pct_descuento_adicional);
    const pct = pyRound(Math.min(R.becas[beca].pct_primer + desc, R.descuentos.tope), 4);   // beca + descuento, tope del 50%
    const icetex = elegibleIcetex(g, e.municipio_colegio || u.municipio);           // sin dato: el municipio donde vive
    const elegible = R.fondos_municipales.includes(u.ubicacion_id);
    return {
      periodo: e.periodo, programa: e.programa, genero: e.genero, edad_al_inscribirse: Math.trunc(Number(e.edad)), estrato: est,
      regimen_salud: e.regimen_salud || (est === 1 ? "SUBSIDIADO" : "CONTRIBUTIVO"), tipo_ubicacion: u.tipo,
      distancia_campus_km: pyRound(recta, 2), distancia_vial_km: pyRound(vial, 2), origen_distancia: origen,
      ubicacion_nombre: u.nombre, ubicacion_id: u.ubicacion_id, canal: e.canal,
      captado_en_evento: Number(["EXPOESTUDIANTES", "CAMPUS_DAY"].includes(e.canal)),
      dias_registro_a_inscripcion: Math.trunc(Number(e.dias_registro_a_inscripcion)),
      contactos_antes_de_inscribirse: Math.trunc(Number(e.contactos_antes_de_inscribirse)),
      colegio_naturaleza: e.tipo_colegio === "PRIVADO" ? "PRIVADO" : "OFICIAL", tipo_colegio: e.tipo_colegio,
      colegio_en_convenio: Number(e.canal === "COLEGIO_CONVENIO"), anios_desde_saber11: Math.trunc(Number(e.anios_desde_saber11)),
      punt_global: g,
      entrevista_realizada: Number(entrevista), puntaje_vocacional: vocacional,
      cumple_req_saber11: Number(g >= R.umbral_icfes),
      cumple_req_mi_vocacion: Number(entrevista && vocacional !== null && vocacional >= R.puntaje_vocacional_minimo),
      beca, tipo_descuento: e.tipo_descuento ?? null, pct_descuento_adicional: desc,
      pct_descuento_inicial: pct, valor_semestre_bruto: bruto, valor_neto_primer_semestre: rint(bruto * (1 - pct)),
      elegible_foes: Number(elegible), apoyo_foes: Number(Boolean(e.apoyo_foes) && elegible),
      elegible_icetex: Number(icetex), aplica_icetex: Number(Boolean(e.solicita_icetex) && icetex),
      ...textos,
    };
  }

  // caracteristicas.construir_caracteristicas: las columnas nuevas del Sprint 2
  function construir(f) {
    const d = { ...f };
    const banda = R.bandas_icfes.find((b) => d.punt_global >= b.desde && d.punt_global < b.hasta);
    d.segmento_rendimiento_icfes = banda ? banda.segmento : "nan";
    d.log_distancia = Math.log(Math.max(d.distancia_vial_km, 0.5));   // piso de 0,5 km: un vecino del campus no da −∞
    d.colegio_privado = Number(d.colegio_naturaleza === "PRIVADO");
    d.tiene_descuento = Number(d.tipo_descuento !== null && d.tipo_descuento !== undefined);   // ya conoce la Universidad
    const km = ref.kmeans;
    const z = km.variables.map((v, j) => (d[v] - km.medias[j]) / km.desv[j]);
    let mejor = 0, dmin = Infinity;
    km.centros.forEach((c, k) => {
      const dist = c.reduce((s, cj, j) => s + (z[j] - cj) ** 2, 0);
      if (dist < dmin) { dmin = dist; mejor = k; }
    });
    d.segmento_mercado = km.nombres[km.posicion[String(mejor)]];
    d.puntaje_vocacional_nlp = puntajeNLPTextos(d);
    return d;
  }

  // prediccion.puntaje_nlp: el dado (calculado antes), el de las respuestas, o el de la psicóloga si no hay respuestas
  function conNLP(d, fila, entrada) {
    const dado = entrada.puntaje_vocacional_nlp;
    if (dado !== null && dado !== undefined) return { ...d, puntaje_vocacional_nlp: pyRound(Math.min(5, Math.max(1, Number(dado))), 3) };
    if (d.puntaje_vocacional_nlp === null && fila.entrevista_realizada === 1) return { ...d, puntaje_vocacional_nlp: Number(fila.puntaje_vocacional) };
    return d;
  }

  // modelado.preparar_X + ColumnTransformer: vector de entrada del modelo y nombre de la variable original de cada columna
  function preparar(d, P) {
    const [mg, sg] = ref.estandarizacion.punt_global;
    const x = { ...d, puntaje_vocacional: d.puntaje_vocacional ?? 0,                          // 0 = sin entrevista
      puntaje_vocacional_nlp: d.puntaje_vocacional_nlp ?? 0, icfes_al_cuadrado: ((d.punt_global - mg) / sg) ** 2, semestre_2: Number(d.periodo.endsWith("-2")) };
    const t = [], origen = [], fila = {};          // fila: solo las columnas del modelo (como X en Python)
    for (const c of [...P.numericas, ...P.categoricas]) fila[c] = x[c];
    P.numericas.forEach((c, j) => {
      t.push(P.media ? (Number(x[c]) - P.media[j]) / P.escala[j] : Number(x[c])); origen.push(c);
    });
    P.categoricas.forEach((c, j) => P.categorias[j].forEach((cat) => { t.push(Number(String(x[c]) === cat)); origen.push(c); }));
    return { t, origen, fila };
  }

  // El modelo que eligió el Sprint 3 para cada objetivo: regresión logística o Random Forest
  const sigmoide = (z) => 1 / (1 + Math.exp(-z));
  const esArboles = (m) => Array.isArray(m.arboles);
  function probModelo(m, t) {
    return esArboles(m) ? m.arboles.reduce((s, a) => s + hoja(a, (j) => f32(t[j])), 0) / m.arboles.length
      : sigmoide(t.reduce((s, v, j) => s + v * m.coef[j], m.intercepto));
  }
  // Valores SHAP: lineales (exactos) para la logística; por árbol para el Random Forest (como el Sprint 4)
  function shapModelo(m, t) {
    return esArboles(m) ? shapArboles(m, t) : t.map((v, j) => m.coef[j] * (v - m.fondo_media[j]));
  }
  function probMatricula(d) { return probModelo(M.matricula, preparar(d, M.matricula).t); }

  // Random Forest: probabilidad = promedio de los árboles (sklearn compara en float32)
  const f32 = Math.fround;
  function hoja(a, valor) {
    let n = 0;
    while (a.izquierda[n] !== -1) n = valor(a.variable[n]) <= a.umbral[n] ? a.izquierda[n] : a.derecha[n];
    return a.valor[n];
  }

  // Valores de Shapley exactos por árbol (intervencionales: las variables ausentes toman el valor del caso de referencia)
  const factorial = [1]; for (let i = 1; i <= 16; i++) factorial[i] = factorial[i - 1] * i;
  function shapArboles(m, t) {
    const fondo = m.fondo, phi = new Array(t.length).fill(0);
    for (const a of m.arboles) {
      const usadas = [...new Set(a.variable.filter((v) => v >= 0))], m = usadas.length, pos = new Map(usadas.map((v, i) => [v, i]));
      const peso = Array.from({ length: m }, (_, s) => factorial[s] * factorial[m - s - 1] / factorial[m]);
      const internos = a.variable.map((v, n) => (v >= 0 ? n : -1)).filter((n) => n >= 0);
      const vaIzq = (vec, n) => f32(vec[a.variable[n]]) <= a.umbral[n];
      const izqX = a.variable.map((v, n) => v >= 0 && vaIzq(t, n)), cache = new Map();
      for (const z of fondo) {
        const izqZ = a.variable.map((v, n) => v >= 0 && vaIzq(z, n));
        const clave = internos.map((n) => (izqZ[n] ? 1 : 0)).join("");     // el árbol solo "ve" hacia dónde va z en cada nodo
        let parcial = cache.get(clave);
        if (!parcial) {
          const vS = new Float64Array(1 << m);
          for (let mask = 0; mask < 1 << m; mask++) {
            let n = 0;
            while (a.izquierda[n] !== -1) n = ((mask >> pos.get(a.variable[n])) & 1 ? izqX[n] : izqZ[n]) ? a.izquierda[n] : a.derecha[n];
            vS[mask] = a.valor[n];
          }
          parcial = new Float64Array(m);
          for (let i = 0; i < m; i++) {
            for (let mask = 0; mask < 1 << m; mask++) {
              if ((mask >> i) & 1) continue;
              let s = 0; for (let q = mask; q; q &= q - 1) s++;
              parcial[i] += peso[s] * (vS[mask | (1 << i)] - vS[mask]);
            }
          }
          cache.set(clave, parcial);
        }
        for (let i = 0; i < m; i++) phi[usadas[i]] += parcial[i];
      }
    }
    const n = fondo.length * m.arboles.length;
    return phi.map((v) => v / n);
  }

  function porVariable(valores, origen) {
    const r = {};
    valores.forEach((v, j) => { r[origen[j]] = (r[origen[j]] || 0) + v; });
    return r;
  }
  function agrupar(contrib, grupos) {
    return Object.entries(grupos).map(([g, vs]) => [g, vs.reduce((s, v) => s + (v in contrib ? contrib[v] : 0), 0)]);
  }

  // explicabilidad.contexto: el dato concreto que acompaña a cada factor
  function contexto(X, grupo) {
    const f = new Proxy(X, { get: (o, c) => { if (!(c in o)) throw new Error(c); return o[c]; } });
    const textos = {
      "Beca y precio": () => `beca ${titulo(String(f.beca).replaceAll("_", " "))}, descuento ${pyFixed(f.pct_descuento_inicial * 100, 0)}%`,
      "Puntaje Saber 11": () => `puntaje global ${Math.trunc(f.punt_global)}`,
      "Distancia al campus": () => `vive a ${pyFixed(Math.exp(f.log_distancia), 0)} km por vía`,
      "Canal de captación": () => `llegó por ${String(f.canal).replaceAll("_", " ").toLowerCase()}`,
      "Entrevista vocacional": () => (f.entrevista_realizada === 1
        ? `puntaje vocacional ${Math.trunc(f.puntaje_vocacional)}; según sus palabras ${pyFixed(Number(f.puntaje_vocacional_nlp), 1)}` : "sin entrevista"),
      "Apoyo FOES municipal": () => (X.apoyo_foes === 1 ? "con apoyo del fondo municipal" : "sin apoyo del fondo municipal"),
      "Descuento institucional": () => (X.tiene_descuento === 1 ? "con descuento institucional: ya conoce la Universidad" : "sin descuento institucional"),
      "Crédito ICETEX": () => (X.aplica_icetex === 1 ? "solicitará el crédito ICETEX y cumple el mérito" : "sin crédito ICETEX"),
      "Estrato y régimen de salud": () => `estrato ${Math.trunc(f.estrato)}`,
      "Programa": () => `programa ${f.programa}`,
      "Ingreso a mitad de año": () => (f.semestre_2 === 1 ? "ingresa en el segundo periodo del año" : "ingresa en el primer periodo del año"),
      "Colegio de procedencia": () => `colegio ${NOMBRE_TIPO_COLEGIO[f.tipo_colegio] || String(f.tipo_colegio).toLowerCase()}`,
      "Contacto con asesores": () => `${Math.trunc(f.contactos_antes_de_inscribirse)} contactos antes de inscribirse`,
      "Edad y años desde el Saber 11": () => `${Math.trunc(f.edad_al_inscribirse)} años`,
      "Segmento de mercado": () => String(f.segmento_mercado),
      "Género": () => `género ${f.genero}`,
    };
    try { return textos[grupo](); } catch { return ""; }
  }

  // explicabilidad.top_factores: los k conceptos que más mueven la predicción, en español
  function topFactores(porGrupo, fila, k, que) {
    return [...porGrupo].sort((a, b) => Math.abs(b[1]) - Math.abs(a[1])).slice(0, k).map(([g, v]) => {
      const dato = contexto(fila, g);
      return `${g}${dato ? ` (${dato})` : ""}: ${v > 0 ? "aumenta" : "reduce"} la probabilidad de ${que}.`;
    });
  }

  function recomendacion(r) {
    const partes = { ALTA: ["Asegurar la matrícula: proceso ágil y recordatorio de las fechas de pago."],
      MEDIA: ["Prioridad de seguimiento del asesor: es un aspirante indeciso, donde una llamada más pesa."],
      BAJA: ["Contacto ligero: la probabilidad es baja; revisar si aplica a beca o a apoyo del fondo municipal."] }[r.segmento_propension];
    if (r.distancia_vial_km > 20) partes.push("Vive lejos: ofrecer el beneficio de 100 pasajes de TransMilenio.");
    if (r.elegible_foes) partes.push("Reside en un municipio con FOES/FOEST: acompañar la solicitud del apoyo antes de la matrícula.");
    if (r.elegible_icetex && !r.aplica_icetex) partes.push("Cumple el mérito del Plan Talento STEM de ICETEX: contarle del crédito (paga el 30% mientras estudia).");
    if (r.puntaje_vocacional === null) partes.push("No ha presentado la entrevista: enviarle la entrevista vocacional (es requisito de la beca Mi Vocación).");
    return partes.join(" ");
  }

  // prediccion.predecir
  function predecir(entrada) {
    const fila = completar(entrada), d = conNLP(construir(fila), fila, entrada);
    const mat = preparar(d, M.matricula);
    const prob = probModelo(M.matricula, mat.t);
    const razones = topFactores(agrupar(porVariable(shapModelo(M.matricula, mat.t), mat.origen), M.matricula.grupos), mat.fila, 3, "matricularse");
    const s = R.segmentos_propension;
    const r = { probabilidad_matricula: prob, segmento_propension: prob >= s.ALTA ? "ALTA" : prob < s.BAJA ? "BAJA" : "MEDIA",
      beca_que_aplica: d.beca, puntaje_vocacional: d.puntaje_vocacional, puntaje_vocacional_nlp: d.puntaje_vocacional_nlp,
      segmento_mercado: d.segmento_mercado,
      segmento_rendimiento_icfes: d.segmento_rendimiento_icfes,
      distancia_campus_km: d.distancia_campus_km, distancia_vial_km: d.distancia_vial_km, origen_distancia: d.origen_distancia,
      ubicacion: d.ubicacion_nombre, elegible_foes: Boolean(d.elegible_foes),
      tipo_descuento: d.tipo_descuento, pct_descuento_inicial: d.pct_descuento_inicial,
      elegible_icetex: Boolean(d.elegible_icetex), aplica_icetex: Boolean(d.aplica_icetex), razones_matricula: razones,
      probabilidad_sin_beca: null };
    if (d.beca !== "NINGUNA") {
      const f0 = { ...fila, beca: "NINGUNA", pct_descuento_inicial: fila.pct_descuento_adicional,   // conserva su descuento
        valor_neto_primer_semestre: rint(fila.valor_semestre_bruto * (1 - fila.pct_descuento_adicional)) };
      r.probabilidad_sin_beca = probMatricula(conNLP(construir(f0), fila, entrada));
    }
    r.recomendacion = recomendacion(r);
    return r;
  }

  // Precio con la beca y el descuento: Saber 11 35% y Mi Vocación 30% en toda la carrera; beca + descuento con tope del 50%
  function precios(programa, periodo, beca, descuento = 0) {
    const bruto = R.tarifas[programa][periodo.slice(0, 4)], b = R.becas[beca], tope = R.descuentos.tope;
    const p1 = pyRound(Math.min(b.pct_primer + descuento, tope), 4), p2 = pyRound(Math.min(b.pct_siguientes + descuento, tope), 4);
    return { bruto, pct_beca: b.pct_primer, pct_descuento: descuento, pct_total: p1, pct_siguientes: p2,
      neto: rint(bruto * (1 - p1)), neto_siguientes: rint(bruto * (1 - p2)) };
  }

  return { reglas: R, ubicaciones: M.ubicaciones, predecir, becaQueAplica, precios, completar, distancias, puntajeNLP,
    descuentoInstitucional, elegibleIcetex };
}
