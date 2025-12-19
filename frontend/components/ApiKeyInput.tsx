"use client";

type Props = {
  apiKey: string;
  setApiKey: (val: string) => void;
};

export default function ApiKeyInput({ apiKey, setApiKey }: Props) {
  return (
    <div className="flex items-center gap-3">
      <label className="text-sm font-medium text-slate-700" htmlFor="apiKey">
        API Key
      </label>
      <input
        id="apiKey"
        type="password"
        className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-indigo-500"
        value={apiKey}
        onChange={(e) => setApiKey(e.target.value)}
        placeholder="Enter x-api-key"
      />
    </div>
  );
}
