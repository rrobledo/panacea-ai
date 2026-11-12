"use client";

import { ArrowUp, Square } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { useApp } from "@/components/AppContext";
import { ClarifyCard } from "@/components/ClarifyCard";
import { Markdown } from "@/components/Markdown";
import { ArtifactCard, Nota, Paso } from "@/components/Tarjetas";
import { ErrorApi, abrirTurno, obtener, type DetalleConversacion, type Item } from "@/lib/api";
import { aclaracionPendiente, aplicarEvento, responderAclaracion } from "@/lib/chat";
import { leerEventos } from "@/lib/sse";

const SUGERENCIAS = [
  "¿Cuánto vendimos el mes pasado contra el mismo mes del año anterior?",
  "¿Qué productos se compran juntos? Sugerí 3 combos.",
  "Listá los clientes que dejaron de comprar y armá una estrategia de recuperación.",
  "Reporte de ventas 2026 vs 2025 por lugar de venta, con proyección a fin de año.",
];

type Respuestas = Record<string, string | string[]>;

export function Chat({ conversacionId }: { conversacionId?: string }) {
  const { perfil, datos, refrescarConversaciones } = useApp();
  const [convId, setConvId] = useState<string | undefined>(conversacionId);
  const convIdRef = useRef(conversacionId);
  const [perfilConv, setPerfilConv] = useState<string | null>(null);
  const [items, setItems] = useState<Item[]>([]);
  const [cargando, setCargando] = useState(Boolean(conversacionId));
  const [noExiste, setNoExiste] = useState(false);
  const [enCurso, setEnCurso] = useState(false);
  const [texto, setTexto] = useState("");
  const abortar = useRef<AbortController | null>(null);
  const fondo = useRef<HTMLDivElement>(null);
  const pegadoAlFondo = useRef(true);
  const scroller = useRef<HTMLDivElement>(null);

  // Historial de una conversación existente.
  useEffect(() => {
    if (!conversacionId) return;
    let vigente = true;
    obtener<DetalleConversacion>(`/api/conversaciones/${conversacionId}`)
      .then((d) => {
        if (!vigente) return;
        setItems(d.items);
        setPerfilConv(d.conversacion.perfil);
      })
      .catch((e) => vigente && (e instanceof ErrorApi && e.status === 404 ? setNoExiste(true) : setItems([{ tipo: "error", texto: e.message }])))
      .finally(() => vigente && setCargando(false));
    return () => {
      vigente = false;
    };
  }, [conversacionId]);

  useEffect(() => () => abortar.current?.abort(), []);

  // Seguir el final mientras llega texto, salvo que el usuario haya subido a leer.
  useEffect(() => {
    if (pegadoAlFondo.current) fondo.current?.scrollIntoView({ block: "end" });
  }, [items]);

  const correrTurno = useCallback(
    async (ruta: "/api/chat" | "/api/clarify", cuerpo: Record<string, unknown>) => {
      const control = new AbortController();
      abortar.current = control;
      setEnCurso(true);
      pegadoAlFondo.current = true;
      try {
        const respuesta = await abrirTurno(ruta, cuerpo, control.signal);
        for await (const ev of leerEventos(respuesta)) {
          if (ev.tipo === "conversacion") {
            const id = String(ev.id);
            setPerfilConv(String(ev.perfil));
            if (!convIdRef.current) {
              // Conversación nueva: la URL pasa a /chat/<id> sin recargar la página.
              convIdRef.current = id;
              window.history.replaceState(null, "", `/chat/${id}`);
              refrescarConversaciones();
            }
            setConvId(id);
            continue;
          }
          setItems((its) => aplicarEvento(its, ev));
        }
      } catch (e) {
        if (control.signal.aborted) {
          setItems((its) => [...aplicarEvento(its, { tipo: "fin" }), { tipo: "aviso", texto: "Detuviste la respuesta. Podés seguir escribiendo." }]);
        } else {
          const mensaje = e instanceof ErrorApi ? e.message : "Se cortó la conexión. El turno se puede retomar.";
          setItems((its) => [...aplicarEvento(its, { tipo: "fin" }), { tipo: "error", texto: mensaje }]);
        }
      } finally {
        abortar.current = null;
        setEnCurso(false);
        refrescarConversaciones();
      }
    },
    [refrescarConversaciones],
  );

  const pendiente = aclaracionPendiente(items);

  function enviar(mensaje: string | null) {
    if (enCurso) return;
    const limpio = mensaje?.trim() || null;
    if (!convId && !limpio) return;
    setItems((its) => {
      let nuevos = its;
      // Un mensaje libre con una aclaración pendiente cuenta como ajuste (así lo trata el backend).
      if (limpio && pendiente) nuevos = responderAclaracion(nuevos, pendiente.id, { decision: "ajustar", respuestas: [], comentario: limpio });
      return limpio ? [...nuevos, { tipo: "usuario", texto: limpio }] : nuevos;
    });
    setTexto("");
    void correrTurno("/api/chat", convId ? { conversacion_id: convId, mensaje: limpio } : { perfil: perfil.id, mensaje: limpio });
  }

  function resolverAclaracion(decision: "aprobar" | "ajustar", respuestas: Respuestas, comentario?: string) {
    if (!pendiente || !convId || enCurso) return;
    const textos = Object.fromEntries(pendiente.preguntas.map((p) => [p.id, p.texto]));
    setItems((its) =>
      responderAclaracion(its, pendiente.id, {
        decision: decision === "aprobar" ? "aprobado" : "ajustar",
        respuestas: Object.entries(respuestas).map(([id, respuesta]) => ({ id, pregunta: textos[id] ?? id, respuesta })),
        comentario,
      }),
    );
    void correrTurno("/api/clarify", { conversacion_id: convId, tool_use_id: pendiente.id, decision, respuestas, comentario });
  }

  if (noExiste) {
    return <div className="h-full grid place-items-center text-fg-2 px-4 text-center">No existe la conversación o no tenés acceso.</div>;
  }

  const nombrePerfil = datos.perfiles.find((p) => p.id === (perfilConv ?? perfil.id))?.nombre ?? perfilConv;
  const ultimoEsError = items[items.length - 1]?.tipo === "error";

  return (
    <div className="h-full grid grid-rows-[1fr_auto]">
      <div
        ref={scroller}
        className="min-h-0 overflow-y-auto"
        onScroll={(e) => {
          const el = e.currentTarget;
          pegadoAlFondo.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
        }}
      >
        <div className="mx-auto max-w-3xl px-4 py-6 grid gap-4">
          {cargando ? (
            <p className="text-muted" aria-busy="true">Cargando conversación…</p>
          ) : items.length === 0 ? (
            <div className="grid gap-6 py-10">
              <div className="grid gap-2">
                <h1 className="text-2xl font-bold">¿Qué querés analizar?</h1>
                <p className="text-fg-2">
                  {nombrePerfil}: {perfil.descripcion || "preguntá en lenguaje natural."} Para un reporte, el agente te va a pedir que
                  confirmes el alcance antes de generarlo.
                </p>
              </div>
              <ul className="grid sm:grid-cols-2 gap-2">
                {SUGERENCIAS.map((s) => (
                  <li key={s}>
                    <button
                      type="button"
                      onClick={() => enviar(s)}
                      className="w-full h-full text-left rounded-xl border border-line bg-surface px-4 py-3 text-sm text-fg-2 hover:border-accent hover:text-fg"
                    >
                      {s}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            items.map((it, i) => {
              switch (it.tipo) {
                case "usuario":
                  return (
                    <div key={i} className="justify-self-end max-w-[85%] rounded-2xl rounded-br-md bg-accent-soft px-4 py-2.5 whitespace-pre-wrap">
                      {it.texto}
                    </div>
                  );
                case "agente":
                  return <Markdown key={i} texto={it.texto} />;
                case "paso":
                  return <Paso key={it.id} paso={it} />;
                case "aclaraciones":
                  return (
                    <ClarifyCard
                      key={it.id}
                      item={it}
                      activa={!enCurso && pendiente?.id === it.id}
                      onAprobar={(r) => resolverAclaracion("aprobar", r)}
                      onAjustar={(c, r) => resolverAclaracion("ajustar", r, c)}
                    />
                  );
                case "artifact":
                  return <ArtifactCard key={`${it.id}-${it.version}`} item={it} />;
                default:
                  return (
                    <Nota
                      key={i}
                      item={it}
                      onReintentar={it.tipo === "error" && i === items.length - 1 && convId && !enCurso ? () => enviar(null) : undefined}
                    />
                  );
              }
            })
          )}
          {enCurso && !ultimoEsError && items[items.length - 1]?.tipo !== "agente" && (
            <p className="text-sm text-muted animate-pulse" aria-live="polite">Pensando…</p>
          )}
          <div ref={fondo} />
        </div>
      </div>

      <form
        className="border-t border-line bg-bg px-4 py-3"
        onSubmit={(e) => {
          e.preventDefault();
          enviar(texto);
        }}
      >
        <div className="mx-auto max-w-3xl flex items-end gap-2 rounded-2xl border border-line bg-surface p-2 focus-within:border-accent focus-within:ring-2 focus-within:ring-accent/25">
          <label htmlFor="mensaje" className="sr-only">Mensaje</label>
          <textarea
            id="mensaje"
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault();
                enviar(texto);
              }
            }}
            rows={1}
            maxLength={20000}
            placeholder={pendiente ? "Escribí un ajuste, o respondé en la tarjeta…" : "Preguntá sobre ventas, clientes o pedí un reporte…"}
            className="flex-1 resize-none bg-transparent px-2 py-1.5 outline-none focus-visible:outline-none max-h-48 field-sizing-content"
          />
          {enCurso ? (
            <button
              type="button"
              onClick={() => abortar.current?.abort()}
              aria-label="Detener"
              title="Detener"
              className="grid place-items-center size-9 rounded-xl bg-fg text-bg"
            >
              <Square className="size-4" aria-hidden="true" />
            </button>
          ) : (
            <button
              type="submit"
              disabled={!texto.trim()}
              aria-label="Enviar"
              title="Enviar (Enter)"
              className="grid place-items-center size-9 rounded-xl bg-accent text-accent-fg disabled:opacity-40"
            >
              <ArrowUp className="size-5" aria-hidden="true" />
            </button>
          )}
        </div>
        <p className="mx-auto max-w-3xl mt-1.5 text-xs text-muted px-1">
          Enter para enviar, Shift+Enter para una línea nueva. El agente puede equivocarse: verificá los números importantes.
        </p>
      </form>
    </div>
  );
}
