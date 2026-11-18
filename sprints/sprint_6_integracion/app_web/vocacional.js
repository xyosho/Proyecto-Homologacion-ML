// Formulario de la entrevista de admisión de Unicervantes ("ENTREVISTA DE ADMISIÓN"), digitalizado. Lo usan el enlace
// público del aspirante (entrevista.js, secciones 1 a 7) y la vista de la psicóloga (psicologia.js, secciones 8 a 10 y
// salud mental). Las claves (p1…c1) son las que valida entrevista_enviar en Supabase.

export const SECCIONES = [
  { id: "programa", titulo: "Interés por el programa académico", preguntas: [
    ["p1", "¿Por qué quiere estudiar esta carrera profesional?"],
    ["p2", "Por favor defina su programa elegido"],
    ["p3", "¿Qué es lo que más le gusta de la carrera?"],
    ["p4", "¿Cómo se ve en un futuro como profesional?"],
    ["p5", "Si tuviera que elegir otra carrera, ¿cuál sería? ¿Por qué?"]] },
  { id: "historia", titulo: "Historia de vida", preguntas: [
    ["h1", "Cuéntenos sobre usted"],
    ["h3", "Ocupación de las personas con quien vive"],
    ["h4", "¿Trabaja? ¿Cómo ha planeado financiar sus estudios?"],
    ["h5", "¿Cuáles considera que son sus cualidades y/o habilidades? Mencione mínimo 3"],
    ["h6", "¿Qué aspectos considera que debe mejorar en usted mismo? Mencione mínimo 3"],
    ["h7", "¿Cómo fue su rendimiento académico en el colegio? (Asignaturas de mayor y menor interés)"],
    ["h8", "¿Qué le gusta hacer en sus tiempos libres?"]] },
  { id: "universidad", titulo: "Interés por la universidad", preguntas: [["u1", "¿Por qué quiere estudiar en Unicervantes?"]] },
  { id: "conciencia", titulo: "Conciencia social", preguntas: [
    ["c1", "¿Cuál cree que es la importancia de la carrera que eligió estudiar frente a las problemáticas actuales del país?"]] },
];
export const CON_QUIEN_VIVE = ["Padre", "Madre", "Hermanos", "Pareja", "Hijos", "Otro"];
export const DOCUMENTOS = { CC: "C.C.", CE: "C.E.", TI: "T.I.", PP: "P.P." };
export const ESTADO_SALUD = { EXCELENTE: "Excelente", BUENO: "Bueno", REGULAR: "Regular", DELICADO: "Delicado" };
export const MOTIVOS_CITA = { ENTREVISTA_VOCACIONAL: "Entrevista vocacional", SEGUNDA_ENTREVISTA: "Segunda entrevista", SEGUIMIENTO: "Seguimiento" };
export const ESTADOS_CITA = { PENDIENTE: "Pendiente", ATENDIDA: "Atendida", NO_ASISTIO: "No asistió", CANCELADA: "Cancelada" };

// Las tres secciones que lee el modelo NLP, con las respuestas en el orden de pregunta_entrevista (preguntas 1 a 13).
// Conciencia social no entra: el modelo se entrenó con esas 13 preguntas.
export function respuestasNLP(r) {
  const x = (r && r.respuestas) || {};
  return { texto_interes_programa: ["p1", "p2", "p3", "p4", "p5"].map((k) => x[k] || ""),
    texto_historia_vida: ["h1", "h3", "h4", "h5", "h6", "h7", "h8"].map((k) => x[k] || ""),
    texto_interes_universidad: [x.u1 || ""] };
}
