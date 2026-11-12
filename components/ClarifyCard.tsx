"use client";

import { Check, ClipboardList, PencilLine } from "lucide-react";
import { useState } from "react";

import type { Item, Pregunta } from "@/lib/api";

type Respuestas = Record<string, string | string[]>;
type ItemAclaracion = Extract<Item, { tipo: "aclaraciones" }>;

function inicial(preguntas: Pregunta[]): Respuestas {
  const r: Respuestas = {};
  for (const p of preguntas) {
    if (p.tipo === "multiple") r[p.id] = Array.isArray(p.recomendada) ? p.recomendada : p.recomendada ? [p.recomendada] : [];
    else r[p.id] = typeof p.recomendada === "string" ? p.recomendada : "";
  }
  return r;
}

function Chips({ titulo, valores }: { titulo: string; valores: string[] }) {
  if (!valores.length) return null;
  return (
    <div className="grid gap-1.5">
      <span className="text-xs font-mono uppercase tracking-[0.06em] text-muted">{titulo}</span>
      <ul className="flex flex-wrap gap-1.5">
        {valores.map((v) => (
          <li key={v} className="rounded-full bg-surface-2 px-2.5 py-0.5 text-sm">
            {v}
          </li>
        ))}
      </ul>
    </div>
  );
}

function CampoPregunta({ p, valor, onChange, deshabilitado }: {
  p: Pregunta;
  valor: string | string[];
  onChange: (v: string | string[]) => void;
  deshabilitado: boolean;
}) {
  const recomendada = (o: string) =>
    (Array.isArray(p.recomendada) ? p.recomendada.includes(o) : p.recomendada === o) ? (
      <span className="ml-1.5 text-xs text-accent">recomendada</span>
    ) : null;

  if (p.tipo === "opcion" || p.tipo === "multiple") {
    const multiple = p.tipo === "multiple";
    const elegidas = Array.isArray(valor) ? valor : [valor];
    return (
      <fieldset className="grid gap-1.5" disabled={deshabilitado}>
        <legend className="font-medium mb-1.5">{p.texto}</legend>
        {p.opciones.map((o) => (
          <label key={o} className="flex items-start gap-2 cursor-pointer">
            <input
              type={multiple ? "checkbox" : "radio"}
              name={`pregunta-${p.id}`}
              checked={elegidas.includes(o)}
              onChange={(e) =>
                onChange(multiple ? (e.target.checked ? [...elegidas, o] : elegidas.filter((x) => x !== o)) : o)
              }
              className="mt-1 accent-[var(--accent)]"
            />
            <span>
              {o}
              {recomendada(o)}
            </span>
          </label>
        ))}
      </fieldset>
    );
  }
  return (
    <label className="grid gap-1.5">
      <span className="font-medium">{p.texto}</span>
      {p.tipo === "fecha" ? (
        <input
          type="date"
          value={valor as string}
          onChange={(e) => onChange(e.target.value)}
          disabled={deshabilitado}
          className="justify-self-start rounded-lg border border-line bg-bg px-3 py-1.5"
        />
      ) : (
        <textarea
          value={valor as string}
          onChange={(e) => onChange(e.target.value)}
          disabled={deshabilitado}
          rows={2}
          placeholder={typeof p.recomendada === "string" ? p.recomendada : undefined}
          className="rounded-lg border border-line bg-bg px-3 py-2 resize-y"
        />
      )}
    </label>
  );
}

