const inputClass =
  "rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none";

export function MatchFilters({
  title,
  location,
  seniority,
}: {
  title?: string;
  location?: string;
  seniority?: string;
}) {
  const hasFilters = Boolean(title || location || seniority);

  return (
    <form className="flex flex-wrap items-end gap-3 rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex flex-col gap-1">
        <label htmlFor="title" className="text-xs font-medium text-slate-500">
          Job title
        </label>
        <input
          id="title"
          name="title"
          type="text"
          defaultValue={title}
          placeholder="e.g. Backend Engineer"
          className={inputClass}
        />
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="location" className="text-xs font-medium text-slate-500">
          Location
        </label>
        <input
          id="location"
          name="location"
          type="text"
          defaultValue={location}
          placeholder="e.g. Remote, Paris"
          className={inputClass}
        />
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="seniority" className="text-xs font-medium text-slate-500">
          Experience level
        </label>
        <select id="seniority" name="seniority" defaultValue={seniority ?? ""} className={inputClass}>
          <option value="">Any</option>
          <option value="junior">Junior</option>
          <option value="mid">Mid</option>
          <option value="senior">Senior</option>
          <option value="lead">Lead</option>
        </select>
      </div>

      <button
        type="submit"
        className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
      >
        Apply filters
      </button>

      {hasFilters && (
        <a href="/matches" className="text-sm font-medium text-slate-500 hover:text-slate-700">
          Clear
        </a>
      )}
    </form>
  );
}
