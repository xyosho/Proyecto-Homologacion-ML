"""Banco de frases para simular las respuestas abiertas de la entrevista de admisión (supuesto S-48).

No hay respuestas reales de entrevistas: cada respuesta se arma con frases en español de tres niveles de vocación
(0 = débil, 1 = media, 2 = fuerte), con el vocabulario del programa y fragmentos coherentes con los datos que ya tiene
el aspirante ANTES de la entrevista (canal, distancia, si su ICFES le da la Beca Saber 11, estrato, rendimiento en el
colegio). Nunca se usa nada que dependa de la entrevista (la beca Mi Vocación se asigna con su puntaje) ni de la
matrícula, ni nombres o datos que identifiquen a una persona.

Uso: responder(rng, pregunta_id, nivel, contexto) -> str   (lo llama src/s02_generar_datos_sinteticos.py)
"""
from __future__ import annotations

PROGRAMAS = {
    "AD": {
        "temas": ["la estadística", "la programación en Python", "las bases de datos", "la visualización de datos",
                  "el aprendizaje automático", "la inteligencia de negocios", "el análisis de datos"],
        "roles": ["científic{o} de datos", "analista de datos", "ingenier{o} de datos", "analista de inteligencia de negocios"],
        "favorita": ["estadística", "informática", "física"],
        "definicion": [
            "Es una ingeniería que usa la estadística, la programación y el aprendizaje automático para convertir los datos en decisiones.",
            "La analítica de datos recoge, limpia y analiza datos para encontrar patrones y predecir lo que puede pasar en una organización.",
            "Es la carrera que forma profesionales capaces de construir modelos con datos para que las empresas tomen mejores decisiones."],
        "otras": ["Estadística", "Economía", "Ingeniería Industrial", "Administración de Empresas", "Contaduría"],
    },
    "SSIA": {
        "temas": ["el desarrollo de software", "la inteligencia artificial", "los algoritmos", "las aplicaciones móviles",
                  "la ciberseguridad", "las redes neuronales", "la programación"],
        "roles": ["desarrollador{a_} de software", "ingenier{o} de inteligencia artificial", "arquitect{o} de software",
                  "ingenier{o} de aprendizaje automático"],
        "favorita": ["informática", "tecnología", "física"],
        "definicion": [
            "Es la ingeniería que diseña y construye software de calidad y aplica la inteligencia artificial para que los sistemas aprendan de los datos.",
            "Forma ingenieros que desarrollan aplicaciones, sistemas y modelos de inteligencia artificial para resolver problemas reales.",
            "Es la carrera que une el desarrollo de software con la inteligencia artificial: programar, diseñar sistemas y entrenar modelos."],
        "otras": ["Ingeniería Electrónica", "Diseño Gráfico", "Ingeniería Mecatrónica", "Ingeniería de Sistemas", "Administración de Empresas"],
    },
}
MULETILLAS = ["Pues, ", "Bueno, ", "Mmm, ", "La verdad, "]
MENOS_GUSTABA = ["sociales", "química", "inglés", "filosofía", "biología", "español"]


def _uno(rng, lista):
    return lista[int(rng.integers(len(lista)))]


def _varios(rng, listas_por_nivel: dict, nivel: int, k: int) -> list[str]:
    """k elementos distintos: cada uno del nivel de la respuesta (70%) o de otro nivel al azar."""
    salida = []
    while len(salida) < k:
        n = nivel if rng.random() < 0.7 else int(rng.integers(3))
        x = _uno(rng, listas_por_nivel[n])
        if x not in salida:
            salida.append(x)
    return salida


def _genero(texto: str, genero: str) -> str:
    f = genero == "F"
    return texto.replace("{o}", "a" if f else "o").replace("{a_}", "a" if f else "")


def _primera_mayuscula(t: str) -> str:
    return t[0].upper() + t[1:] if t else t


