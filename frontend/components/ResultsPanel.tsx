"use client";

"use client";

type MappingEntry = { keyword: string };
type Iteration = { iteration: number; score_before: number; score_after: number; changes: string[] };

type ResultShape = {
  ats_score?: number;
  render_attempts?: number | null;
  mapping?: {
    matched?: MappingEntry[];
    missing?: MappingEntry[];
  };
  optimizer?: { iterations?: Iteration[] };
  pdf_url?: string;
  audit_url?: string;
  run_id?: string;
};

type Props = {
  result: ResultShape | null;
};

export default function ResultsPanel({ result }: Props) {
  if (!result) {
    return <p className="text-sm text-slate-500">No results yet. Generate a resume to see details.</p>;
  }

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <p className="text-xs uppercase tracking-wide text-slate-500">ATS Score</p>
        <p className="mt-2 text-3xl font-bold text-emerald-600">{result.ats_score}</p>
        <p className="text-xs text-slate-500">Render attempts: {result.render_attempts ?? "n/a"}</p>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <p className="text-xs uppercase tracking-wide text-slate-500">Matched Keywords</p>
        <p className="mt-1 text-sm text-slate-900">
          {result.mapping?.matched?.map((m) => m.keyword).join(", ") || "—"}
        </p>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <p className="text-xs uppercase tracking-wide text-slate-500">Missing Keywords</p>
        <p className="mt-1 text-sm text-slate-900">
          {result.mapping?.missing?.map((m) => m.keyword).join(", ") || "—"}
        </p>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm md:col-span-3">
        <p className="text-xs uppercase tracking-wide text-slate-500">Optimizer Iterations</p>
        {result.optimizer?.iterations?.length ? (
          <ul className="mt-2 space-y-1 text-sm text-slate-800">
            {result.optimizer.iterations.map((it) => (
              <li key={it.iteration} className="rounded bg-slate-50 px-2 py-1">
                Iter {it.iteration}: {it.score_before} → {it.score_after} | {it.changes.join("; ")}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-1 text-sm text-slate-700">No iterations logged.</p>
        )}
      </div>

      <div className="flex gap-3 md:col-span-3">
        <a
          href={result.pdf_url}
          target="_blank"
          rel="noreferrer"
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700"
        >
          Download PDF
        </a>
        {result.run_id && (
          <>
            <a
          href={`${result.pdf_url?.startsWith("http") ? result.pdf_url : `/runs/${result.run_id}/pdf`}`}
              target="_blank"
              rel="noreferrer"
              className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-slate-300"
            >
              View PDF
            </a>
            <a
          href={`${result.audit_url || `/runs/${result.run_id}/audit`}`}
              target="_blank"
              rel="noreferrer"
              className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-slate-300"
            >
              View Audit JSON
            </a>
          </>
        )}
      </div>
    </div>
  );
}
