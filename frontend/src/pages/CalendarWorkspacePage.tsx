import FullCalendar from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";
import interactionPlugin from "@fullcalendar/interaction";

const demoEvents = [
  { title: "Leadership Onboarding", date: "2026-04-08" },
  { title: "Quarterly Compliance Quiz", date: "2026-04-11" },
  { title: "Public Holiday Overlay", date: "2026-04-14" },
];

export function CalendarWorkspacePage() {
  return (
    <section className="grid gap-6">
      <div className="rounded-[28px] border border-white/70 bg-slate-950 px-6 py-6 text-white shadow-board">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-sky-200">FullCalendar Module</p>
        <h2 className="mt-3 text-3xl font-black tracking-tight">Calendar Workspace</h2>
        <p className="mt-3 max-w-3xl text-sm text-slate-300">
          This is the migration target for the current Django calendar. It is ready for month, week, day, holiday
          overlays, task drag-drop, and live refresh through Socket.io.
        </p>
      </div>

      <div className="rounded-[28px] border border-white/70 bg-white/85 p-5 shadow-board backdrop-blur">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm font-semibold text-slate-900">Modern Scheduling Board</p>
            <p className="text-sm text-slate-500">FullCalendar replaces the current heavy custom bundle here.</p>
          </div>
          <div className="flex gap-2">
            <span className="rounded-full bg-orange-100 px-3 py-1 text-xs font-semibold text-orange-700">Holidays</span>
            <span className="rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-700">Tasks</span>
            <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700">Learner View</span>
          </div>
        </div>

        <FullCalendar
          plugins={[dayGridPlugin, interactionPlugin]}
          initialView="dayGridMonth"
          headerToolbar={{
            left: "today prev,next",
            center: "title",
            right: "dayGridMonth",
          }}
          height="auto"
          events={demoEvents}
          editable={false}
          selectable
        />
      </div>
    </section>
  );
}
