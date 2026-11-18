// Comprueba que modelo.js (navegador) da lo mismo que prediccion.predecir (Python) en los casos de exportar_modelo.py.
// Uso: node sprints/sprint_6_integracion/app_web/pruebas/verificar_modelo.mjs
import { readFileSync } from "node:fs";
import { crearModelo, direccionACatastro, pyFixed } from "../modelo.js";

const aqui = new URL(".", import.meta.url);
const modelo = crearModelo(JSON.parse(readFileSync(new URL("../modelo.json", aqui), "utf8")));
const casos = JSON.parse(readFileSync(new URL("casos_verificacion.json", aqui), "utf8"));

const NUMEROS = ["probabilidad_matricula", "probabilidad_sin_beca", "puntaje_vocacional", "puntaje_vocacional_nlp",
  "distancia_campus_km", "distancia_vial_km"];
const TEXTOS = ["segmento_propension", "beca_que_aplica", "segmento_mercado", "segmento_rendimiento_icfes", "origen_distancia",
  "ubicacion", "elegible_foes", "razones_matricula", "recomendacion"];
const TOLERANCIA = 1e-9;

let fallas = 0, maxDif = 0;
const inicio = performance.now();
for (const [i, { entrada, salida }] of casos.entries()) {
  const r = modelo.predecir(entrada);
  const claves = (o) => JSON.stringify(Object.keys(o).sort());          // ni una clave de más ni de menos
  if (claves(r) !== claves(salida)) { fallas++; console.log(`caso ${i} · claves:\n  JS     ${claves(r)}\n  Python ${claves(salida)}`); }
  for (const k of NUMEROS) {
    const a = r[k], b = salida[k];
    const ok = a === null || b === null ? a === b : Math.abs(a - b) <= TOLERANCIA;
    if (a !== null && b !== null) maxDif = Math.max(maxDif, Math.abs(a - b));
    if (!ok) { fallas++; console.log(`caso ${i} · ${k}: JS ${a} vs Python ${b}`); }
  }
  for (const k of TEXTOS) {
    if (JSON.stringify(r[k]) !== JSON.stringify(salida[k])) {
      fallas++; console.log(`caso ${i} · ${k}:\n  JS     ${JSON.stringify(r[k])}\n  Python ${JSON.stringify(salida[k])}`);
    }
  }
}
const ms = (performance.now() - inicio) / casos.length;

// Direcciones (lo esperado es lo que devuelve prediccion.direccion_a_catastro en Python) y redondeos de Python
const direcciones = [["Calle 26 # 57-41", ["CL 26", "57 41"]], ["Carrera 69B # 37A-35 Sur", ["KR 69B", "37A 35 S"]],
  ["Avenida Calle 26 No. 57-41", ["AC 26", "57 41"]], ["Calle 9 Bis A # 7-65 Sur", ["CL 9BIS A", "7 65 S"]],
  ["Diagonal 40A Sur # 12-30", ["DG 40A S", "12 30"]], ["Transversal 78 H # 41 F - 12", ["TV 78 H", "41 F 12"]],
  ["KR 7 # 72-41", ["KR 7", "72 41"]], ["Carrera 104 # 152C-30 Este", ["KR 104", "152C 30 E"]],
  ["calle 170 n° 54-20", ["CL 170", "54 20"]], ["Cra 15 # 85-24", ["KR 15", "85 24"]]];
for (const [t, esperado] of direcciones) {
  const r = direccionACatastro(t);
  if (JSON.stringify(r) !== JSON.stringify(esperado)) { fallas++; console.log(`dirección '${t}': ${r} (se esperaba ${esperado})`); }
}
for (const [x, d, esperado] of [[2.675, 2, "2.67"], [0.125, 2, "0.12"], [0.375, 2, "0.38"], [12.5, 0, "12"], [13.5, 0, "14"], [4.0, 2, "4.00"]]) {
  if (pyFixed(x, d) !== esperado) { fallas++; console.log(`pyFixed(${x}, ${d}) = ${pyFixed(x, d)} (Python: ${esperado})`); }
}

console.log(`${casos.length} aspirantes · diferencia máxima ${maxDif.toExponential(2)} · ${ms.toFixed(1)} ms por predicción`);
console.log(fallas ? `FALLÓ: ${fallas} diferencias` : "OK: modelo.js da lo mismo que Python");
process.exit(fallas ? 1 : 0);