export function ClarifyCard({ item, activa, onAprobar, onAjustar }: {
  item: ItemAclaracion;
  activa: boolean; // es la pendiente y no hay un turno en curso
  onAprobar: (respuestas: Respuestas) => void;
  onAjustar: (comentario: string, respuestas: Respuestas) => void;
}) {
  const [respuestas, setRespuestas] = useState<Respuestas>(() => inicial(item.preguntas));
  const [ajustando, setAjustando] = useState(false);
  const [comentario, setComentario] = useState("");
  const { brief, respuesta } = item;
  const respondida = respuesta != null;

  return (
    <section className="rounded-xl border border-line bg-surface overflow-hidden" aria-label="Aclaraciones antes del reporte">
      <div className="p-4 sm:p-5 grid gap-4 border-b border-line bg-accent-soft/50">
        <div className="flex items-center gap-2 text-sm font-mono uppercase tracking-[0.06em] text-accent">
          <ClipboardList className="size-4" aria-hidden="true" /> Voy a generar
        </div>
        <div className="grid gap-1">
          <h3 className="text-lg font-semibold">{brief.titulo}</h3>
          <p className="text-fg-2">{brief.objetivo}</p>
        </div>
        <dl className="grid sm:grid-cols-2 gap-x-6 gap-y-2 text-sm">
          <div>
            <dt className="text-muted">Período</dt>
            <dd>{brief.periodo || "—"}</dd>
          </div>
          <div>
            <dt className="text-muted">Para</dt>
            <dd>{brief.audiencia || "—"}</dd>
          </div>
        </dl>
        <Chips titulo="Secciones" valores={brief.secciones} />
        <Chips titulo="Métricas" valores={brief.metricas} />
      </div>

      {respondida ? (
        <div className="p-4 sm:p-5 grid gap-3 text-sm">
          {respuesta.respuestas.filter((r) => r.respuesta != null && r.respuesta !== "").map((r) => (
            <div key={r.id}>
              <div className="text-muted">{r.pregunta}</div>
              <div>{Array.isArray(r.respuesta) ? r.respuesta.join(", ") : r.respuesta}</div>
            </div>
          ))}
          <div className={`flex items-center gap-2 font-medium ${respuesta.decision === "aprobado" ? "text-good" : "text-warn"}`}>
            {respuesta.decision === "aprobado" ? (
              <>
                <Check className="size-4" aria-hidden="true" /> Aprobado
              </>
            ) : (
              <>
                <PencilLine className="size-4" aria-hidden="true" /> Pediste ajustes{respuesta.comentario ? `: “${respuesta.comentario}”` : ""}
              </>
            )}
          </div>
        </div>
      ) : (
        <form
          className="p-4 sm:p-5 grid gap-5"
          onSubmit={(e) => {
            e.preventDefault();
            if (ajustando) {
              if (comentario.trim()) onAjustar(comentario.trim(), respuestas);
            } else onAprobar(respuestas);
          }}
        >
          {item.preguntas.map((p) => (
            <CampoPregunta
              key={p.id}
              p={p}
              valor={respuestas[p.id]}
              deshabilitado={!activa}
              onChange={(v) => setRespuestas((r) => ({ ...r, [p.id]: v }))}
            />
          ))}
          {ajustando && (
            <label className="grid gap-1.5">
              <span className="font-medium">¿Qué querés cambiar?</span>
              <textarea
                autoFocus
                value={comentario}
                onChange={(e) => setComentario(e.target.value)}
                rows={3}
                placeholder="Ej.: mejor por semana y sin la proyección"
                className="rounded-lg border border-line bg-bg px-3 py-2 resize-y"
              />
            </label>
          )}
          <div className="flex flex-wrap gap-2">
            {ajustando ? (
              <>
                <button type="submit" disabled={!activa || !comentario.trim()} className="rounded-lg bg-accent text-accent-fg px-4 py-2 font-medium disabled:opacity-50">
                  Enviar ajuste
                </button>
                <button type="button" onClick={() => setAjustando(false)} className="rounded-lg border border-line px-4 py-2 hover:border-accent">
                  Cancelar
                </button>
              </>
            ) : (
              <>
                <button type="submit" disabled={!activa} className="inline-flex items-center gap-2 rounded-lg bg-accent text-accent-fg px-4 py-2 font-medium disabled:opacity-50">
                  <Check className="size-4" aria-hidden="true" /> Aprobar y generar
                </button>
                <button type="button" disabled={!activa} onClick={() => setAjustando(true)} className="inline-flex items-center gap-2 rounded-lg border border-line px-4 py-2 hover:border-accent disabled:opacity-50">
                  <PencilLine className="size-4" aria-hidden="true" /> Ajustar
                </button>
              </>
            )}
          </div>
        </form>
      )}
    </section>
  );
}
