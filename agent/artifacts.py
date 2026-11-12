"""
Composición y validación del HTML de los artifacts.

El modelo manda contenido estructurado (resumen, KPIs, secciones con texto, tabla o gráfico,
estrategias) y opcionalmente HTML propio por sección; acá se arma el documento sobre la plantilla de
Panacea y se valida antes de guardarlo: scripts externos solo de cdn.jsdelivr.net y nada que parezca
una credencial o una cadena de conexión.
"""

import html
import json
import os
import re
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy.engine import make_url

from agent.almacen import ZONA

PLANTILLA = Path(__file__).resolve().parent / "plantillas" / "reporte.html"
DOMINIOS_SCRIPT = {"cdn.jsdelivr.net"}

# Se sirve en el visor con esta política y dentro de <iframe sandbox="allow-scripts">.
# `sandbox` en la propia CSP aísla el documento aunque se abra la URL directamente.
CSP = ("default-src 'none'; script-src 'unsafe-inline' https://cdn.jsdelivr.net; "
       "style-src 'unsafe-inline'; img-src data:; font-src data:; sandbox allow-scripts")

_CONEXION = re.compile(r"\b(?:postgres(?:ql)?|mysql|mariadb|mssql|oracle|mongodb(?:\+srv)?|redis)"
                       r"(?:\+\w+)?://", re.I)
_VARIABLES_SECRETAS = re.compile(r"^(DB_URL_\w+|DATABASE_URL\w*|POSTGRES_\w+|PG\w*PASSWORD|"
                                 r"\w*(SECRET|PASSWORD|API_KEY|TOKEN)\w*)$")


class ArtifactInvalido(ValueError):
    pass


