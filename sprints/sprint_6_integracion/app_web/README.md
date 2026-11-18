# App web de ingreso de aspirantes (Vercel + Supabase)

Versión en línea del formulario de ingreso, publicada en **https://homologacion-ingreso-aspirantes.vercel.app**
(proyecto de Vercel `homologacion-ingreso-aspirantes`). El personal de Admisiones inicia sesión, registra aspirantes,
predice su matrícula con el modelo del proyecto, hace el seguimiento y mira la analítica en vivo.

| Sección | Qué hace |
|---|---|
| **Resumen** | Indicadores (registrados, con predicción, que se matricularían, por contactar), propensión, "para llamar primero" (indecisos sin contactar) y los registrados recientemente |
| **Registrar aspirante** | Registro por pasos: Aspirante → Contacto → Saber 11 y becas → Residencia → Colegio → Revisar. Desplegables para los datos con opciones (edad, cómo conoció la Universidad, estrato, cuándo presentó el Saber 11, rúbrica de la entrevista de 1 a 5 por sección, ciudad, localidad, régimen de salud, tipo de colegio) y **dirección guiada** (tipo de vía, número, letra, Bis, Sur/Este, cruce y placa) que en Bogotá se ubica sola en Catastro y elige la localidad. El panel lateral muestra en vivo la beca, el precio y la **distancia al campus en línea recta y por vías** |
| **Aspirantes** | Lista con filtro rápido por propensión, búsqueda, filtros (programa, seguimiento, distancia por vía), orden, distancia en las dos medidas y descarga en CSV. Las altas de otras sesiones llegan en vivo |
| **Ficha del aspirante** | Predicción (probabilidad, razones, índice vocacional, recomendación), contacto (llamar, WhatsApp, correo), distancia, **mapa con la ruta por calles al campus** (km y tiempo en carro), beca y precio, datos, camino de seguimiento y notas |
| **Analítica** | Tablero que se actualiza solo (tiempo real de Supabase). **Pestañas por semestre de ingreso** (todos, 2027-1, 2027-2…) y **comparación por semestre** lado a lado (registrados, con predicción, que se matricularían, probabilidad, distancia, seguimiento). Filtros por programa y fecha; 8 gráficas predeterminadas (registros por día, propensión, cómo conocieron la Universidad, distancia por ubicación en línea recta y por vías, distancia y probabilidad, probabilidad por programa, seguimiento, ICFES y probabilidad). Cada gráfica cambia de tipo y muestra la tabla; **Agregar gráfica** arma una propia (agrupar por un dato, elegir la medida y el tipo, o una dispersión de dos variables) y queda guardada en el navegador |
| **Errores** | Páginas propias para dirección inexistente (404, también la estática de Vercel), aspirante que no existe, sin conexión con la base, cuenta sin permiso y error inesperado; franja de "sin conexión" y avisos emergentes |

Beca y precio: la Beca Saber 11 es del **35%** el 1er semestre y del **30%** desde el 2º (recibos 2024-2 y 2025-2026);
Mi Vocación, del **30%** el 1er semestre y del **20%** después. El pronto pago no es un descuento de la Universidad: no se
muestra ni lo usa el modelo.

**Soacha** se puede elegir como municipio vecino (coordenada de la DIVIPOLA del DANE). No está en los datos de
entrenamiento (Bogotá y Sabana Centro): el modelo la calcula por su distancia al campus y la app avisa que es una
extrapolación.

## Base simulada y aspirantes nuevos, en vivo
La lista, la ficha y la analítica leen la vista `vista_aspirantes` de Supabase por la API (clave publicable + sesión),
sin copias: une los **registrados en la app** (`aspirante_registrado`) con la **base simulada** 2024-1 a 2027-1
(`dataset_matricula`, `prediccion`, `inscripcion`, `aspirante`), con su predicción del Sprint 6 y el resultado real.
Cada fila dice su origen y su identificador de origen (trazabilidad). Cuando un asesor registra un aspirante, queda
guardado en Supabase (RLS le da permiso de escritura solo para los suyos) y aparece al instante para el jefe y el
administrador. La base simulada es de solo lectura y la ven el jefe y el administrador; el asesor ve solo lo suyo.
La analítica muestra todos los semestres, compara la predicción con el resultado real y agrupa por mes cuando el
rango es largo.

