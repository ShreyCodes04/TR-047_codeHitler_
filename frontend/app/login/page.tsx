"use client";

import { useState } from "react";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

export default function LoginPage() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isBusy, setIsBusy] = useState(false);

  const submit = async () => {
    setError("");
    setIsBusy(true);
    try {
      const endpoint = mode === "login" ? "/auth/login" : "/auth/register";
      const res = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      });
      const payload = (await res.json()) as { access_token?: string; detail?: string };
      if (!res.ok) {
        throw new Error(payload.detail || "Request failed.");
      }
      if (!payload.access_token) {
        throw new Error("No access token returned.");
      }
      window.localStorage.setItem("auth_token", payload.access_token);
      window.location.href = "/dashboard";
    } catch (e) {
      setError(e instanceof Error ? e.message : "Authentication failed.");
    } finally {
      setIsBusy(false);
    }
  };

  return (
    <main className="relative mx-auto flex min-h-screen w-full max-w-2xl flex-col justify-center px-4 py-10 sm:px-6">
      <div className="rounded-[32px] border border-white/10 bg-slate-950/50 p-6 shadow-panel backdrop-blur-sm sm:p-8">
        <div className="mb-6">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">
            {mode === "login" ? "Log In" : "Create Account"}
          </p>
          <h1 className="mt-3 text-3xl font-semibold text-white">Welcome back.</h1>
          <p className="mt-2 text-sm leading-7 text-slate-300">
            Use your email and password to {mode === "login" ? "sign in" : "register"}.
          </p>
        </div>

        <div className="space-y-4">
          <label className="block">
            <span className="mb-2 block text-sm font-medium text-slate-200">Email</span>
            <input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              type="email"
              className="w-full rounded-2xl border border-slate-700 bg-slate-950/70 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-signal"
              placeholder="you@company.com"
            />
          </label>

          <label className="block">
            <span className="mb-2 block text-sm font-medium text-slate-200">Password</span>
            <input
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              type="password"
              className="w-full rounded-2xl border border-slate-700 bg-slate-950/70 px-4 py-3 text-sm text-slate-100 outline-none transition focus:border-signal"
              placeholder="••••••••"
            />
          </label>

          <button
            type="button"
            onClick={submit}
            disabled={isBusy || !email || !password}
            className="flex w-full items-center justify-center rounded-2xl bg-gradient-to-r from-signal via-teal-300 to-cyan-300 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isBusy ? "Working..." : mode === "login" ? "Log In" : "Register"}
          </button>

          {error ? (
            <div className="rounded-2xl border border-rose-400/20 bg-rose-400/10 px-4 py-3 text-sm text-rose-100">
              {error}
            </div>
          ) : null}

          <div className="flex items-center justify-between gap-3 pt-2 text-sm text-slate-400">
            <a href="/" className="underline decoration-white/20 underline-offset-4 hover:text-white">
              Back to home
            </a>
            <button
              type="button"
              onClick={() => setMode(mode === "login" ? "register" : "login")}
              className="underline decoration-white/20 underline-offset-4 hover:text-white"
            >
              {mode === "login" ? "Create an account" : "I already have an account"}
            </button>
          </div>
        </div>
      </div>
    </main>
  );
}

