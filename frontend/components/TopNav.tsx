"use client";

import { useEffect, useState } from "react";

export default function TopNav() {
  const [hasToken, setHasToken] = useState(false);

  useEffect(() => {
    setHasToken(Boolean(window.localStorage.getItem("auth_token")));
  }, []);

  const logout = () => {
    window.localStorage.removeItem("auth_token");
    window.location.href = "/";
  };

  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-slate-950/40 backdrop-blur">
      <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6 lg:px-8">
        <a href="/" className="flex items-center gap-3">
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.06] text-sm font-semibold text-white">
            AI
          </span>
          <span className="hidden text-sm font-semibold tracking-wide text-white sm:block">
            Incident Report Generator
          </span>
        </a>

        <nav className="flex items-center gap-2">
          <NavLink href="/dashboard" label="Home" />
          <NavLink href="/#how-it-works" label="How It Works" />
          <NavLink href="/#faqs" label="FAQs" />
          {hasToken ? (
            <button
              type="button"
              onClick={logout}
              className="rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-slate-200 transition hover:border-rose-400/30 hover:text-white"
            >
              Log Out
            </button>
          ) : (
            <NavLink href="/login" label="Log In" emphasize />
          )}
        </nav>
      </div>
    </header>
  );
}

function NavLink({
  href,
  label,
  emphasize
}: {
  href: string;
  label: string;
  emphasize?: boolean;
}) {
  const base =
    "rounded-full px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] transition";
  const normal = "border border-white/10 bg-white/[0.04] text-slate-200 hover:border-signal/40 hover:text-white";
  const strong =
    "bg-gradient-to-r from-signal via-teal-300 to-cyan-300 text-slate-950 hover:brightness-110";

  return (
    <a href={href} className={`${base} ${emphasize ? strong : normal}`}>
      {label}
    </a>
  );
}

