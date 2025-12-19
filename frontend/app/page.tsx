"use client";

import { useMemo, useState } from "react";
import ProfileIngest from "@/components/ProfileIngest";
import ResumeGenerate from "@/components/ResumeGenerate";
import ResultsPanel from "@/components/ResultsPanel";

export default function Home() {
  const apiKey = useMemo(() => process.env.NEXT_PUBLIC_API_KEY || "", []);
  const [ingestStatus, setIngestStatus] = useState<string | null>(null);
  const [ingestSections, setIngestSections] = useState<string[]>([]);
  const [ingestChunks, setIngestChunks] = useState<number | null>(null);

  const [jdText, setJdText] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [jobCompany, setJobCompany] = useState("");
  const [jobLocation, setJobLocation] = useState("");

  const [genResult, setGenResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const baseUrl = useMemo(() => process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000", []);

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <header className="mb-8 flex flex-col gap-2">
          <p className="text-sm font-semibold text-indigo-600">RAG ATS Resume Builder</p>
          <h1 className="text-3xl font-bold">Generate an ATS-optimized, one-page resume</h1>
          <p className="text-sm text-slate-600">Backend: {baseUrl}. Using API key from environment.</p>
        </header>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-semibold">Profile Ingest (LaTeX Resume)</h2>
            <ProfileIngest
              apiKey={apiKey}
              baseUrl={baseUrl}
              onSuccess={(chunks, sections, message) => {
                setIngestChunks(chunks);
                setIngestSections(sections);
                setIngestStatus(message);
              }}
              onError={(msg) => {
                setError(msg);
              }}
            />
            {ingestStatus && (
              <div className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
                {ingestStatus} — sections: {ingestSections.join(", ")}; chunks: {ingestChunks}
              </div>
            )}
          </section>

          <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-semibold">Resume Generation</h2>
            <ResumeGenerate
              apiKey={apiKey}
              baseUrl={baseUrl}
              jdText={jdText}
              setJdText={setJdText}
              jobTitle={jobTitle}
              setJobTitle={setJobTitle}
              jobCompany={jobCompany}
              setJobCompany={setJobCompany}
              jobLocation={jobLocation}
              setJobLocation={setJobLocation}
              onSuccess={(res) => {
                setGenResult(res);
                setError(null);
              }}
              onError={(msg) => setError(msg)}
            />
          </section>
        </div>

        {error && (
          <div className="mt-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <ResultsPanel result={genResult} />
        </section>
      </div>
    </main>
  );
}
