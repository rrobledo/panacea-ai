// Cliente del backend FastAPI. Corre en el navegador: la cookie de sesión (panacea.sesion) viaja sola,
// porque /api/* es el mismo origen.

export type Perfil = { id: string; nombre: string; descripcion: string };
export type DatosUsuario = { usuario: { email: string; admin: boolean }; perfiles: Perfil[] };

export type Conversacion = {
  id: string;
  perfil: string;
  titulo: string;
  estado: "lista" | "en_curso" | "esperando_aclaracion";
  usuario: string;
  creada: string;
  actualizada: string;
};

export type Brief = {
  titulo: string;
  objetivo: string;
  periodo: string;
  secciones: string[];
  metricas: string[];
  audiencia: string;
};

export type Pregunta = {
  id: string;
  texto: string;
  tipo: "opcion" | "multiple" | "texto" | "fecha";
  opciones: string[];
  recomendada?: string | string[] | null;
};

export type RespuestaAclaracion = {
  decision: "aprobado" | "ajustar";
  respuestas: { id: string; pregunta: string; respuesta: string | string[] | null }[];
  comentario?: string;
};

export type Item =
  | { tipo: "usuario"; texto: string }
  | { tipo: "agente"; texto: string }
  | {
      tipo: "paso";
      id: string;
      nombre: string;
      argumentos: string;
      duracion_ms: number | null;
      es_error: boolean | null;
      filas?: number | null;
      en_curso?: boolean;
    }
  | { tipo: "aclaraciones"; id: string; brief: Brief; preguntas: Pregunta[]; respuesta: RespuestaAclaracion | null }
  | { tipo: "artifact"; id: string; version: number; titulo: string; url: string }
  | { tipo: "aviso"; texto: string }
  | { tipo: "error"; texto: string };

export type DetalleConversacion = {
  conversacion: Conversacion;
  aclaracion_pendiente: ({ tool_use_id: string; brief: Brief; preguntas: Pregunta[] }) | null;
  items: Item[];
};

export class ErrorApi extends Error {
  constructor(
    public status: number,
    mensaje: string,
  ) {
    super(mensaje);
  }
}

async function detalle(r: Response): Promise<string> {
  try {
    const j = await r.json();
    if (typeof j?.detail === "string") return j.detail;
    if (Array.isArray(j?.detail)) return "Pedido inválido";
  } catch {
    // sin cuerpo JSON
  }
  return r.status >= 500 ? "Error del servidor. Probá de nuevo en un rato." : r.statusText || `Error ${r.status}`;
}

async function pedir(ruta: string, init?: RequestInit): Promise<Response> {
  const r = await fetch(ruta, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (r.status === 401) {
    // La sesión venció: volver a entrar y regresar a esta página.
    window.location.href = `/login?destino=${encodeURIComponent(window.location.pathname)}`;
    throw new ErrorApi(401, "Tu sesión venció");
  }
  if (!r.ok) throw new ErrorApi(r.status, await detalle(r));
  return r;
}

export async function obtener<T>(ruta: string): Promise<T> {
  return (await pedir(ruta)).json() as Promise<T>;
}

/** POST que responde con SSE (chat y aclaraciones). */
export function abrirTurno(ruta: "/api/chat" | "/api/clarify", cuerpo: unknown, signal: AbortSignal) {
  return pedir(ruta, { method: "POST", body: JSON.stringify(cuerpo), signal });
}

export const NOMBRES_HERRAMIENTAS: Record<string, string> = {
  perfil_datos: "Perfil de los datos",
  describir_tabla: "Estructura de la tabla",
  resumen_ventas: "Resumen de ventas",
  comparar_periodos: "Comparación de períodos",
  clientes_inactivos: "Clientes inactivos",
  productos_asociados: "Productos asociados",
  proyectar_ventas: "Proyección de ventas",
  consultar: "Consulta SQL",
  solicitar_aclaraciones: "Aclaraciones",
  generar_artifact: "Generar reporte",
  editar_artifact: "Editar reporte",
};
