import { Routes, Route, NavLink } from "react-router-dom";

import { CalendarWorkspacePage } from "./pages/CalendarWorkspacePage";
import { SearchWorkspacePage } from "./pages/SearchWorkspacePage";

export default function App() {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_#eff6ff,_#e2e8f0_45%,_#cbd5e1)] text-slate-900">
      <div className="mx-auto flex min-h-screen max-w-7xl flex-col gap-8 px-6 py-8">
        <header className="flex flex-wrap items-center justify-between gap-4 rounded-[28px] border border-white/70 bg-white/80 px-6 py-5 shadow-board backdrop-blur">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">LMS Next</p>
            <h1 className="text-3xl font-black tracking-tight text-slate-950">Enterprise Learning Frontend</h1>
            <p className="mt-2 max-w-2xl text-sm text-slate-600">
              React + TypeScript + Tailwind scaffold with FullCalendar, real-time messaging hooks, and a modern global
              search shell.
            </p>
          </div>
          <nav className="flex flex-wrap items-center gap-3">
            <NavLink
              to="/"
              className={({ isActive }) =>
                `rounded-full px-4 py-2 text-sm font-semibold transition ${
                  isActive ? "bg-slate-950 text-white" : "bg-white text-slate-700"
                }`
              }
            >
              Calendar
            </NavLink>
            <NavLink
              to="/search"
              className={({ isActive }) =>
                `rounded-full px-4 py-2 text-sm font-semibold transition ${
                  isActive ? "bg-slate-950 text-white" : "bg-white text-slate-700"
                }`
              }
            >
              Search
            </NavLink>
          </nav>
        </header>

        <Routes>
          <Route path="/" element={<CalendarWorkspacePage />} />
          <Route path="/search" element={<SearchWorkspacePage />} />
        </Routes>
      </div>
    </div>
  );
}
