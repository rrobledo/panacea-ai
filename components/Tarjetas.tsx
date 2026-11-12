"use client";

import { AlertTriangle, CircleAlert, Download, ExternalLink, FileBarChart2, LoaderCircle, Wrench } from "lucide-react";

import { NOMBRES_HERRAMIENTAS, type Item } from "@/lib/api";

type ItemDe<T extends Item["tipo"]> = Extract<Item, { tipo: T }>;

function duracion(ms: number | null): string {
  if (ms == null) return "";
  return ms < 1000 ? `${ms} ms` : `${(ms / 1000).toLocaleString("es-AR", { maximumFractionDigits: 1 })} s`;
}

export function Paso({ paso }: { paso: ItemDe<"paso"> }) {
  const nombre = NOMBRES_HERRAMIENTAS[paso.nombre] ?? paso.nombre;
  return (
    <div className="flex items-center gap-2 text-sm text-fg-2 min-w-0" title={paso.argumentos}>
      {paso.en_curso ? (
        <LoaderCircle className="size-4 shrink-0 animate-spin text-accent" aria-hidden="true" />
      ) : paso.es_error ? (
        <CircleAlert className="size-4 shrink-0 text-bad" aria-hidden="true" />
      ) : (
        <Wrench className="size-4 shrink-0 text-muted" aria-hidden="true" />
      )}
      <span className="font-medium text-fg whitespace-nowrap">{nombre}</span>
      <span className="truncate text-muted font-mono text-xs hidden sm:inline">{paso.argumentos}</span>
      <span className="ml-auto shrink-0 text-xs text-muted tabular-nums">
        {paso.en_curso
          ? "consultando…"
          : [
              paso.es_error ? "con error" : null,
              paso.filas != null ? `${paso.filas.toLocaleString("es-AR")} filas` : null,
              duracion(paso.duracion_ms),
            ]
              .filter(Boolean)
              .join(" · ")}
      </span>
    </div>
  );
}

export function ArtifactCard({ item }: { item: ItemDe<"artifact"> }) {
  const html = `/api/artifacts/${item.id}/html?version=${item.version}`;
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-line bg-surface p-4">
      <FileBarChart2 className="size-6 text-accent shrink-0" aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <div className="font-semibold truncate">{item.titulo}</div>
        <div className="text-sm text-muted">Reporte · versión {item.version}</div>
      </div>
      <div className="flex gap-2">
        <a
          href={html}
          target="_blank"
          rel="noopener"
          className="inline-flex items-center gap-1.5 rounded-lg bg-accent text-accent-fg px-3 py-1.5 text-sm font-medium hover:opacity-90"
        >
          <ExternalLink className="size-4" aria-hidden="true" /> Abrir
        </a>
        <a
          href={`${html}&descargar=true`}
          className="inline-flex items-center gap-1.5 rounded-lg border border-line px-3 py-1.5 text-sm hover:border-accent"
        >
          <Download className="size-4" aria-hidden="true" /> Descargar
        </a>
      </div>
    </div>
  );
}

export function Nota({ item, onReintentar }: { item: ItemDe<"aviso"> | ItemDe<"error">; onReintentar?: () => void }) {
  const error = item.tipo === "error";
  const Icono = error ? CircleAlert : AlertTriangle;
  return (
    <div
      role={error ? "alert" : "status"}
      className={`flex flex-wrap items-center gap-2 rounded-lg px-3 py-2 text-sm ${error ? "bg-bad-soft text-bad" : "bg-warn-soft text-warn"}`}
    >
      <Icono className="size-4 shrink-0" aria-hidden="true" />
      <span className="flex-1 min-w-0">{item.texto}</span>
      {onReintentar && (
        <button type="button" onClick={onReintentar} className="underline underline-offset-2 font-medium">
          Reintentar
        </button>
      )}
    </div>
  );
}