## Encuesta para el aspirante (enlace)
El asesor crea un enlace en **Encuestas** (nombre opcional, programa, vencimiento de 7 a 180 días y, si quiere, de un
solo uso) y lo envía por WhatsApp, correo o el botón de compartir del celular. El aspirante abre
`/encuesta/<código>` **sin iniciar sesión** y solo ve la encuesta: sus datos por pasos, su **beca con el descuento y
el precio** en vivo y el **mapa de su ruta al campus**. Al enviarla queda como aspirante **NUEVO** de ese asesor (marca
«Encuesta»), le llega un aviso en vivo y su app calcula la predicción sola. El aspirante nunca ve la predicción.
- **Seguridad:** el aspirante no lee ni escribe tablas. La página solo llama a dos funciones de Supabase sin sesión,
  `encuesta_info` (dice si el enlace sirve y el primer nombre del asesor) y `encuesta_enviar` (valida el enlace con
  bloqueo y cada dato, y guarda). Límites: un solo uso si así se creó, 20 respuestas cada 10 minutos y 300 en total por
  enlace, vencimiento, campo trampa para robots y autorización de datos obligatoria (Ley 1581 de 2012).
- **Enlaces:** tabla `enlace_encuesta` (el código lo genera la base). RLS: cada asesor ve y desactiva los suyos; el jefe
  y el administrador, todos. Desde la app nadie puede marcar un aspirante como «Encuesta» ni cambiar de dónde llegó.
- **Probar sin Supabase:** en la app de demostración (`?demo=asesor`) cree un enlace y ábralo con «Ver encuesta»; lo
  que se envíe aparece en la otra pestaña.
- **Enlace o código QR:** cada enlace listo se comparte de las dos formas. El enlace recién creado muestra a la vez
  el enlace (copiar, WhatsApp, correo) y su **código QR**; en «Mis enlaces», cada enlace activo tiene el botón
  **Código QR**. El enlace de la entrevista vocacional de la ficha también trae su QR. El aspirante lo escanea con la
  cámara del celular (en una feria, en el colegio o frente al asesor), y **Descargar QR** guarda un PNG con el título
  debajo para enviarlo o imprimirlo. El QR lo dibuja `qr.js` en el navegador con `qrcode-generator` (cdnjs, con
  `integrity`): el enlace no se envía a ningún servicio externo.

## Diseño y uso en el celular
- **Letra:** Open Sans, la misma del sitio oficial (unicervantes.edu.co): texto en 400 con interlineado 1,5, títulos y
  etiquetas en 700 y cifras grandes en 800. Colores: blanco y rojo, con el vino y el dorado del logo.
- **Celular (hasta 900 px):** barra superior con el logo y el menú, y **barra inferior fija** con Resumen, Aspirantes
  (con su contador), Registrar, Analítica y **Más** (equipo, usuarios, mi perfil y cerrar sesión). La lista de
  aspirantes pasa a tarjetas, los filtros quedan plegados en **Filtros y orden** (el botón dice cuántos hay puestos) y
  las pestañas de propensión y de semestre se deslizan con el dedo.
- **Escritorio:** menú lateral que se pliega a íconos; en la tabla de aspirantes la primera columna queda fija al
  desplazarla a lo ancho.

