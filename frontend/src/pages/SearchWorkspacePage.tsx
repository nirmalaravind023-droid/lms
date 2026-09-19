import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { fetchGlobalSearch } from "@/lib/api";

export function SearchWorkspacePage() {
  const [query, setQuery] = useState("calendar");
  const enabled = query.trim().length >= 2;

  const searchQuery = useQuery({
    queryKey: ["global-search", query],
    queryFn: () => fetchGlobalSearch(query),
    enabled,
  });

  const grouped = useMemo(() => {
    const rows = searchQuery.data?.results ?? [];
    return rows.reduce<Record<string, typeof rows>>((acc, item) => {
      acc[item.category] = acc[item.category] ?? [];
      acc[item.category].push(item);
      return acc;
    }, {});
  }, [searchQuery.data]);

  return (
    <section className="grid gap-6">
      <div className="rounded-[28px] border border-white/70 bg-white/85 p-6 shadow-board backdrop-blur">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">Elasticsearch Ready</p>
        <h2 className="mt-3 text-3xl font-black tracking-tight text-slate-950">Global Search Workspace</h2>
        <p className="mt-3 max-w-3xl text-sm text-slate-600">
          This page is designed for the future Elasticsearch-backed search. Today it can already point at the Django
          fallback API, and later the NestJS search service can replace the same contract.
        </p>

        <div className="mt-6 rounded-[22px] border border-slate-200 bg-slate-950/95 p-4 text-white">
          <label className="mb-2 block text-sm font-semibold text-slate-300" htmlFor="search-query">
            Search Query
          </label>
          <input
            id="search-query"
            className="w-full rounded-2xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm outline-none ring-0"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search courses, users, messages, quizzes"
          />
          <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-400">
            <span className="rounded-full bg-slate-800 px-3 py-1">API contract stable</span>
            <span className="rounded-full bg-slate-800 px-3 py-1">NestJS compatible</span>
            <span className="rounded-full bg-slate-800 px-3 py-1">Elasticsearch source aware</span>
          </div>
        </div>
      </div>

      <div className="grid gap-4">
        {!enabled ? <p className="text-sm text-slate-500">Type at least 2 letters to search.</p> : null}
        {searchQuery.isLoading ? <p className="text-sm text-slate-500">Searching...</p> : null}
        {searchQuery.error ? <p className="text-sm text-rose-600">Search request failed.</p> : null}

        {Object.entries(grouped).map(([category, items]) => (
          <article key={category} className="rounded-[24px] border border-white/70 bg-white/85 p-5 shadow-board backdrop-blur">
            <div className="mb-4 flex items-center justify-between gap-3">
              <h3 className="text-lg font-bold text-slate-950">{category}</h3>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
                {items.length} result{items.length === 1 ? "" : "s"}
              </span>
            </div>
            <div className="grid gap-3">
              {items.map((item) => (
                <a
                  key={`${item.category}-${item.url}-${item.title}`}
                  href={item.url}
                  className="rounded-2xl border border-slate-200 px-4 py-3 transition hover:border-slate-300 hover:bg-slate-50"
                >
                  <div className="text-sm font-semibold text-slate-900">{item.title}</div>
                  <div className="mt-1 text-sm text-slate-500">{item.subtitle}</div>
                  {item.meta ? <div className="mt-2 text-xs uppercase tracking-[0.2em] text-slate-400">{item.meta}</div> : null}
                </a>
              ))}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