# ---------------------------------------------------------------- validación
class _Recursos(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.externos: list[tuple[str, str]] = []  # (etiqueta, url)
        self.prohibidas: set[str] = set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "script" and a.get("src"):
            self.externos.append(("script", a["src"]))
        elif tag == "link" and a.get("href"):
            self.externos.append(("link", a["href"]))
        elif tag in ("iframe", "object", "embed", "base", "frame", "frameset"):
            self.prohibidas.add(tag)
        elif tag == "meta" and (a.get("http-equiv") or "").lower() == "refresh":
            self.prohibidas.add("meta refresh")

    handle_startendtag = handle_starttag


def secretos_del_entorno(entorno=None) -> dict[str, str]:
    """valor secreto → variable de la que sale (incluye la clave de cada URL de base). Más largos primero."""
    entorno = os.environ if entorno is None else entorno
    out = {}
    for nombre, valor in entorno.items():
        if not valor or not _VARIABLES_SECRETAS.match(nombre):
            continue
        if len(valor) >= 8:
            out[valor] = nombre
        if "://" in valor:
            try:
                clave = make_url(valor).password
            except Exception:
                clave = None
            if clave and len(clave) >= 6:
                out[str(clave)] = nombre
    return dict(sorted(out.items(), key=lambda kv: -len(kv[0])))


def validar_html(documento: str, secretos: dict[str, str] | None = None) -> None:
    """Lanza ArtifactInvalido si el HTML carga recursos de otros dominios o contiene credenciales."""
    p = _Recursos()
    p.feed(documento)
    p.close()
    for tag, url in p.externos:
        partes = urlsplit(url.strip())
        if not partes.scheme and not partes.netloc:
            raise ArtifactInvalido(f"<{tag}> con ruta relativa ({url[:80]}): el reporte debe ser autocontenido")
        if partes.scheme != "https" or (partes.hostname or "") not in DOMINIOS_SCRIPT:
            raise ArtifactInvalido(f"<{tag}> desde un dominio no permitido: {partes.hostname or url[:80]}. "
                                   f"Solo se permite {', '.join(sorted(DOMINIOS_SCRIPT))}")
    if p.prohibidas:
        raise ArtifactInvalido(f"Etiquetas no permitidas en el reporte: {', '.join(sorted(p.prohibidas))}")
    if _CONEXION.search(documento):
        raise ArtifactInvalido("El reporte contiene una cadena de conexión a base de datos")
    for valor, nombre in (secretos if secretos is not None else secretos_del_entorno()).items():
        if valor in documento:
            raise ArtifactInvalido(f"El reporte contiene el valor de la variable {nombre}")


# ---------------------------------------------------------------- composición
_e = html.escape


def _texto(t: str) -> str:
    """Texto simple → HTML: párrafos, viñetas con '- ' y **negrita**."""
    bloques = []
    for parrafo in re.split(r"\n\s*\n", t.strip()):
        lineas = [l.strip() for l in parrafo.splitlines() if l.strip()]
        if lineas and all(l.startswith(("- ", "• ")) for l in lineas):
            bloques.append("<ul>" + "".join(f"<li>{_en_linea(l[2:])}</li>" for l in lineas) + "</ul>")
        elif lineas:
            bloques.append(f"<p>{_en_linea(' '.join(lineas))}</p>")
    return "".join(bloques)


def _en_linea(t: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", _e(t))


def _numero(valor, formato: str) -> str:
    if valor is None:
        return "—"
    return f'<span data-v="{_e(repr(float(valor)) if isinstance(valor, (int, float)) else str(valor))}" ' \
           f'data-f="{_e(formato)}">{_e(str(valor))}</span>'


def _kpis(kpis: list[dict]) -> str:
    tarjetas = []
    for k in kpis:
        cmp = ""
        if k.get("variacion") is not None:
            cmp = f'<span class="delta" data-delta="{float(k["variacion"])!r}"></span>'
        if k.get("comparacion"):
            cmp += f" {_e(k['comparacion'])}"
        tarjetas.append(f'<div class="kpi"><span class="lbl">{_e(k["etiqueta"])}</span>'
                        f'<span class="val">{_numero(k["valor"], k.get("formato", "numero"))}</span>'
                        + (f'<span class="cmp">{cmp.strip()}</span>' if cmp else "") + "</div>")
    return f'<div class="kpis">{"".join(tarjetas)}</div>'


def _tabla(t: dict) -> str:
    formatos = t.get("formatos") or []
    cab = "".join(f'<th{" class=r" if i < len(formatos) and formatos[i] != "texto" else ""}>{_e(c)}</th>'
                  for i, c in enumerate(t["columnas"]))
    filas = []
    for fila in t["filas"]:
        celdas = []
        for i, v in enumerate(fila):
            f = formatos[i] if i < len(formatos) else "texto"
            if f != "texto" and isinstance(v, (int, float)) and not isinstance(v, bool):
                celdas.append(f'<td data-v="{float(v)!r}" data-f="{_e(f)}">{_e(str(v))}</td>')
            else:
                celdas.append(f"<td>{_e('' if v is None else str(v))}</td>")
        filas.append("<tr>" + "".join(celdas) + "</tr>")
    return f'<div class="tbl"><table><thead><tr>{cab}</tr></thead><tbody>{"".join(filas)}</tbody></table></div>'


def componer(contenido: dict, *, perfil: str, fecha: datetime | None = None) -> str:
    """Arma el documento completo. `contenido` es la entrada validada de generar/editar_artifact."""
    fecha = (fecha or datetime.now(ZONA)).astimezone(ZONA)
    graficos, cuerpo = [], []

    if contenido.get("resumen"):
        items = "".join(f"<li><span>{_en_linea(h)}</span></li>" for h in contenido["resumen"])
        cuerpo.append('<section><span class="eyebrow">Resumen ejecutivo</span>'
                      f'<h2>Hallazgos principales</h2><ol class="findings">{items}</ol></section>')
    if contenido.get("kpis"):
        cuerpo.append(f'<section><span class="eyebrow">Indicadores</span>{_kpis(contenido["kpis"])}</section>')

    for i, s in enumerate(contenido.get("secciones") or []):
        partes = [f"<h2>{_e(s['titulo'])}</h2>"]
        if s.get("texto"):
            partes.append(f'<div class="texto">{_texto(s["texto"])}</div>')
        if s.get("grafico"):
            g = dict(s["grafico"], id=f"g{i}")
            graficos.append(g)
            nota = f"<figcaption>{_e(g['nota'])}</figcaption>" if g.get("nota") else ""
            partes.append(f'<figure><div class="chart"><canvas id="g{i}" role="img" '
                          f'aria-label="{_e(g.get("titulo") or s["titulo"])}"></canvas></div>{nota}</figure>')
        if s.get("tabla"):
            partes.append(_tabla(s["tabla"]))
        if s.get("html"):
            partes.append(f'<div class="libre">{s["html"]}</div>')
        cuerpo.append(f'<section>{"".join(partes)}</section>')

    if contenido.get("estrategias"):
        tarjetas = []
        for est in contenido["estrategias"]:
            tarjetas.append(
                f'<article class="strat"><div class="top"><h3>{_e(est["titulo"])}</h3>'
                f'<span class="pill {_e(est["prioridad"])}">Prioridad {_e(est["prioridad"])}</span></div>'
                '<dl class="chain">'
                f'<div><dt>Dato</dt><dd>{_en_linea(est["dato"])}</dd></div>'
                f'<div><dt>Acción</dt><dd>{_en_linea(est["accion"])}</dd></div>'
                f'<div><dt>Impacto estimado</dt><dd class="impact">{_e(est["impacto"])}</dd></div>'
                f'<div><dt>KPI</dt><dd>{_e(est["kpi"])}</dd></div></dl></article>')
        cuerpo.append('<section><span class="eyebrow">Qué hacer</span><h2>Estrategias priorizadas</h2>'
                      f'<div class="strats">{"".join(tarjetas)}</div></section>')
    if contenido.get("nota_metodologica"):
        cuerpo.append('<section class="method"><h2>Nota metodológica</h2>'
                      f'<div class="texto">{_texto(contenido["nota_metodologica"])}</div></section>')

    meta = [f"<span>{_e(contenido['periodo'])}</span>"] if contenido.get("periodo") else []
    meta.append(f"<span>Generado: {fecha:%d/%m/%Y}</span>")
    subtitulo = f'<p class="lede">{_e(contenido["subtitulo"])}</p>' if contenido.get("subtitulo") else ""
    # Dentro de <script>, "</" cortaría el bloque: se escapa.
    datos = json.dumps(graficos, ensure_ascii=False).replace("</", "<\\/")
    reemplazos = {"{{titulo}}": _e(contenido["titulo"]), "{{perfil}}": _e(perfil), "{{subtitulo}}": subtitulo,
                  "{{meta}}": "".join(meta), "{{fecha}}": f"{fecha:%d/%m/%Y %H:%M}", "{{graficos}}": datos,
                  "{{cuerpo}}": "\n".join(cuerpo)}
    # Una sola pasada: el contenido del modelo nunca se vuelve a interpretar como marcador.
    plantilla = PLANTILLA.read_text(encoding="utf-8")
    return re.sub(r"\{\{\w+\}\}", lambda m: reemplazos.get(m.group(0), m.group(0)), plantilla)