## Ruta al campus por calles (mapa)
En la ficha de cada aspirante, la tarjeta **Ruta al campus por calles** traza la ruta en carro con punto de partida en
la dirección del aspirante (la placa de Catastro; si no la hay, el centro de su localidad o municipio, marcado como
aproximado) y llegada siempre en el campus (Calle 209, vía Arrayanes). Muestra los km por calles y el tiempo en carro, y
el botón **Abrir en Google Maps** abre la misma ruta. La misma tarjeta aparece en el panel lateral de **Registrar
aspirante** (se traza al elegir la ciudad o municipio y se afina cuando Catastro ubica la placa) y en la encuesta del
aspirante; cada vista tiene su propio mapa (`tarjetaRuta` en `mapa.js`).
- **Ruta y distancia:** OSRM (Open Source Routing Machine) sobre la red vial de OpenStreetMap, sin clave. En los
  aspirantes de la app se guarda en `aspirante_registrado` (`distancia_ruta_km`, `duracion_ruta_min`,
  `ruta_calculada_en`) cuando la abre quien puede editarla.
- **Mapa y cifras de la misma ruta:** con `GOOGLE_MAPS_KEY` en Vercel, el mapa, los km y el tiempo (con el tráfico de
  ese momento) salen de **Google Maps** (Maps JavaScript API y clase `Route` de la Routes API), en una página aislada
  (`ruta-google.html`, marco sandbox sin acceso a la sesión). Si Google no responde (por ejemplo, la clave sin la Routes
  API), se usa Leaflet 1.9.4 con OpenStreetMap y la ruta de OSRM, con sus propias cifras. Nunca se mezcla el mapa de un
  servicio con las cifras del otro.
- **Privacidad:** a los servicios externos solo va la coordenada redondeada a unos 100 m (3 decimales), nunca el nombre
  ni la dirección escrita.
- El modelo sigue usando su distancia por vías (supuesto S-44), con la que se entrenó; la ruta por calles es
  información para el asesor.

## Mi perfil, menú de usuario y barra lateral
- Al tocar su nombre en la barra lateral se abre el menú con **Mi perfil** y **Cerrar sesión**.
- **Mi perfil**: nombre, teléfono, cargo, foto (bucket privado `avatares` de Supabase Storage, recortada a 256 px y sin
  datos de ubicación) y cambio de contraseña. El correo y el rol los cambia el administrador; un disparador impide que
  alguien cambie su propio rol o su acceso.
- La barra lateral se **pliega** a solo íconos (botón junto al logo) y la app recuerda la preferencia.

## Traspaso de aspirantes entre asesores
Si un asesor no puede seguir con un aspirante, en su ficha usa **Traspasar a otro asesor**: elige a otro asesor activo
y escribe el motivo (obligatorio). El que recibe lo ve al instante en su lista, con un aviso y el motivo; el que lo
entregó lo sigue viendo en solo lectura («Traspasado a …»). El jefe y el administrador reasignan a cualquiera del
equipo (motivo opcional). Cada cambio de asesor queda en la tabla `traspaso_aspirante` (de quién, a quién, motivo,
quién lo hizo y cuándo), que escribe un disparador en Supabase y se ve en la ficha como **Historial de asesores**.

## Roles
| Rol | Qué puede hacer |
|---|---|
| **Asesor** (por defecto) | Registra aspirantes y ve, predice y hace seguimiento **solo de los suyos**; puede **traspasarlos** a otro asesor con un motivo. No borra (marca "Descartado") |
| **Jefe de admisiones** | Ve **todos** los aspirantes y **qué asesor tiene cada uno** (sección **Equipo**, columna y filtro de asesor, gráficas por asesor), los reasigna y los borra |
| **Administrador** | Lo mismo que el jefe y además la sección **Usuarios**: crea cuentas eligiendo el rol (asesor, jefe de admisiones o administrador, con contraseña temporal), cambia el rol entre asesor y jefe, y da de baja o reactiva a cualquier persona menos a otro administrador |

- El rol vive en la tabla `personal_autorizado` y lo hace cumplir **RLS** en Supabase: aunque alguien manipule la página,
  solo lee o cambia lo que su rol permite. Un cambio de rol rige de inmediato (no hay que volver a iniciar sesión).
