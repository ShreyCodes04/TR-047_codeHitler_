import SplineBackground from "./SplineBackground";
import TopNav from "./TopNav";

const SPLINE_SCENE_URL = process.env.NEXT_PUBLIC_SPLINE_SCENE_URL ?? "";

export default function HeroPage() {
  return (
    <>
      <SplineBackground sceneUrl={SPLINE_SCENE_URL} />
      <TopNav />

      <main className="relative mx-auto w-full max-w-7xl px-4 pb-16 pt-10 sm:px-6 lg:px-8">
        <section className="min-h-[calc(100vh-56px)]">
          <div className="flex min-h-[calc(100vh-96px)] items-center">
            <div className="max-w-2xl space-y-7 pt-8 sm:pt-14">
              <div className="inline-flex items-center gap-2 rounded-full border border-signal/30 bg-signal/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.28em] text-signal">
                AI Log Analysis
              </div>

              <div className="space-y-4">
                <h1 className="text-4xl font-semibold leading-tight text-white sm:text-6xl">
                  Your incident report, built from logs in minutes.
                </h1>
                <p className="max-w-xl text-sm leading-7 text-slate-200 sm:text-base">
                  Upload multi-service logs, define the incident window, and let the pipeline
                  correlate events, rank suspects, and generate a structured postmortem.
                </p>
              </div>

              <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                <a
                  href="/dashboard"
                  className="inline-flex items-center justify-center rounded-2xl bg-gradient-to-r from-signal via-teal-300 to-cyan-300 px-6 py-3 text-sm font-semibold text-slate-950 transition hover:brightness-110"
                >
                  Get Started
                </a>
                <a
                  href="/#how-it-works"
                  className="inline-flex items-center justify-center rounded-2xl border border-white/10 bg-white/[0.04] px-6 py-3 text-sm font-semibold text-slate-100 transition hover:border-signal/40"
                >
                  How It Works
                </a>
              </div>

              <div className="grid gap-4 sm:grid-cols-3">
                <Stat label="Inputs" value="Multi-source logs" />
                <Stat label="Correlation" value="Templates + time" />
                <Stat label="Output" value="Postmortem JSON" />
              </div>
            </div>
          </div>
        </section>

        <section id="how-it-works" className="scroll-mt-24 pt-10">
          <div className="mb-6">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">
              How It Works
            </p>
            <h2 className="mt-3 text-2xl font-semibold text-white sm:text-3xl">
              Correlate. Rank. Report.
            </h2>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-200">
              A pragmatic pipeline that stays fast on large incidents and produces output engineers can
              act on.
            </p>
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            <Step
              title="1. Parse"
              body="Drain3 mines templates and extracts variables so you can reason about patterns, not noise."
            />
            <Step
              title="2. Correlate"
              body="Events are formed using time proximity, template similarity, and service identity."
            />
            <Step
              title="3. Detect + Report"
              body="Anomaly scoring ranks suspects, then Gemini generates a deterministic JSON postmortem."
            />
          </div>
        </section>

        <section id="faqs" className="scroll-mt-24 pt-12">
          <div className="mb-6">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">FAQs</p>
            <h2 className="mt-3 text-2xl font-semibold text-white sm:text-3xl">
              Common questions
            </h2>
          </div>

          <div className="grid gap-4">
            <Faq
              q="Do I need to log in to generate a report?"
              a="Login is available for user sessions. Your backend can be configured to require auth for report generation if you want."
            />
            <Faq
              q="What timestamp formats are supported?"
              a="ISO formats (including minute precision from datetime-local), epoch seconds/millis, and common syslog formats."
            />
            <Faq
              q="Is the postmortem output structured?"
              a="Yes. The LLM is constrained to output valid JSON with summary, timeline, root cause, impact, and action items."
            />
            <Faq
              q="What if the Spline scene doesn’t load?"
              a="The page still works. The background falls back to a grid + gradient atmosphere."
            />
          </div>
        </section>
      </main>
    </>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-3xl border border-white/10 bg-white/[0.05] px-4 py-5">
      <p className="text-xs uppercase tracking-[0.22em] text-slate-500">{label}</p>
      <p className="mt-3 text-lg font-semibold text-white">{value}</p>
    </div>
  );
}

function Step({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-[28px] border border-white/10 bg-slate-950/50 p-6 shadow-panel backdrop-blur-sm">
      <p className="text-lg font-semibold text-white">{title}</p>
      <p className="mt-3 text-sm leading-7 text-slate-300">{body}</p>
    </div>
  );
}

function Faq({ q, a }: { q: string; a: string }) {
  return (
    <details className="group rounded-[28px] border border-white/10 bg-slate-950/50 px-6 py-5 shadow-panel backdrop-blur-sm">
      <summary className="cursor-pointer list-none text-sm font-semibold text-white">
        <span className="inline-flex items-center gap-3">
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.05] text-xs text-slate-200">
            ?
          </span>
          {q}
        </span>
      </summary>
      <p className="mt-4 text-sm leading-7 text-slate-300">{a}</p>
    </details>
  );
}
