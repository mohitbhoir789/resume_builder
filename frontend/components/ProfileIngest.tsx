"use client";

import { FormEvent, useState } from "react";

type Props = {
  apiKey: string;
  baseUrl: string;
  onSuccess: (chunks: number, sections: string[], message: string, profile: Record<string, unknown>) => void;
  onError: (msg: string) => void;
};

export default function ProfileIngest({ apiKey, baseUrl, onSuccess, onError }: Props) {
  const [mode, setMode] = useState<"pdf" | "text">("pdf");
  const [latexOrText, setLatexOrText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    onError(null);
    setLoading(true);
    try {
      let resp: Response;
      if (mode === "pdf") {
        if (!file) throw new Error("Please select a PDF file");
        const form = new FormData();
        form.append("resume_file", file);
        resp = await fetch(`${baseUrl}/profile/ingest`, {
          method: "POST",
          headers: apiKey ? { "x-api-key": apiKey } : undefined,
          body: form,
        });
      } else {
        if (!latexOrText.trim()) throw new Error("Please enter resume text");
        resp = await fetch(`${baseUrl}/profile/ingest-text`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(apiKey ? { "x-api-key": apiKey } : {}),
          },
          body: JSON.stringify({ resume_text: latexOrText }),
        });
      }
      if (!resp.ok) {
        const detail = await resp.json().catch(() => ({}));
        if (resp.status === 400) throw new Error(detail.detail || "Invalid input");
        if (resp.status === 500) throw new Error(detail.detail || "Ingestion failed");
        throw new Error("Ingestion failed");
      }
      const data = await resp.json();
      onSuccess(data.chunks_created, data.sections, `Profile ingested (${data.ingest_type})`, data.profile);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Unexpected error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="space-y-3" onSubmit={handleSubmit}>
      <div className="flex items-center gap-3 text-sm">
        <label className="flex items-center gap-1">
          <input type="radio" checked={mode === "pdf"} onChange={() => setMode("pdf")} /> PDF upload
        </label>
        <label className="flex items-center gap-1">
          <input type="radio" checked={mode === "text"} onChange={() => setMode("text")} /> Plain text
        </label>
      </div>

      {mode === "pdf" ? (
        <input
          type="file"
          accept="application/pdf"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          className="w-full text-sm"
        />
      ) : (
        <textarea
          className="h-40 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-indigo-500"
          placeholder="Paste your resume text..."
          value={latexOrText}
          onChange={(e) => setLatexOrText(e.target.value)}
          required
        />
      )}

      <button
        type="submit"
        disabled={loading}
        className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-slate-300"
      >
        {loading ? "Ingesting..." : "Ingest Profile"}
      </button>
    </form>
  );
}
