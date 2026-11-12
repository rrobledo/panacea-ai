"""
Validación de la sesión en el backend.

El login es el mismo que usa panacea-compras: lo hace panacea-produccion-backend (`/auth/google`), que
devuelve un JWT HS256 firmado con su SECRET_KEY (claims sub, email, role, exp). Next lo recibe en
/auth/callback, controla el email y lo guarda en la cookie httpOnly `panacea.sesion`. Este backend lo
valida con AUTH_SECRET, que tiene que ser el mismo valor que SECRET_KEY de ese backend. El token llega
en la cookie (mismo origen) o en `Authorization: Bearer`.
"""

import os

import jwt

COOKIE_SESION = "panacea.sesion"


class SesionInvalida(Exception):
    pass


def secreto() -> str:
    s = os.environ.get("AUTH_SECRET", "")
    if not s:
        raise RuntimeError("Falta AUTH_SECRET (el SECRET_KEY de panacea-produccion-backend)")
    return s


def token_de(headers, cookies) -> str | None:
    auth = headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    return cookies.get(COOKIE_SESION) or None


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
