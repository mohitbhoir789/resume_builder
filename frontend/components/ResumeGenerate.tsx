"use client";

import { FormEvent, useState } from "react";

type Props = {
  apiKey: string;
  baseUrl: string;
  profileName: string;
  jdText: string;
  setJdText: (val: string) => void;
  jobTitle: string;
  setJobTitle: (val: string) => void;
  jobCompany: string;
  setJobCompany: (val: string) => void;
  jobLocation: string;
  setJobLocation: (val: string) => void;
  onSuccess: (res: Record<string, unknown>) => void;
  onError: (msg: string) => void;
};

export default function ResumeGenerate({
  apiKey,
  baseUrl,
  profileName,
  jdText,
  setJdText,
  jobTitle,
  setJobTitle,
  jobCompany,
  setJobCompany,
  jobLocation,
  setJobLocation,
  onSuccess,
  onError,
}: Props) {
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    onError(null);
    setLoading(true);
    try {
      if (!profileName.trim()) {
        throw new Error("Please enter a profile name");
      }
      const payload = {
        job: { title: jobTitle, company: jobCompany, location: jobLocation, description: jdText },
        profile_name: profileName,
      };
      const resp = await fetch(`${baseUrl}/resume/generate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-api-key": apiKey,
        },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) {
        if (resp.status === 401) throw new Error("Invalid or missing API key");
        if (resp.status === 429) throw new Error("Rate limit exceeded");
        const detail = await resp.json().catch(() => ({}));
        throw new Error(detail.detail || "Resume generation failed");
      }
      const data = await resp.json();
      onSuccess(data);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Unexpected error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="space-y-3" onSubmit={handleSubmit}>
      <div className="grid gap-2 md:grid-cols-2">
        <input
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-indigo-500"
          placeholder="Job title"
          value={jobTitle}
          onChange={(e) => setJobTitle(e.target.value)}
          required
        />
        <input
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-indigo-500"
          placeholder="Company"
          value={jobCompany}
          onChange={(e) => setJobCompany(e.target.value)}
        />
        <input
          className="md:col-span-2 rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-indigo-500"
          placeholder="Location"
          value={jobLocation}
          onChange={(e) => setJobLocation(e.target.value)}
        />
      </div>
      <textarea
        className="h-40 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-indigo-500"
        placeholder="Paste job description..."
        value={jdText}
        onChange={(e) => setJdText(e.target.value)}
        required
      />
      <button
        type="submit"
        disabled={loading || !profileName.trim()}
        className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-slate-300"
      >
        {loading ? "Generating..." : "Generate Resume"}
      </button>
      {!profileName.trim() && (
        <p className="text-xs text-slate-500">Enter a profile name to generate a resume.</p>
      )}
    </form>
  );
}
