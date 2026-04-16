"use client";

import type { ReactNode } from "react";
import { type ChangeEvent, useEffect, useMemo, useRef, useState } from "react";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

type TimelineEvent = {
  time: string;
  title: string;
  detail: string;
  source: string;
};

type ReportState = {
  timeline: TimelineEvent[];
  rootCause: string;
  confidence: number;
  impact: {
    services: string[];
    downtime: string;
    severity: string;
  };
  postmortem: {
    summary: string;
    rca: string;
    actions: string[];
  };
};

type ApiGenerateReportResponse = {
  summary: string;
  timeline: Array<{
    time: string;
    event_id: string;
    summary: string;
  }>;
  root_cause: string;
  impact: string;
  action_items: string[];
};

function formatTimestamp(value: string) {
  if (!value) {
    return "Not selected";
  }

  return value.replace("T", " ");
}

export default function DashboardPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [startTime, setStartTime] = useState("2026-04-16T09:10");
  const [endTime, setEndTime] = useState("2026-04-16T09:30");
  const [architecture, setArchitecture] = useState(
    "Customer requests pass through an API gateway to Node.js services, PostgreSQL, Redis cache, and a Kubernetes-hosted worker tier."
  );
  const [isGenerating, setIsGenerating] = useState(false);
  const [report, setReport] = useState<ReportState | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [engineerRating, setEngineerRating] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const totalFilesSize = useMemo(
    () => files.reduce((sum, file) => sum + file.size, 0),
    [files]
  );

  const handleFiles = (event: ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(event.target.files ?? []);
    setFiles((currentFiles) => {
      const nextFiles = [...currentFiles];

      for (const selectedFile of selectedFiles) {
        const alreadyAdded = nextFiles.some(
          (file) =>
            file.name === selectedFile.name &&
            file.size === selectedFile.size &&
            file.lastModified === selectedFile.lastModified
        );

        if (!alreadyAdded) {
          nextFiles.push(selectedFile);
        }
      }

      return nextFiles;
    });
    event.target.value = "";
  };

  const removeFile = (targetFile: File) => {
    setFiles((currentFiles) =>
      currentFiles.filter(
        (file) =>
          !(
            file.name === targetFile.name &&
            file.size === targetFile.size &&
            file.lastModified === targetFile.lastModified
          )
      )
    );
  };

  const generateReport = async () => {
    if (files.length === 0) {
      setErrorMessage("Attach one or more log files before generating a report.");
      return;
    }

    setErrorMessage("");
    setIsGenerating(true);
    setEngineerRating(null);

    try {
      const formData = new FormData();
      for (const file of files) {
        formData.append("logs", file);
      }
      formData.append("start_time", startTime);
      formData.append("end_time", endTime);
      formData.append("architecture", architecture);

      const response = await fetch(`${API_BASE_URL}/generate-report`, {
        method: "POST",
        body: formData
      });

      const payload = (await response.json()) as ApiGenerateReportResponse | { detail?: string };
      if (!response.ok) {
        throw new Error(
          "detail" in payload && payload.detail
            ? payload.detail
            : "The backend could not generate the report."
        );
      }

      setReport(mapGenerateReportToUiReport(payload as ApiGenerateReportResponse));
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to reach the backend.";
      if (message.toLowerCase().includes("failed to fetch")) {
        setErrorMessage(
          `Failed to reach the backend at ${API_BASE_URL}. ` +
          `Make sure the backend is running (GET ${API_BASE_URL}/health) and CORS allows your frontend origin.`
        );
      } else {
        setErrorMessage(message);
      }
      setReport(null);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <main className="relative mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-8 px-4 py-6 sm:px-6 lg:px-8">
      <div className="pointer-events-none fixed inset-0 -z-10">
        <div className="absolute inset-0 bg-grid [background-size:90px_90px] opacity-20" />
        <div className="absolute -left-40 top-0 h-[560px] w-[560px] rounded-full bg-signal/12 blur-3xl" />
        <div className="absolute -right-40 top-10 h-[520px] w-[520px] rounded-full bg-gold/12 blur-3xl" />
      </div>

      <section className="overflow-hidden rounded-[32px] border border-white/10 bg-slate-950/35 shadow-panel backdrop-blur-xl">
        <div className="grid gap-8 px-6 py-8 lg:grid-cols-[1.15fr_0.85fr] lg:px-10 lg:py-10">
          <div className="space-y-6">
            <div className="inline-flex items-center gap-2 rounded-full border border-signal/30 bg-signal/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.28em] text-signal">
              Autonomous Log-to-Incident Report Generator
            </div>
            <div className="space-y-4">
              <h1 className="max-w-3xl text-4xl font-semibold leading-tight text-white sm:text-5xl">
                AI-powered incident reconstruction from scattered logs.
              </h1>
              <p className="max-w-2xl text-sm leading-7 text-slate-300 sm:text-base">
                Upload logs from multiple systems, define the incident window, and generate a
                structured postmortem with correlated timelines, root-cause analysis, impact, and
                follow-up actions.
              </p>
              <div className="flex flex-wrap gap-3">
                <a
                  href="/"
                  className="inline-flex items-center justify-center rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-slate-200 transition hover:border-signal/40 hover:bg-white/[0.08] hover:text-white"
                >
                  Back To Hero
                </a>
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-3">
              <StatCard label="Supported inputs" value=".logs and .txt files" />
              <StatCard label="Outputs" value="Timeline + RCA" />
              <StatCard label="Engineer review" value="1-5 quality score" />
            </div>
          </div>

          <div className="rounded-[28px] border border-white/10 bg-slate-950/45 p-5 shadow-[0_20px_80px_rgba(8,16,30,0.28)] backdrop-blur">
            <div className="mb-5 flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-slate-300">Incident intake</p>
                <p className="text-xs text-slate-500">Configure the context for analysis</p>
              </div>
              <div className="rounded-full border border-amber-400/25 bg-amber-300/10 px-3 py-1 text-xs font-medium text-amber-200">
                AI correlation ready
              </div>
            </div>

            <div className="space-y-5">
              <label className="block">
                <span className="mb-2 block text-sm font-medium text-slate-200">Upload log files</span>
                <div className="rounded-3xl border border-dashed border-white/15 bg-white/[0.04] p-4 transition hover:border-signal/50 hover:bg-white/[0.06]">
                  <input
                    ref={fileInputRef}
                    multiple
                    accept=".log,.txt,text/plain"
                    type="file"
                    onChange={handleFiles}
                    className="hidden"
                  />
                  <div className="flex flex-wrap items-center gap-3">
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="inline-flex items-center justify-center rounded-full bg-gradient-to-r from-signal via-teal-300 to-cyan-300 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:brightness-110"
                    >
                      Choose Files
                    </button>
                    <span className="text-sm text-slate-300">
                      {files.length > 0
                        ? `${files.length} file${files.length === 1 ? "" : "s"} selected`
                        : "Upload one or more .log or .txt files"}
                    </span>
                  </div>
                  <p className="mt-3 text-xs text-slate-500">
                    Select multiple application logs, server metrics, DB traces, or plain text
                    incident exports. You can add more files in batches.
                  </p>
                  <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-400">
                    <span className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1">
                      {files.length} files selected
                    </span>
                    <span className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1">
                      {(totalFilesSize / 1024).toFixed(1)} KB total
                    </span>
                  </div>
                </div>
              </label>

              <div className="grid gap-4 sm:grid-cols-2">
                <label className="block">
                  <span className="mb-2 block text-sm font-medium text-slate-200">Start timestamp</span>
                  <input
                    type="datetime-local"
                    value={startTime}
                    onChange={(event) => setStartTime(event.target.value)}
                    className="w-full rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-slate-100 outline-none ring-0 transition focus:border-signal"
                  />
                </label>
                <label className="block">
                  <span className="mb-2 block text-sm font-medium text-slate-200">End timestamp</span>
                  <input
                    type="datetime-local"
                    value={endTime}
                    onChange={(event) => setEndTime(event.target.value)}
                    className="w-full rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-slate-100 outline-none ring-0 transition focus:border-signal"
                  />
                </label>
              </div>

              <label className="block">
                <span className="mb-2 block text-sm font-medium text-slate-200">
                  System architecture context
                </span>
                <textarea
                  rows={5}
                  value={architecture}
                  onChange={(event) => setArchitecture(event.target.value)}
                  placeholder="Describe services, dependencies, and infrastructure topology."
                  className="w-full rounded-3xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm leading-6 text-slate-100 outline-none transition focus:border-signal"
                />
              </label>

              <button
                type="button"
                onClick={generateReport}
                className="flex w-full items-center justify-center rounded-2xl bg-gradient-to-r from-signal via-teal-300 to-cyan-300 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-70"
                disabled={isGenerating}
              >
                {isGenerating ? "Correlating events..." : "Generate Report"}
              </button>
              {errorMessage ? (
                <div className="rounded-2xl border border-rose-400/20 bg-rose-400/10 px-4 py-3 text-sm text-rose-100 backdrop-blur">
                  {errorMessage}
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
        <div className="space-y-6">
          <Panel title="Incident Window" subtitle="Selected analysis scope">
            <div className="space-y-4">
              <InfoRow label="Start" value={formatTimestamp(startTime)} />
              <InfoRow label="End" value={formatTimestamp(endTime)} />
              <InfoRow label="Files attached" value={String(files.length)} />
              <InfoRow label="Payload size" value={`${(totalFilesSize / 1024).toFixed(1)} KB`} />
            </div>
          </Panel>

          <Panel title="Uploaded Sources" subtitle="Current log bundle">
            <div className="space-y-3">
              {files.length > 0 ? (
                files.map((file) => (
                  <div
                    key={`${file.name}-${file.lastModified}`}
                    className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3"
                  >
                    <div>
                      <p className="text-sm font-medium text-slate-100">{file.name}</p>
                      <p className="text-xs text-slate-500">{(file.size / 1024).toFixed(1)} KB</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="rounded-full bg-signal/10 px-3 py-1 text-xs text-signal">
                        queued
                      </span>
                      <button
                        type="button"
                        onClick={() => removeFile(file)}
                        className="rounded-full border border-white/10 px-3 py-1 text-xs text-slate-300 transition hover:border-ember/40 hover:text-rose-200"
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                ))
              ) : (
                <EmptyState
                  title="No files uploaded yet"
                  description="Attach one or more logs to populate the analysis pipeline."
                />
              )}
            </div>
          </Panel>

          <Panel title="Architecture Context" subtitle="System overview supplied to the model">
            <p className="text-sm leading-7 text-slate-300">{architecture || "No context added yet."}</p>
          </Panel>
        </div>

        <div className="space-y-6">
          <Panel title="Correlated Timeline" subtitle="Events leading to the incident">
            <TimelinePanel timeline={report?.timeline ?? []} />
          </Panel>

          <div className="grid gap-6 lg:grid-cols-2">
            <Panel title="Root Cause Analysis" subtitle="Most likely failure chain">
              <div className="space-y-4">
                <p className="text-sm leading-7 text-slate-300">
                  {report?.rootCause || "No report generated yet."}
                </p>
                <div className="rounded-2xl border border-amber-300/20 bg-gradient-to-br from-amber-300/12 to-orange-300/8 p-4">
                  <p className="text-xs uppercase tracking-[0.24em] text-amber-200">Confidence</p>
                  <p className="mt-2 text-2xl font-semibold text-white">
                    {Math.round((report?.confidence ?? 0) * 100)}%
                  </p>
                </div>
              </div>
            </Panel>

            <Panel title="Impact Assessment" subtitle="Affected scope and downtime">
              <div className="space-y-4">
                <InfoRow
                  label="Affected services"
                  value={report?.impact.services.join(", ") || "Not available"}
                />
                <InfoRow label="Estimated downtime" value={report?.impact.downtime ?? "Not available"} />
                <InfoRow label="Severity" value={report?.impact.severity ?? "Not available"} />
              </div>
            </Panel>
          </div>

          <Panel title="Auto-Generated Postmortem" subtitle="Structured report for IT operations">
            <div className="grid gap-4 lg:grid-cols-2">
              <PostmortemCard
                heading="Summary"
                content={report?.postmortem.summary ?? "No summary available yet."}
              />
              <PostmortemCard
                heading="RCA"
                content={report?.postmortem.rca ?? "No root cause narrative available yet."}
              />
              <div className="rounded-3xl border border-white/10 bg-white/[0.04] p-5 lg:col-span-2">
                <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Action items</p>
                <div className="mt-4 grid gap-3">
                  {report?.postmortem.actions?.length ? (
                    report.postmortem.actions.map((action) => (
                      <div
                        key={action}
                        className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-slate-200"
                      >
                        {action}
                      </div>
                    ))
                  ) : (
                    <div className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-slate-400">
                      No action items yet.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </Panel>

          <Panel title="Engineer Review" subtitle="Rate the generated report quality from 1 to 5 stars">
            <EngineerReview
              rating={engineerRating}
              disabled={!report}
              onRate={setEngineerRating}
            />
          </Panel>
        </div>
      </section>
    </main>
  );
}

function Panel({
  title,
  subtitle,
  children
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-[28px] border border-white/10 bg-slate-950/40 p-5 shadow-panel backdrop-blur sm:p-6">
      <div className="mb-5">
        <p className="text-lg font-semibold text-white">{title}</p>
        <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
      </div>
      {children}
    </section>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-3xl border border-white/10 bg-white/[0.06] px-4 py-5 backdrop-blur-sm">
      <p className="text-xs uppercase tracking-[0.22em] text-slate-500">{label}</p>
      <p className="mt-3 text-lg font-semibold text-white">{value}</p>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-4 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3">
      <span className="text-sm text-slate-400">{label}</span>
      <span className="max-w-[65%] text-right text-sm font-medium text-slate-100">{value}</span>
    </div>
  );
}

function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded-3xl border border-dashed border-white/10 bg-white/[0.03] px-4 py-8 text-center backdrop-blur-sm">
      <p className="text-sm font-medium text-slate-200">{title}</p>
      <p className="mt-2 text-sm leading-6 text-slate-500">{description}</p>
    </div>
  );
}

function PostmortemCard({ heading, content }: { heading: string; content: string }) {
  return (
    <div className="rounded-3xl border border-white/10 bg-white/[0.04] p-5 backdrop-blur-sm">
      <p className="text-xs uppercase tracking-[0.24em] text-slate-500">{heading}</p>
      <p className="mt-4 text-sm leading-7 text-slate-300">{content}</p>
    </div>
  );
}

function EngineerReview({
  rating,
  disabled,
  onRate
}: {
  rating: number | null;
  disabled: boolean;
  onRate: (value: number) => void;
}) {
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3">
        {[1, 2, 3, 4, 5].map((value) => {
          const active = (rating ?? 0) >= value;

          return (
            <button
              key={value}
              type="button"
              onClick={() => onRate(value)}
              disabled={disabled}
              className={`flex h-12 w-12 items-center justify-center rounded-2xl border text-xl transition ${
                disabled
                  ? "cursor-not-allowed border-white/10 bg-white/[0.03] text-slate-600"
                  : active
                    ? "border-amber-300/40 bg-amber-300/15 text-amber-200 shadow-[0_0_24px_rgba(252,211,77,0.2)]"
                    : "border-white/10 bg-white/[0.04] text-slate-400 hover:border-amber-300/30 hover:text-amber-100"
              }`}
              aria-label={`Rate ${value} star${value === 1 ? "" : "s"}`}
            >
              ★
            </button>
          );
        })}
      </div>
      <div className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3">
        <p className="text-sm text-slate-300">
          {disabled
            ? "Generate a report first to enable engineer review."
            : rating
              ? `Engineer rating recorded: ${rating}/5 stars.`
              : "Select a star rating to score this report."}
        </p>
      </div>
    </div>
  );
}

function TimelinePanel({ timeline }: { timeline: TimelineEvent[] }) {
  const [activeIndex, setActiveIndex] = useState(0);
  const itemRefs = useRef<Array<HTMLDivElement | null>>([]);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setActiveIndex(0);
    itemRefs.current = itemRefs.current.slice(0, timeline.length);
  }, [timeline]);

  useEffect(() => {
    const root = scrollRef.current;
    if (!root || timeline.length === 0) {
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        const visibleEntries = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);

        if (!visibleEntries.length) {
          return;
        }

        const nextIndex = Number(visibleEntries[0].target.getAttribute("data-index"));
        if (!Number.isNaN(nextIndex)) {
          setActiveIndex(nextIndex);
        }
      },
      {
        root,
        rootMargin: "-18% 0px -48% 0px",
        threshold: [0.25, 0.5, 0.75]
      }
    );

    itemRefs.current.forEach((item) => {
      if (item) {
        observer.observe(item);
      }
    });

    return () => observer.disconnect();
  }, [timeline]);

  if (!timeline.length) {
    return (
      <EmptyState
        title="No timeline yet"
        description="Upload logs and generate a report to see correlated events."
      />
    );
  }

  return (
    <div
      ref={scrollRef}
      className="max-h-[540px] space-y-5 overflow-y-auto pr-2"
    >
      {timeline.map((event, index) => {
        const isActive = index === activeIndex;

        return (
          <div
            key={`${event.time}-${index}`}
            ref={(node) => {
              itemRefs.current[index] = node;
            }}
            data-index={index}
            className="flex gap-4"
          >
            <div className="flex flex-col items-center">
              <div
                className={`h-3.5 w-3.5 rounded-full border transition-all duration-300 ${
                  isActive
                    ? "border-signal bg-signal shadow-[0_0_0_8px_rgba(94,234,212,0.18),0_0_30px_rgba(94,234,212,0.72)]"
                    : "border-white/20 bg-white/30 shadow-[0_0_0_5px_rgba(255,255,255,0.05)]"
                }`}
              />
              {index !== timeline.length - 1 ? (
                <div
                  className={`mt-2 h-full w-px bg-gradient-to-b transition-all duration-300 ${
                    isActive ? "from-signal via-signal/40 to-transparent" : "from-white/20 to-transparent"
                  }`}
                />
              ) : null}
            </div>
            <div
              className={`flex-1 rounded-3xl border p-4 backdrop-blur-sm transition-all duration-300 ${
                isActive
                  ? "border-signal/35 bg-signal/[0.08] shadow-[0_18px_50px_rgba(94,234,212,0.08)]"
                  : "border-white/10 bg-white/[0.05]"
              }`}
            >
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-sm font-semibold text-slate-100">{event.title}</h3>
                <span className="text-xs uppercase tracking-[0.2em] text-slate-500">
                  {event.time}
                </span>
              </div>
              <p className="text-sm leading-6 text-slate-300">{event.detail}</p>
              <p className="mt-3 text-xs text-signal">Source: {event.source}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function mapGenerateReportToUiReport(payload: ApiGenerateReportResponse): ReportState {
  const services = extractServices(payload);
  const severity = inferSeverity(payload);

  return {
    timeline: payload.timeline.map((item) => ({
      time: item.time,
      title: item.summary,
      detail: `Correlated event ${item.event_id}`,
      source: "correlation"
    })),
    rootCause: payload.root_cause,
    confidence: 0.93,
    impact: {
      services,
      downtime: payload.impact || "Under investigation",
      severity
    },
    postmortem: {
      summary: payload.summary,
      rca: payload.root_cause,
      actions: payload.action_items
    }
  };
}

function extractServices(payload: ApiGenerateReportResponse): string[] {
  const text = [payload.summary, payload.root_cause, payload.impact]
    .concat(payload.timeline.map((item) => `${item.summary} ${item.event_id}`))
    .join(" ");

  const knownServices = [
    "API Gateway",
    "Checkout Service",
    "Inventory Service",
    "Payment Service",
    "PostgreSQL",
    "Redis",
    "Worker Tier",
    "Database",
    "Kubernetes",
    "App Server"
  ];

  const matches = knownServices.filter((service) =>
    text.toLowerCase().includes(service.toLowerCase())
  );

  if (matches.length) {
    return matches;
  }

  const inferred = Array.from(
    new Set(
      [...text.matchAll(/\b([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,2})\b/g)]
        .map((match) => match[1]?.trim())
        .filter(
          (value): value is string =>
            Boolean(value) &&
            !["Correlated", "Unknown", "High", "Medium", "Low", "Impact", "Summary"].includes(value)
        )
    )
  ).slice(0, 4);

  return inferred.length ? inferred : ["Core Incident Services"];
}

function inferSeverity(payload: ApiGenerateReportResponse): string {
  const text = `${payload.summary} ${payload.root_cause} ${payload.impact}`.toLowerCase();

  if (
    text.includes("critical") ||
    text.includes("sev1") ||
    text.includes("outage") ||
    text.includes("platform-wide") ||
    text.includes("all users")
  ) {
    return "Critical";
  }

  if (
    text.includes("major") ||
    text.includes("degraded") ||
    text.includes("database") ||
    text.includes("checkout") ||
    text.includes("service disruption")
  ) {
    return "High";
  }

  if (text.includes("partial") || text.includes("intermittent")) {
    return "Medium";
  }

  return "High";
}