# ---------------------------------------------------------------------------- Interés por el programa académico
def _por_que_carrera(rng, n, c, p):
    return _uno(rng, {
        2: ["Desde el colegio me apasiona el mundo de {tema}; hice cursos por mi cuenta y quiero dedicarme a esto.",
            "Siempre he querido trabajar con {tema}. En el colegio participé en proyectos y supe que esta es mi carrera.",
            "Me encanta resolver problemas con {tema} y quiero formarme como {rol}.",
            "Tengo claro que quiero ser {rol}; llevo tiempo aprendiendo sobre {tema} por mi cuenta y me motiva mucho."],
        1: ["Me gustan las matemáticas y la tecnología, y creo que esta carrera las une.",
            "Me llama la atención el tema de {tema} y la carrera tiene buen campo laboral.",
            "Me fue bien en matemáticas y quiero aprovecharlo en una ingeniería.",
            "Me interesa la tecnología y quiero aprender más sobre {tema}."],
        0: ["Mis papás me dijeron que tiene buena salida laboral.",
            "No estoy muy segur{o} todavía, pero dicen que paga bien.",
            "Un amigo la está estudiando y me pareció una opción.",
            "Quería estudiar algo y esta carrera me pareció interesante, aunque no la conozco mucho."]}[n])


def _defina_programa(rng, n, c, p):
    return _uno(rng, {
        2: p["definicion"],
        1: ["Es una carrera de tecnología donde se trabaja con {tema} y con computadores.",
            "Se trata de usar la tecnología para resolver problemas de las empresas.",
            "Es una ingeniería que mezcla las matemáticas con la programación."],
        0: ["Es algo de computadores, creo.", "No sabría definirla bien; tiene que ver con sistemas.",
            "Es una ingeniería, pero todavía no sé muy bien qué se ve.", "Algo relacionado con la tecnología."]}[n])


def _que_le_gusta(rng, n, c, p):
    return _uno(rng, {
        2: ["Lo que más me gusta es todo lo relacionado con {tema} y poder construir soluciones reales.",
            "Me emociona trabajar con {tema}; ya hice un proyecto pequeño y quiero aprender a hacerlo bien.",
            "Que puedo aplicar {tema} en salud, educación o medio ambiente y ayudar a la gente."],
        1: ["Que es una carrera moderna y tiene mucho futuro.", "Me gusta que tiene mucha práctica con {tema}.",
            "Que se aprende a programar."],
        0: ["Que tiene buena salida laboral.", "Que se gana bien.", "Todavía no conozco bien las materias."]}[n])


def _futuro(rng, n, c, p):
    return _uno(rng, {
        2: ["Me veo como {rol} en una empresa grande y después quiero hacer una maestría.",
            "Trabajando como {rol} y, más adelante, con mi propia empresa de tecnología.",
            "En cinco años me veo como {rol}, liderando proyectos de {tema}."],
        1: ["Trabajando en una empresa de tecnología.", "Con un buen trabajo y ayudando a mi familia.",
            "Me veo trabajando en lo que estudié, quizás en otra ciudad."],
        0: ["No lo tengo muy claro todavía.", "Con un trabajo estable, no sé bien en qué.",
            "Eso todavía no lo he pensado mucho."]}[n])


def _otra_carrera(rng, n, c, p):
    return _uno(rng, {
        2: ["No me veo estudiando otra cosa; esta es la carrera que quiero.",
            "Si tuviera que elegir sería {otra}, pero esta es mi primera opción sin duda."],
        1: ["Tal vez {otra}, porque también me gustan los números.", "Quizás {otra}; también me llama la atención."],
        0: ["Estoy entre esta y {otra}; todavía no me decido.",
            "{otra}, porque también me presenté a esa carrera en otra universidad.",
            "Cualquiera, la verdad no estoy segur{o}."]}[n])


# ---------------------------------------------------------------------------- Historia de vida
def _sobre_usted(rng, n, c, p):
    base = _uno(rng, {
        2: ["Soy una persona curiosa y disciplinada; me gusta aprender sobre tecnología por mi cuenta.",
            "Me considero constante: cuando algo me interesa, investigo hasta entenderlo.",
            "Soy disciplinad{o} y tengo metas claras; quiero ser profesional y salir adelante con mi familia."],
        1: ["Soy una persona tranquila y responsable; vivo con mi familia.",
            "Me gusta compartir con mis amigos y con mi familia; soy alegre.",
            "Soy responsable y me gusta hacer bien las cosas."],
        0: ["No sé qué decir; soy normal, me gusta salir con mis amigos.",
            "Soy una persona tranquila; todavía estoy pensando qué hacer con mi vida.",
            "No sé, me cuesta hablar de mí."]}[n])
    etapa = ("Terminé el colegio hace un tiempo y quiero retomar mis estudios." if c["edad"] >= 20
             else "Acabo de terminar el colegio.")
    return f"{etapa} {base}" if rng.random() < 0.6 else base