- **Crear usuarios** necesita la clave secreta de Supabase, que nunca puede ir en el navegador; por eso lo hace la Edge
  Function `crear-usuario` (`supabase/functions/crear-usuario/index.ts`), que primero comprueba que quien llama es
  administrador activo. La cuenta nueva queda confirmada y con el rol elegido (la función solo acepta `ASESOR`,
  `JEFE` o `ADMIN`).
- Un administrador **no** puede cambiar su propio rol ni el de otro administrador, ni darlo de baja: lo impiden la
  política RLS `admin_cambia_roles` y el disparador `privado.proteger_rol`. Un rol de administrador ya existente solo se
  cambia en Supabase (SQL Editor), por ejemplo:
  `UPDATE public.personal_autorizado SET rol = 'JEFE' WHERE correo = 'correo@ejemplo.com';`
- **Dar de baja** quita el acceso sin borrar nada (sus aspirantes siguen guardados) y pide confirmar con un segundo
  clic; **Reactivar** lo devuelve.
- Cada quien cambia sus datos, su foto y su contraseña en **Mi perfil** (menú del usuario).
- Modo demostración por rol: `?demo` (administrador), `?demo=jefe` o `?demo=asesor`.

Alternativas que se descartaron: guardar el rol en el token (claims o `app_metadata`) obliga a volver a iniciar sesión
para que un cambio rija y necesita un Auth Hook; invitar por correo exige configurar SMTP propio.

## Cómo funciona
- **El modelo corre en el navegador** (`modelo.js`). Es la traducción de `src/prediccion.py`: columnas del Sprint 2,
  el modelo de matrícula que elige el Sprint 3 (hoy, regresión logística; también acepta un Random Forest), el índice
  vocacional de la rúbrica de la entrevista y explicaciones SHAP en español. Los parámetros
  salen de `modelo.json`, que genera `exportar_modelo.py` con los artefactos de los sprints 2 a 4.
- **Verificación:** `pruebas/verificar_modelo.mjs` compara 400 aspirantes al azar con Python (con rúbrica, solo con el puntaje vocacional y sin entrevista): la diferencia máxima es
  del orden de 10⁻¹⁶ y las razones son las mismas, palabra por palabra (`tests/test_app_web.py`).
- **Distancias:** en línea recta (Haversine) y por vías (tramo norte-sur + oriente-occidente, supuesto S-44); el modelo
  usa la de vías. Se guardan las dos con la coordenada y cómo se ubicó (placa de Catastro o centro de la localidad).
- **Datos:** tabla `aspirante_registrado` en Supabase (`sql/08_app_aspirantes.sql`). RLS: solo el personal que está en
  `personal_autorizado` puede leer o escribir; la clave publicable sola no ve nada. Crear una cuenta en Supabase Auth
  no da acceso. El tiempo real (Realtime) también respeta RLS.
- **Código:** `app.js` (arranque, sesión, rutas, vistas y errores), `formulario.js` (registro por pasos), `analitica.js`
  (tablero, Chart.js 4.4.1), `datos.js` (Supabase, tiempo real y predicción), `mapa.js` (ruta al campus),
  `ui.js` (formatos, avisos y animaciones).
  Paleta de las gráficas validada para daltonismo; todo respeta "reducir movimiento" del sistema.

## Conectar Vercel con Supabase (variables de entorno)
En Vercel → proyecto `homologacion-ingreso-aspirantes` → **Settings → Environment Variables** agregue, para
*Production* y *Preview*:

| Nombre | Valor |
|---|---|
| `SUPABASE_URL` | `https://<ref>.supabase.co` (Supabase → Project Settings → Data API) |
| `SUPABASE_KEY` | la clave **publicable** `sb_publishable_…` (Supabase → Project Settings → API Keys). **Nunca** la secreta |
| `GOOGLE_MAPS_KEY` | opcional: clave de Google Maps (`AIza…`) para el mapa de la ruta con los km y minutos de Google. Va en la página por diseño, así que en Google Cloud se **restringe**: *Restricciones de la aplicación* → sitios web (`https://homologacion-ingreso-aspirantes.vercel.app/*`) y *Restricciones de API* → **Maps JavaScript API** y **Routes API** (las dos habilitadas en el proyecto, con facturación activa) |

