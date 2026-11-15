"use client";

// Dictado por voz con el reconocimiento del navegador (Web Speech API). No pasa por el backend:
// el texto reconocido se escribe en el cuadro del mensaje y el usuario lo revisa antes de enviarlo.
// Chrome y Edge envían el audio a su servicio de reconocimiento; Safari lo procesa en el equipo o en
// Apple. Firefox no lo soporta: ahí el botón no aparece.

import { Mic, MicOff } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { unirDictado } from "@/lib/dictado";

// Tipos mínimos: lib.dom no incluye el constructor con prefijo webkit.
type Resultado = { isFinal: boolean; 0: { transcript: string } };
type EventoResultado = { resultIndex: number; results: ArrayLike<Resultado> };
type EventoError = { error: string };
type Reconocedor = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((e: EventoResultado) => void) | null;
  onerror: ((e: EventoError) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
};
type ConstructorReconocedor = new () => Reconocedor;

function constructorDisponible(): ConstructorReconocedor | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as { SpeechRecognition?: ConstructorReconocedor; webkitSpeechRecognition?: ConstructorReconocedor };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

const MENSAJES_ERROR: Record<string, string> = {
  "not-allowed": "El navegador no dio permiso para usar el micrófono. Habilitalo en la barra de direcciones.",
  "service-not-allowed": "El navegador no permite el dictado en esta página.",
  "audio-capture": "No se encontró un micrófono.",
  "no-speech": "No se escuchó nada. Probá de nuevo, más cerca del micrófono.",
  network: "El dictado necesita conexión a internet.",
};

export function useDictado(texto: string, setTexto: (t: string) => void) {
  const [soportado, setSoportado] = useState(false);
  const [escuchando, setEscuchando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const reconocedor = useRef<Reconocedor | null>(null);
  const base = useRef("");
  const textoActual = useRef(texto);
  textoActual.current = texto;

  // Se decide en el cliente: en el servidor no existe window y el HTML inicial no muestra el botón.
  useEffect(() => setSoportado(constructorDisponible() !== null), []);
  useEffect(() => () => reconocedor.current?.abort(), []);

  const detener = useCallback(() => reconocedor.current?.stop(), []);

  const empezar = useCallback(() => {
    const Ctor = constructorDisponible();
    if (!Ctor || reconocedor.current) return;
    const r = new Ctor();
    r.lang = "es-AR";
    r.continuous = true;
    r.interimResults = true;
    base.current = textoActual.current;
    let finales = "";
    r.onresult = (e) => {
      let provisorio = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const res = e.results[i];
        if (res.isFinal) finales = unirDictado(finales, res[0].transcript);
        else provisorio = unirDictado(provisorio, res[0].transcript);
      }
      setTexto(unirDictado(base.current, unirDictado(finales, provisorio)));
    };
    r.onerror = (e) => {
      if (e.error !== "aborted") setError(MENSAJES_ERROR[e.error] ?? "El dictado se cortó. Probá de nuevo.");
    };
    r.onend = () => {
      reconocedor.current = null;
      setEscuchando(false);
    };
    setError(null);
    reconocedor.current = r;
    try {
      r.start();
      setEscuchando(true);
    } catch {
      reconocedor.current = null;
      setError("No se pudo iniciar el dictado.");
    }
  }, [setTexto]);

  return { soportado, escuchando, error, empezar, detener };
}

export function BotonDictado({
  escuchando,
  deshabilitado,
  onEmpezar,
  onDetener,
}: {
  escuchando: boolean;
  deshabilitado: boolean;
  onEmpezar: () => void;
  onDetener: () => void;
}) {
  const etiqueta = escuchando ? "Terminar dictado" : "Dictar un mensaje de voz";
  return (
    <button
      type="button"
      onClick={escuchando ? onDetener : onEmpezar}
      disabled={deshabilitado && !escuchando}
      aria-label={etiqueta}
      aria-pressed={escuchando}
      title={etiqueta}
      className={`grid place-items-center size-9 rounded-xl disabled:opacity-40 ${
        escuchando ? "bg-bad text-bg motion-safe:animate-pulse" : "text-fg-2 hover:bg-surface-2 hover:text-fg"
      }`}
    >
      {escuchando ? <MicOff className="size-5" aria-hidden="true" /> : <Mic className="size-5" aria-hidden="true" />}
    </button>
  );
}