def _ocupacion_hogar(rng, n, c, p):
    e = c["estrato"]
    return _uno(rng, [
        "Mi mamá trabaja en casas de familia y mi papá es conductor.",
        "Mi mamá tiene un negocio de comidas y mi hermano trabaja en construcción.",
        "Vivo con mi mamá, que trabaja en un almacén, y con mi abuela, que es pensionada."] if e <= 2 else [
        "Mi papá es técnico de mantenimiento y mi mamá es secretaria.",
        "Mi mamá es auxiliar contable y mi papá trabaja como vendedor.",
        "Mis papás tienen una tienda en el barrio."] if e == 3 else [
        "Mi papá es ingeniero y mi mamá es abogada.",
        "Mis padres son profesionales: mi mamá es médica y mi papá es administrador.",
        "Mi mamá es docente universitaria y mi papá tiene una empresa."])


def _trabajo_financiacion(rng, n, c, p):
    trabaja = rng.random() < 0.12 + 0.30 * (c["edad"] >= 20) + 0.10 * (c["estrato"] <= 2)
    partes = [f"Sí, trabajo medio tiempo en {_uno(rng, ['un almacén', 'un call center', 'un restaurante', 'una empresa de mensajería', 'un negocio familiar'])}."
              if trabaja else _uno(rng, ["No trabajo; me dedico a estudiar.", "Por ahora no trabajo."])]
    partes.append(_uno(rng, {
        2: ["Ya tengo el plan: mis papás pagan una parte y el resto lo cubro con un crédito del ICETEX.",
            "Ahorré durante el último año y ya tengo lo de la primera matrícula.",
            "Ya estoy tramitando un crédito educativo para todo el semestre."],
        1: ["Mis papás me van a ayudar con la matrícula.", "Entre mi familia y yo vamos a pagar el semestre.",
            "Pensamos pedir un crédito educativo."],
        0: ["Todavía no sé cómo lo voy a pagar; estoy mirando opciones.",
            "Depende de si me dan alguna ayuda; si no, tendría que esperar.",
            "No lo he pensado bien; mis papás están mirando."]}[n]))
    if c["saber11"]:                                       # el ICFES ya le da la beca: lo sabe antes de la entrevista
        partes.append("Tengo la Beca Saber 11 por mi puntaje, y eso me ayuda mucho.")
    elif rng.random() < 0.5:                               # Mi Vocación depende de esta entrevista: solo la menciona
        partes.append("Quiero aplicar a la beca Mi Vocación para pagar menos.")
    if c["apoyo_foes"]:
        partes.append("También voy a pedir el apoyo del fondo de educación de mi municipio.")
    return " ".join(partes)


def _cualidades(rng, n, c, p):
    a, b, d = _varios(rng, {
        2: ["la disciplina", "la curiosidad", "el pensamiento lógico", "la facilidad para las matemáticas",
            "la perseverancia", "la creatividad para resolver problemas"],
        1: ["la responsabilidad", "la puntualidad", "el trabajo en equipo", "el respeto", "la amabilidad"],
        0: ["la paciencia", "el buen humor", "la tranquilidad", "que soy buena persona"]}, n, 3)
    return f"Considero que mis cualidades son {a}, {b} y {d}."


def _por_mejorar(rng, n, c, p):
    a, b, d = _varios(rng, {
        2: ["la impaciencia cuando un programa no funciona", "la organización de mi tiempo de estudio",
            "el miedo a hablar en público", "el perfeccionismo"],
        1: ["la puntualidad", "la timidez", "el manejo del estrés", "el orden en mis cosas"],
        0: ["la pereza", "la falta de constancia", "la desmotivación", "la indecisión"]}, n, 3)
    return f"Debo mejorar {a}, {b} y {d}."


