"use client";

import { FormEvent, useState } from "react";

type Props = {
  apiKey: string;
  baseUrl: string;
  onSuccess: (chunks: number, sections: string[], message: string) => void;
  onError: (msg: string) => void;
};

export default function ProfileIngest({ apiKey, baseUrl, onSuccess, onError }: Props) {
  const [latex, setLatex] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    onError("");
    setLoading(true);
    try {
      const resp = await fetch(`${baseUrl}/profile/ingest`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-api-key": apiKey,
        },
        body: JSON.stringify({ resume_latex: latex }),
      });
      if (!resp.ok) {
        if (resp.status === 401) throw new Error("Invalid or missing API key");
        if (resp.status === 429) throw new Error("Rate limit exceeded");
        const detail = await resp.json().catch(() => ({}));
        throw new Error(detail.detail || "Ingestion failed");
      }
      const data = await resp.json();
      onSuccess(data.chunks_created, data.sections, "Profile ingested");
    } catch (err) {
      onError(err instanceof Error ? err.message : "Unexpected error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="space-y-3" onSubmit={handleSubmit}>
      <textarea
        className="h-40 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-indigo-500"
        placeholder="Paste your LaTeX resume..."
        value={latex}
        onChange={(e) => setLatex(e.target.value)}
        required
      />
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
