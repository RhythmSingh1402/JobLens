import Link from "next/link";
import { MatchCard } from "@/components/MatchCard";
import { MatchFilters } from "@/components/MatchFilters";
import { fetchMatches } from "@/lib/api";

export default async function MatchesPage({
  searchParams,
}: {
  searchParams: { title?: string; location?: string; seniority?: string };
}) {
  const { title, location, seniority } = searchParams;
  const hasFilters = Boolean(title || location || seniority);

  let matches;
  try {
    matches = await fetchMatches({ title, location, seniority });
  } catch {
    return (
      <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
        Couldn&apos;t reach the API. Make sure the backend is running, then refresh this page.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-bold">Your matches</h1>

      <MatchFilters title={title} location={location} seniority={seniority} />

      {matches.length === 0 && !hasFilters && (
        <div className="flex flex-col items-start gap-3">
          <p className="text-slate-600">Upload a resume first and we&apos;ll rank jobs for you.</p>
          <Link
            href="/upload"
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
          >
            Upload resume
          </Link>
        </div>
      )}

      {matches.length === 0 && hasFilters && (
        <p className="text-slate-600">No jobs match these filters. Try broadening your search.</p>
      )}

      {matches.map((match) => (
        <MatchCard key={match.id} match={match} />
      ))}
    </div>
  );
}
