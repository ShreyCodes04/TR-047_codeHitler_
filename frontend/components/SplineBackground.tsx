"use client";

import { Application } from "@splinetool/runtime";
import { useEffect, useRef, useState } from "react";

export default function SplineBackground({ sceneUrl }: { sceneUrl: string }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    if (!sceneUrl) return;

    let app: Application | null = null;
    let cancelled = false;

    (async () => {
      try {
        app = new Application(canvas);
        await app.load(sceneUrl);
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : "Failed to load Spline scene.");
      }
    })();

    return () => {
      cancelled = true;
      try {
        (app as unknown as { dispose?: () => void })?.dispose?.();
      } catch {
        // ignore
      }
      app = null;
    };
  }, [sceneUrl]);

  return (
    <>
      <div className="pointer-events-none fixed inset-0 -z-20">
        <canvas ref={canvasRef} className="h-full w-full" />
      </div>

      {!sceneUrl ? (
        <div className="pointer-events-none fixed inset-0 -z-10">
          <div className="absolute inset-0 bg-grid [background-size:90px_90px] opacity-35" />
          <div className="absolute -left-40 top-0 h-[560px] w-[560px] rounded-full bg-signal/10 blur-3xl" />
          <div className="absolute -right-40 top-10 h-[520px] w-[520px] rounded-full bg-gold/10 blur-3xl" />
        </div>
      ) : null}

      {error ? (
        <div className="pointer-events-none fixed bottom-6 left-1/2 z-50 w-[min(640px,calc(100vw-2rem))] -translate-x-1/2">
          <div className="rounded-3xl border border-rose-400/20 bg-rose-400/10 px-5 py-3 text-sm text-rose-100 backdrop-blur">
            Spline failed to load: {error}
          </div>
        </div>
      ) : null}
    </>
  );
}
