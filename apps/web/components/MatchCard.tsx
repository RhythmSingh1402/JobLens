"use client";

import { useState } from "react";
import { generateCoverLetter, type Match } from "@/lib/api";

function scoreColor(score: number) {
  if (score >= 75) return "bg-green-100 text-green-800";
  if (score >= 50) return "bg-amber-100 text-amber-800";
  return "bg-slate-100 text-slate-600";
}

export function MatchCard({ match: initialMatch }: { match: Match }) {
  const [match, setMatch] = useState(initialMatch);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const hasLetter = Boolean(match.cover_letter_body);

  async function handleGenerate() {
    setLoading(true);
    setError(null);
    try {
      const updated = await generateCoverLetter(match.id);
      setMatch(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't generate a cover letter. Try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <article className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold">{match.job.title}</h2>
            {match.job.source !== "seed" && (
              <span className="rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-blue-700">
                via {match.job.source}
              </span>
            )}
          </div>
          <p className="text-sm text-slate-600">
            {match.job.company} · {match.job.location}
            {match.job.seniority && ` · ${match.job.seniority}`}
          </p>
        </div>
        <span
          className={`shrink-0 rounded-full px-3 py-1 text-sm font-semibold ${scoreColor(match.score)}`}
        >
          {Math.round(match.score)}%
        </span>
      </div>

      <p className="mt-3 text-sm text-slate-700">{match.rationale}</p>

      <div className="mt-3 flex flex-wrap gap-2">
        {match.job.requirements.map((req) => (
          <span
            key={req}
            className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600"
          >
            {req}
          </span>
        ))}
      </div>

      <div className="mt-3 flex items-center justify-between">
        {match.job.salary_range && (
          <p className="text-xs text-slate-500">{match.job.salary_range}</p>
        )}
        {match.job.url && (
          <a
            href={match.job.url}
            target="_blank"
            rel="noopener noreferrer"
            className="ml-auto rounded-md border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            View posting ↗
          </a>
        )}
      </div>

      <div className="mt-3 border-t border-slate-100 pt-3">
        {!hasLetter && (
          <button
            type="button"
            onClick={handleGenerate}
            disabled={loading}
            className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? "Drafting cover letter..." : "Generate cover letter"}
          </button>
        )}

        {hasLetter && (
          <div className="flex flex-col gap-2">
            <div className="rounded-md bg-slate-50 p-3">
              <p className="text-sm font-semibold text-slate-800">{match.cover_letter_subject}</p>
              <p className="mt-2 whitespace-pre-wrap text-sm text-slate-700">
                {match.cover_letter_body}
              </p>
            </div>
            <p className="text-xs text-slate-400">
              Draft only — nothing is sent automatically. Review and copy it yourself.
            </p>
            <button
              type="button"
              onClick={handleGenerate}
              disabled={loading}
              className="self-start rounded-md border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? "Regenerating..." : "Regenerate"}
            </button>
          </div>
        )}

        {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
      </div>
    </article>
  );
}