def _rendimiento_colegio(rng, n, c, p):
    prom = c["promedio_colegio"]
    nivel = ("Mi rendimiento fue muy bueno; casi siempre estuve en el cuadro de honor." if prom >= 4.6 else
             "Mi rendimiento fue bueno." if prom >= 4.0 else "Mi rendimiento fue regular; me costaron algunas materias.")
    menos = _uno(rng, MENOS_GUSTABA)
    interes = _uno(rng, {
        2: [f"Mis materias favoritas eran matemáticas y {_uno(rng, p['favorita'])}; la que menos me gustaba era {menos}."],
        1: [f"Me gustaban las matemáticas; me costaba {menos}."],
        0: ["Me iba mejor en educación física y artes; las matemáticas no eran lo mío.",
            f"No tenía una materia favorita; la que menos me gustaba era {menos}."]}[n])
    return f"{nivel} {interes}"


def _tiempo_libre(rng, n, c, p):
    a, b = _varios(rng, {
        2: ["programar pequeños proyectos", "ver tutoriales sobre {tema}", "armar y arreglar computadores",
            "participar en retos de programación"],
        1: ["jugar videojuegos", "leer", "escuchar música", "hacer deporte"],
        0: ["dormir", "ver series", "salir con mis amigos", "estar en redes sociales"]}, n, 2)
    return f"En mi tiempo libre me gusta {a} y {b}."


# ---------------------------------------------------------------------------- Interés por la universidad
def _por_que_unicervantes(rng, n, c, p):
    razones = {"REFERIDO": "un familiar estudió aquí y me la recomendó",
               "EXPOESTUDIANTES": "la conocí en ExpoEstudiantes y me gustó el programa",
               "CAMPUS_DAY": "fui al Campus Day y me gustó el campus",
               "INMERSION": "hice la inmersión y me sentí muy a gusto",
               "COLEGIO_CONVENIO": "mi colegio tiene convenio con la universidad"}
    opciones = [razones.get(c["canal"], "vi el programa en internet y me pareció muy completo")]
    if c["km_via"] <= 10:
        opciones.append("queda cerca de mi casa")
    elif c["km_via"] > 20:
        opciones.append("aunque queda lejos de mi casa, el programa vale la pena")
    opciones.append("con la Beca Saber 11 puedo pagarla" if c["saber11"] else
                    _uno(rng, ["tiene precios que mi familia puede pagar", "si me dan la beca Mi Vocación, puedo pagarla"]))
    razon = _uno(rng, opciones)
    return _uno(rng, {
        2: [f"Unicervantes es mi primera opción: {razon}.", f"Elegí Unicervantes porque {razon}, y quiero estudiar aquí."],
        1: [f"Me gusta Unicervantes porque {razon}.", f"Escogí Unicervantes porque {razon}."],
        0: ["Me presenté a varias universidades y Unicervantes fue una de las que me respondió.",
            f"Estoy esperando respuesta de otras universidades; Unicervantes es una opción porque {razon}.",
            f"La verdad no conozco mucho Unicervantes; {razon}."]}[n])


RESPUESTAS = {1: _por_que_carrera, 2: _defina_programa, 3: _que_le_gusta, 4: _futuro, 5: _otra_carrera,
              6: _sobre_usted, 7: _ocupacion_hogar, 8: _trabajo_financiacion, 9: _cualidades, 10: _por_mejorar,
              11: _rendimiento_colegio, 12: _tiempo_libre, 13: _por_que_unicervantes}


def responder(rng, pregunta_id: int, nivel: int, contexto: dict) -> str:
    """Respuesta simulada a una pregunta abierta. nivel: 0 débil, 1 media, 2 fuerte."""
    p = PROGRAMAS[contexto["programa"]]
    texto = RESPUESTAS[pregunta_id](rng, nivel, contexto, p)
    texto = (texto.replace("{tema}", _uno(rng, p["temas"])).replace("{rol}", _uno(rng, p["roles"]))
             .replace("{otra}", _uno(rng, p["otras"])))
    if rng.random() < {0: 0.35, 1: 0.10, 2: 0.0}[nivel]:          # quien duda empieza con muletillas
        propio = texto.startswith(("Unicervantes", "ICETEX"))      # los nombres propios no van en minúscula
        texto = _uno(rng, MULETILLAS) + (texto if propio else texto[0].lower() + texto[1:])
    return _primera_mayuscula(_genero(texto, contexto["genero"]))
