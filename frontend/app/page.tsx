"use client";

import { useMemo, useState } from "react";
import ResumeGenerate from "@/components/ResumeGenerate";
import ResultsPanel from "@/components/ResultsPanel";

export default function Home() {
  const apiKey = useMemo(() => process.env.NEXT_PUBLIC_API_KEY || "", []);
  const [profileName, setProfileName] = useState("my_profile");

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
          <p className="text-sm text-slate-600">Backend: {baseUrl}. Using pre-ingested profile.</p>
        </header>

        <div className="mb-6 rounded-2xl border border-blue-200 bg-blue-50 p-5 shadow-sm">
          <h2 className="text-lg font-semibold text-blue-900 mb-3">📋 Profile Selection</h2>
          <p className="text-sm text-blue-800 mb-3">
            Your resume was pre-ingested using the <code className="bg-blue-100 px-2 py-1 rounded">ingest_profile.ipynb</code> notebook.
            Select which profile to use below.
          </p>
          <div className="flex gap-3 items-center">
            <label className="text-sm font-medium text-blue-900">Profile Name:</label>
            <input
              type="text"
              value={profileName}
              onChange={(e) => setProfileName(e.target.value)}
              placeholder="e.g., my_profile"
              className="flex-1 rounded-lg border border-blue-300 px-3 py-2 text-sm outline-none focus:border-indigo-500 bg-white"
            />
            <span className="text-xs text-blue-700">Default: my_profile</span>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-1">
          <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-semibold">Resume Generation</h2>
            <ResumeGenerate
              apiKey={apiKey}
              baseUrl={baseUrl}
              profileName={profileName}
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
