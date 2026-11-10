"""Conexión SEGURA de Python con Supabase para leer la tabla plana dataset_matricula.

Las credenciales NUNCA se escriben en el código ni se imprimen:
  - En el computador: archivo .env en la raíz del proyecto, excluido por .gitignore (plantilla: .env.example).
    Se puede crear con:  python src/s00_configurar_credenciales.py
  - En Google Colab: panel "Secretos" (icono de llave) con SUPABASE_URL y SUPABASE_KEY, con acceso al cuaderno.

SUPABASE_KEY es la clave PUBLICABLE del proyecto. En la base, la seguridad a nivel de fila (RLS) solo le permite
LEER dataset_matricula (sin datos personales); las otras 25 tablas están cerradas y nadie puede escribir con ella.
Así, aunque la clave se filtrara, solo se podría leer el dataset anonimizado.
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

TABLA = "dataset_matricula"
VARIABLES = ("SUPABASE_URL", "SUPABASE_KEY")
TAMANO_PAGINA = 1000          # la API de Supabase entrega como máximo 1.000 filas por petición
TIEMPO_LIMITE_S = 30          # si la red no responde, se desiste en vez de quedarse esperando


def en_colab() -> bool:
    try:
        import google.colab  # noqa: F401
        return True
    except ImportError:
        return False


def obtener_credenciales() -> tuple[str, str]:
    """Devuelve (url, clave) desde los Secretos de Colab o desde .env / variables de entorno.

    En Colab, la primera vez que un cuaderno lee un secreto aparece un aviso para darle acceso: hay que aceptarlo
    (mientras no se acepte, la celda espera). Los errores explican qué falta, nunca muestran los valores.
    """
    problemas = []
    if en_colab():
        from google.colab import userdata
        valores = {}
        for v in VARIABLES:
            try:
                valores[v] = (userdata.get(v) or "").strip()
            except Exception as e:                  # SecretNotFoundError / NotebookAccessError
                valores[v] = ""
                motivo = ("el cuaderno no tiene acceso: active 'Acceso del notebook'" if "Access" in type(e).__name__
                          else "no existe un secreto con ese nombre exacto")
                problemas.append(f"{v}: {motivo}")
        donde = "los Secretos de Colab (icono de llave, con 'Acceso del notebook' activado)"
    else:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).resolve().parents[1] / ".env")
        valores = {v: os.environ.get(v, "").strip() for v in VARIABLES}
        donde = "el archivo .env (python src/s00_configurar_credenciales.py o copia de .env.example)"
    problemas += [f"{v}: está vacío" for v, x in valores.items() if not x and not any(p.startswith(v) for p in problemas)]
    url, clave = valores["SUPABASE_URL"], valores["SUPABASE_KEY"]
    if url and not (url.startswith("https://") and url.rstrip("/").endswith(".supabase.co")):
        problemas.append("SUPABASE_URL: no es la URL del proyecto (debe ser https://<proyecto>.supabase.co; "
                         "no la cadena postgresql:// del pooler)")
    if clave.lower().startswith(("postgres://", "postgresql://")):
        problemas.append("SUPABASE_KEY: es la cadena del pooler; aquí va la clave PUBLICABLE (sb_publishable_...)")
    elif clave.startswith("sb_secret_"):
        problemas.append("SUPABASE_KEY: es la clave SECRETA; use la PUBLICABLE (sb_publishable_...)")
    if problemas:
        raise RuntimeError(f"Credenciales incompletas en {donde}: " + "; ".join(problemas) + ".")
    return url, clave


def crear_cliente(url: str | None = None, clave: str | None = None):
    """Cliente de la API de Supabase con tiempo límite. La clave se usa en memoria y no se muestra."""
    from supabase import ClientOptions, create_client
    if url is None or clave is None:
        url, clave = obtener_credenciales()
    return create_client(url, clave, options=ClientOptions(postgrest_client_timeout=TIEMPO_LIMITE_S))


def leer_dataset_matricula(cliente, tabla: str = TABLA) -> pd.DataFrame:
    """Lee la tabla completa en páginas de 1.000 filas (límite de la API), ordenada por inscripcion_id."""
    filas, inicio = [], 0
    while True:
        r = (cliente.table(tabla).select("*").order("inscripcion_id")
             .range(inicio, inicio + TAMANO_PAGINA - 1).execute())
        filas += r.data
        if len(r.data) < TAMANO_PAGINA:
            break
        inicio += TAMANO_PAGINA
    return pd.DataFrame(filas)


def probar_solo_lectura(cliente, tabla: str = TABLA) -> bool:
    """Intenta modificar la tabla con la clave publicable. Devuelve True si la base lo RECHAZA por permisos
    (código 42501 de PostgreSQL: permiso denegado). La fila -1 no existe, así que nada cambiaría de todos modos."""
    try:
        cliente.table(tabla).update({"punt_global": 0}).eq("inscripcion_id", -1).execute()
    except Exception as e:                           # APIError de la API de Supabase
        return getattr(e, "code", None) == "42501"
    return False