`construir.mjs` también acepta los nombres que crea la integración de Supabase en Vercel (`NEXT_PUBLIC_SUPABASE_URL`,
`NEXT_PUBLIC_SUPABASE_ANON_KEY`…) y rechaza claves secretas o `service_role`. Con las variables puestas, Vercel
construye la app solo (`vercel.json`: `node construir.mjs` → `publico/`):
```bash
vercel deploy sprints/sprint_6_integracion/app_web --prod
```
Sin variables en Vercel también se puede construir aquí con el `.env` y subir la carpeta ya armada:
```bash
python sprints/sprint_6_integracion/app_web/exportar_modelo.py
node sprints/sprint_6_integracion/app_web/construir.mjs
vercel deploy sprints/sprint_6_integracion/app_web/publico --prod
```
La primera vez: `vercel login` y `vercel link --yes --project homologacion-ingreso-aspirantes` en la carpeta que se
sube. `.vercelignore` impide subir el `.env.local` que deja `vercel link`. Las cabeceras de seguridad (CSP, sin
iframes, sin indexación) están en `vercel.json`.

### Tarea diaria para que Supabase no pause el proyecto
En el plan gratuito, Supabase **pausa el proyecto tras 7 días sin actividad**, y la app deja de iniciar sesión y de
guardar aspirantes hasta que alguien lo reactive a mano. Para evitarlo, `vercel.json` tiene un **Vercel Cron**
(`"crons"`) que todos los días a las 8:00 a. m. de Colombia (13:00 UTC) llama a `api/mantener-activo.js`. Esa función
hace una sola lectura (1 fila de `prediccion`) con la clave **publicable** de las variables de Vercel: no escribe nada
ni usa la clave secreta, y responde `{"ok": true, "supabase": 200}`.
- Funciona con el despliegue de la carpeta `app_web` (el primer comando de arriba). Si se sube solo `publico/`, no
  van ni la función ni el cron.
- En Vercel → proyecto → **Settings → Cron Jobs** aparece la tarea, con su historial y el botón para correrla ya.
- Opcional: si agrega la variable `CRON_SECRET` en Vercel, la función solo responde a Vercel (que la envía en la
  cabecera `Authorization`). Sin ella, la ruta solo hace esa lectura pública.
- Probarla: abrir `https://homologacion-ingreso-aspirantes.vercel.app/api/mantener-activo` (sin `CRON_SECRET`).

## Dar acceso a una persona del equipo
Lo normal es crearla desde la app (**Usuarios**, con una cuenta de administrador). A mano, en Supabase:
1. Supabase → Authentication → Users → **Add user** (correo y contraseña; marcar *Auto Confirm User*).
2. SQL Editor (queda como asesor; agregue `rol` para otro):
   ```sql
   INSERT INTO public.personal_autorizado (user_id, correo, nombre)
   SELECT id, email, 'Nombre de la persona' FROM auth.users WHERE email = 'correo@ejemplo.com';
   ```
3. Recomendado: Authentication → Sign In / Providers → desactivar **Allow new users to sign up**. Aunque alguien se
   registre, no ve datos; desactivarlo evita cuentas que no sirven.

Para quitar el acceso: **Dar de baja** en Usuarios (o `UPDATE public.personal_autorizado SET activo = false WHERE correo = …`).

## Probar sin Supabase
Con `publico/` servida en este computador, `http://127.0.0.1:<puerto>/?demo` abre la app sin inicio de sesión y guarda
los datos solo en el navegador (el modo demostración solo funciona en localhost).

Es un prototipo académico: el resultado es una estimación de apoyo, no una decisión de admisión.
