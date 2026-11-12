"""
Validación de la sesión de Auth.js en el backend.

Auth.js se configura (task 4.2) con jwt.encode/decode propios que firman la sesión como JWT HS256
con AUTH_SECRET, en lugar del JWE por defecto. El backend la valida con el mismo secreto. El token
llega en la cookie de sesión (mismo origen) o en `Authorization: Bearer`.
"""

import os

import jwt

COOKIES_SESION = ("__Secure-authjs.session-token", "authjs.session-token")


class SesionInvalida(Exception):
    pass


def secreto() -> str:
    s = os.environ.get("AUTH_SECRET", "")
    if len(s) < 32:
        raise RuntimeError("AUTH_SECRET falta o tiene menos de 32 caracteres")
    return s


def token_de(headers, cookies) -> str | None:
    auth = headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    for nombre in COOKIES_SESION:
        if cookies.get(nombre):
            return cookies[nombre]
    return None


def email_de_token(token: str | None, clave: str | None = None) -> str:
    if not token:
        raise SesionInvalida("Sin sesión")
    try:
        datos = jwt.decode(token, clave or secreto(), algorithms=["HS256"],
                           options={"require": ["exp"]}, leeway=30)
    except jwt.PyJWTError as e:
        raise SesionInvalida(f"Sesión inválida: {e}") from None
    email = datos.get("email")
    if not isinstance(email, str) or "@" not in email:
        raise SesionInvalida("La sesión no tiene email")
    return email.strip().lower()
