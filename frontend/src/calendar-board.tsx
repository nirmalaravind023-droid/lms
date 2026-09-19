import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";

type DepartmentOption = {
  id: string;
  name: string;
  color: string;
};

type HolidayFilter = {
  key: string;
  label: string;
  color: string;
  count?: number;
};

type CalendarSummary = {
  total_items: number;
  quiz_items: number;
  assignment_items: number;
  task_items: number;
  holiday_items: number;
};

type CalendarDetailRow = {
  label: string;
  value: string | number;
  hint: string;
};

type CalendarEventItem = {
  kind: "task" | "holiday" | string;
  id: string;
  title: string;
  type_label: string;
  subtitle: string;
  color: string;
  url?: string;
  open_url?: string;
  edit_url?: string;
  department?: string;
  department_color?: string;
  section_title?: string;
  overview_lines?: string[];
  start_label?: string;
  start_time_label?: string;
  end_time_label?: string;
  meeting_type_label?: string;
  holiday_calendar_key?: string;
  holiday_calendar_label?: string;
};

type CalendarCell = {
  iso_date: string;
  day: number;
  in_month: boolean;
  is_today: boolean;
  create_url: string;
  events: CalendarEventItem[];
};

type CalendarResponse = {
  current_month: number;
  month?: number;
  year?: number;
  display_month: string;
  display_year: number;
  selected_department: string;
  departments: DepartmentOption[];
  holiday_filters: HolidayFilter[];
  is_learner: boolean;
  can_manage: boolean;
  create_task_url: string;
  previous_month: number;
  previous_year: number;
  next_month: number;
  next_year: number;
  calendar_summary: CalendarSummary;
  calendar_detail_rows: CalendarDetailRow[];
  weeks: CalendarCell[][];
};

type CalendarUiState = {
  month: number;
  year: number;
  department: string;
  holidayKeys: string[];
  showTasks: boolean;
};

type CalendarAppState = {
  loading: boolean;
  error: string;
  data: CalendarResponse | null;
  month: number;
  year: number;
  department: string;
};

type TaskColorStyle = React.CSSProperties & {
  "--task-color": string;
};

function buildQuery({ month, year, department }: { month: number; year: number; department: string }) {
  const params = new URLSearchParams();
  params.set("month", String(month));
  params.set("year", String(year));
  if (department) {
    params.set("department", department);
  }
  return params.toString();
}

function readCalendarUiState({
  initialMonth,
  initialYear,
  initialDepartment,
}: {
  initialMonth: string;
  initialYear: string;
  initialDepartment: string;
}): CalendarUiState {
  if (typeof window === "undefined") {
    return {
      month: Number(initialMonth),
      year: Number(initialYear),
      department: initialDepartment || "",
      holidayKeys: [],
      showTasks: true,
    };
  }

  const params = new URLSearchParams(window.location.search);
  const month = Number(params.get("month") || initialMonth);
  const year = Number(params.get("year") || initialYear);
  const department = params.get("department") || initialDepartment || "";
  const holidayKeys = (params.get("holidays") || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  const showTasks = params.get("show_tasks") !== "0";

  return {
    month,
    year,
    department,
    holidayKeys,
    showTasks,
  };
}

function CalendarFilterBar({
  data,
  toolbarTitle,
  selectedDepartmentLabel,
  onSelectDepartment,
  onNavigate,
}: {
  data: CalendarResponse | null;
  toolbarTitle: string;
  selectedDepartmentLabel: string;
  onSelectDepartment: (department: string) => void;
  onNavigate: (month: number, year: number) => void;
}) {
  if (!data) {
    return null;
  }

  return (
    <div className="react-calendar-controls-stack">
      {data.departments?.length ? (
        <div className="calendar-filter-rail calendar-filter-rail-modern react-calendar-filter-rail">
          {!data.is_learner ? (
            <button
              type="button"
              className={`button button-secondary ${!data.selected_department ? "calendar-filter-active" : ""}`}
              onClick={() => onSelectDepartment("")}
            >
              All Teams
            </button>
          ) : null}
          {data.departments.map((department) => (
            <button
              type="button"
              key={department.id}
              className={`button button-secondary ${data.selected_department === department.id ? "calendar-filter-active" : ""}`}
              style={{ borderColor: department.color }}
              onClick={() => onSelectDepartment(department.id)}
            >
              {department.name}
            </button>
          ))}
        </div>
      ) : null}

      <div className="react-calendar-period-nav card compact-card">
        <div className="react-calendar-period-nav-copy">
          <span className="badge">Month Control</span>
          <strong>{toolbarTitle}</strong>
          <p className="muted">Department: {selectedDepartmentLabel}</p>
        </div>
        <div className="react-calendar-period-nav-actions">
          <button
            className="button button-secondary react-calendar-arrow"
            type="button"
            aria-label="Previous month"
            onClick={() => onNavigate(data.previous_month, data.previous_year)}
          >
            {"<"}
          </button>
          <button
            className="button button-secondary react-calendar-arrow"
            type="button"
            aria-label="Next month"
            onClick={() => onNavigate(data.next_month, data.next_year)}
          >
            {">"}
          </button>
        </div>
      </div>
    </div>
  );
}

function HolidayFilterPanel({
  holidayFilters,
  selectedHolidayKeys,
  onToggleHoliday,
  onSelectAllHolidays,
  showTasks,
  onToggleTasks,
}: {
  holidayFilters: HolidayFilter[];
  selectedHolidayKeys: string[];
  onToggleHoliday: (holidayKey: string) => void;
  onSelectAllHolidays: () => void;
  showTasks: boolean;
  onToggleTasks: () => void;
}) {
  if (!holidayFilters.length) {
    return null;
  }

  return (
    <section className="card compact-card calendar-holiday-panel">
      <div className="calendar-holiday-panel-header">
        <div>
          <span className="badge">Holiday Filters</span>
          <strong>Choose which religious or public calendars to show</strong>
        </div>
        <div className="calendar-holiday-actions">
          <button className="button button-secondary" type="button" onClick={onSelectAllHolidays}>
            Show All
          </button>
        </div>
      </div>

      <label className="calendar-holiday-toggle">
        <input type="checkbox" checked={showTasks} onChange={onToggleTasks} />
        <span>Show LMS Tasks</span>
      </label>

      <div className="calendar-holiday-rail">
        {holidayFilters.map((filter) => {
          const active = selectedHolidayKeys.includes(filter.key);
          return (
            <button
              key={filter.key}
              type="button"
              className={`calendar-holiday-chip ${active ? "calendar-holiday-chip-active" : ""}`}
              onClick={() => onToggleHoliday(filter.key)}
              aria-pressed={active}
            >
              <span className="calendar-holiday-chip-check">{active ? "✓" : ""}</span>
              <span className="calendar-holiday-chip-dot" style={{ background: filter.color }} />
              <span>{filter.label}</span>
            </button>
          );
        })}
      </div>
      <p className="muted">
        Turn on only the calendars you want to see. For example, keep just Hindu holidays visible while hiding the others.
      </p>
    </section>
  );
}

function TaskOverviewModal({
  task,
  canManage,
  onClose,
}: {
  task: CalendarEventItem | null;
  canManage: boolean;
  onClose: () => void;
}) {
  if (!task) {
    return null;
  }

  return (
    <div className="calendar-task-modal-backdrop" role="presentation" onClick={onClose}>
      <section
        className="calendar-task-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="calendar-task-modal-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="calendar-task-modal-topbar">
          <div className="calendar-task-modal-actions">
            {canManage && task.edit_url ? (
              <a
                className="calendar-task-icon-button"
                href={task.edit_url}
                aria-label="Edit task"
                title="Edit task"
              >
                ✎
              </a>
            ) : null}
            <button
              className="calendar-task-icon-button"
              type="button"
              onClick={onClose}
              aria-label="Close task overview"
              title="Close"
            >
              ×
            </button>
          </div>
        </div>

        <div className="calendar-task-modal-body">
          <div className="calendar-task-modal-title-row">
            <span
              className="calendar-task-modal-dot"
              style={{ background: task.department_color || task.color }}
              aria-hidden="true"
            />
            <div>
              <h2 id="calendar-task-modal-title">{task.title}</h2>
              <p className="calendar-task-modal-date">{task.start_label}</p>
            </div>
          </div>

          <div className="calendar-task-modal-meta">
            <div className="calendar-task-modal-meta-row">
              <span className="calendar-task-modal-meta-icon">◴</span>
              <div>
                <strong>{task.type_label}</strong>
                <span>{task.start_time_label}{task.end_time_label ? ` to ${task.end_time_label}` : ""}</span>
              </div>
            </div>

            {task.section_title ? (
              <div className="calendar-task-modal-meta-row">
                <span className="calendar-task-modal-meta-icon">▤</span>
                <div>
                  <strong>Section</strong>
                  <span>{task.section_title}</span>
                </div>
              </div>
            ) : null}

            {task.department ? (
              <div className="calendar-task-modal-meta-row">
                <span className="calendar-task-modal-meta-icon">■</span>
                <div>
                  <strong>Department</strong>
                  <span>{task.department}</span>
                </div>
              </div>
            ) : null}

            {task.overview_lines?.length ? (
              <div className="calendar-task-modal-meta-row">
                <span className="calendar-task-modal-meta-icon">≡</span>
                <div>
                  <strong>Overview</strong>
                  <span>{task.overview_lines.join(" · ")}</span>
                </div>
              </div>
            ) : null}

            {task.meeting_type_label ? (
              <div className="calendar-task-modal-meta-row">
                <span className="calendar-task-modal-meta-icon">⌕</span>
                <div>
                  <strong>Meeting Type</strong>
                  <span>{task.meeting_type_label}</span>
                </div>
              </div>
            ) : null}
          </div>

          <div className="calendar-task-modal-footer">
            {task.open_url ? (
              <a className="button" href={task.open_url}>
                Open
              </a>
            ) : null}
            <button className="button button-secondary" type="button" onClick={onClose}>
              Close
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}

function CalendarApp({
  endpoint,
  initialMonth,
  initialYear,
  initialDepartment,
}: {
  endpoint: string;
  initialMonth: string;
  initialYear: string;
  initialDepartment: string;
}) {
  const initialUiState = useMemo(
    () => readCalendarUiState({ initialMonth, initialYear, initialDepartment }),
    [initialMonth, initialYear, initialDepartment]
  );
  const [state, setState] = useState<CalendarAppState>({
    loading: true,
    error: "",
    data: null,
    month: initialUiState.month,
    year: initialUiState.year,
    department: initialUiState.department,
  });
  const [selectedHolidayKeys, setSelectedHolidayKeys] = useState(initialUiState.holidayKeys);
  const [showTasks, setShowTasks] = useState(initialUiState.showTasks);
  const [activeTask, setActiveTask] = useState<CalendarEventItem | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const query = buildQuery({
      month: state.month,
      year: state.year,
      department: state.department,
    });

    setState((current) => ({ ...current, loading: true, error: "" }));

    fetch(`${endpoint}?${query}`, {
      credentials: "same-origin",
      signal: controller.signal,
      headers: {
        "X-Requested-With": "XMLHttpRequest",
      },
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Calendar request failed with ${response.status}`);
        }
        return response.json();
      })
      .then((data: CalendarResponse) => {
        setState((current) => ({
          ...current,
          loading: false,
          data,
          error: "",
          month: data.current_month,
          year: Number(data.display_year),
          department: data.selected_department || "",
        }));
      })
      .catch((error: Error) => {
        if (error.name === "AbortError") {
          return;
        }
        setState((current) => ({
          ...current,
          loading: false,
          error: error.message || "Unable to load the calendar.",
        }));
      });

    return () => controller.abort();
  }, [endpoint, state.month, state.year, state.department]);

  const data = state.data;
  const safeData = useMemo(() => {
    if (!data) {
      return null;
    }
    return {
      ...data,
      departments: data.departments || [],
      holiday_filters: data.holiday_filters || [],
      weeks: data.weeks || [],
      calendar_summary: data.calendar_summary || {
        total_items: 0,
        quiz_items: 0,
        assignment_items: 0,
        task_items: 0,
        holiday_items: 0,
      },
      calendar_detail_rows: data.calendar_detail_rows || [],
      selected_department: data.selected_department || "",
      display_month: data.display_month || "",
      display_year: Number(data.display_year || data.year || new Date().getFullYear()),
    };
  }, [data]);

  const toolbar = useMemo(() => {
    if (!safeData) {
      return {
        title: "",
        subtitle: "",
      };
    }
    return {
      title: `${safeData.display_month} ${safeData.display_year}`.trim(),
      subtitle: safeData.is_learner
        ? "Your department quizzes, assignments, and LMS tasks in one modern board."
        : "Plan and track department tasks, quizzes, and assignment milestones in one place.",
    };
  }, [safeData]);

  const selectedDepartmentLabel = useMemo(() => {
    if (!safeData) {
      return "";
    }
    if (!safeData.selected_department) {
      return safeData.is_learner ? "My Team" : "All Teams";
    }
    const match = safeData.departments?.find((department) => department.id === safeData.selected_department);
    return match?.name || "Selected Department";
  }, [safeData]);

  const holidayFilters = useMemo(() => {
    if (!safeData) {
      return [];
    }
    if (safeData.holiday_filters?.length) {
      return [...safeData.holiday_filters].sort((a, b) => a.label.localeCompare(b.label));
    }
    const entries = new Map<string, HolidayFilter>();
    safeData.weeks.forEach((week) => {
      week.forEach((cell) => {
        cell.events.forEach((event) => {
          if (event.kind !== "holiday" || !event.holiday_calendar_key) {
            return;
          }
          if (!entries.has(event.holiday_calendar_key)) {
            entries.set(event.holiday_calendar_key, {
              key: event.holiday_calendar_key,
              label: event.holiday_calendar_label || event.type_label || event.holiday_calendar_key,
              color: event.color || "#dc2626",
              count: 0,
            });
          }
        });
      });
    });
    return Array.from(entries.values()).sort((a, b) => a.label.localeCompare(b.label));
  }, [safeData]);

  useEffect(() => {
    if (!holidayFilters.length) {
      setSelectedHolidayKeys([]);
      return;
    }
    setSelectedHolidayKeys((current) => {
      if (!current.length) {
        return holidayFilters.map((item) => item.key);
      }
      const available = new Set(holidayFilters.map((item) => item.key));
      const kept = current.filter((key) => available.has(key));
      return kept.length ? kept : holidayFilters.map((item) => item.key);
    });
  }, [holidayFilters]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const params = new URLSearchParams(window.location.search);
    params.set("month", String(state.month));
    params.set("year", String(state.year));
    if (state.department) {
      params.set("department", state.department);
    } else {
      params.delete("department");
    }
    if (selectedHolidayKeys.length && holidayFilters.length && selectedHolidayKeys.length !== holidayFilters.length) {
      params.set("holidays", selectedHolidayKeys.join(","));
    } else {
      params.delete("holidays");
    }
    if (!showTasks) {
      params.set("show_tasks", "0");
    } else {
      params.delete("show_tasks");
    }
    const nextSearch = params.toString();
    const nextUrl = `${window.location.pathname}${nextSearch ? `?${nextSearch}` : ""}`;
    window.history.replaceState({}, "", nextUrl);
  }, [state.month, state.year, state.department, selectedHolidayKeys, showTasks, holidayFilters]);

  const navigate = (month: number, year: number) => {
    setState((current) => ({
      ...current,
      month,
      year,
    }));
  };

  const selectDepartment = (department: string) => {
    setState((current) => ({
      ...current,
      department,
    }));
  };

  const toggleHoliday = (holidayKey: string) => {
    setSelectedHolidayKeys((current) => {
      if (current.includes(holidayKey)) {
        const next = current.filter((key) => key !== holidayKey);
        return next.length ? next : current;
      }
      return [...current, holidayKey];
    });
  };

  const selectAllHolidays = () => {
    setSelectedHolidayKeys(holidayFilters.map((item) => item.key));
  };

  const toggleTasks = () => {
    setShowTasks((current) => !current);
  };

  const openTaskOverview = (event: React.MouseEvent<HTMLButtonElement>, task: CalendarEventItem) => {
    event.preventDefault();
    setActiveTask(task);
  };

  const closeTaskOverview = () => {
    setActiveTask(null);
  };

  return (
    <section className="panel calendar-shell calendar-shell-modern">
      {state.loading && !safeData ? (
        <div className="react-calendar-loading">
          <div className="react-calendar-loader" aria-hidden="true">
            <span />
            <span />
            <span />
          </div>
          <span className="badge">Loading</span>
          <h1>Loading calendar...</h1>
          <p className="muted">Fetching calendar items, holidays, and task cards. This can take a moment on slower API responses.</p>
        </div>
      ) : null}

      {state.error && !safeData ? (
        <div className="react-calendar-error">
          <span className="badge">Calendar Error</span>
          <h1>Unable to load calendar</h1>
          <p className="muted">{state.error}</p>
        </div>
      ) : null}

      {safeData ? (
        <>
          {state.loading ? (
            <div className="react-calendar-loading-overlay" role="status" aria-live="polite">
              <div className="react-calendar-loading-overlay-card">
                <div className="react-calendar-loader react-calendar-loader-compact" aria-hidden="true">
                  <span />
                  <span />
                  <span />
                </div>
                <strong>Refreshing calendar...</strong>
                <p className="muted">Updating the board with the latest month, department, and task data.</p>
              </div>
            </div>
          ) : null}

          <div className="react-calendar-toolbar">
            <div className="react-calendar-toolbar-left">
              <span className="badge">React Calendar</span>
              <div className="calendar-title-block">
                <h1>{toolbar.title}</h1>
                <p className="muted">{toolbar.subtitle}</p>
              </div>
            </div>
            <div className="react-calendar-toolbar-actions">
              {safeData.can_manage && safeData.create_task_url ? (
                <a className="button" href={safeData.create_task_url}>
                  Add Task
                </a>
              ) : null}
            </div>
          </div>

          <div className="calendar-summary-strip calendar-summary-strip-modern react-calendar-summary">
            <article className="calendar-summary-card">
              <span className="badge">Total</span>
              <strong>{safeData.calendar_summary.total_items}</strong>
              <p className="muted">Department task items scheduled for this month.</p>
            </article>
            <article className="calendar-summary-card">
              <span className="badge">Quizzes</span>
              <strong>{safeData.calendar_summary.quiz_items}</strong>
              <p className="muted">Assessment deadlines in view.</p>
            </article>
            <article className="calendar-summary-card">
              <span className="badge">Assignments</span>
              <strong>{safeData.calendar_summary.assignment_items}</strong>
              <p className="muted">Course work due this month.</p>
            </article>
            <article className="calendar-summary-card">
              <span className="badge">Tasks</span>
              <strong>{safeData.calendar_summary.task_items}</strong>
              <p className="muted">Calendar tasks already scheduled.</p>
            </article>
            <article className="calendar-summary-card">
              <span className="badge">Holidays</span>
              <strong>{safeData.calendar_summary.holiday_items}</strong>
              <p className="muted">Religious and public holiday items visible in the board.</p>
            </article>
          </div>

          {!safeData.calendar_summary.total_items ? (
            <section className="card compact-card react-calendar-empty-state">
              <span className="badge">No Department Tasks</span>
              <h2>
                {safeData.is_learner
                  ? `No calendar tasks are assigned for ${selectedDepartmentLabel} in ${toolbar.title}.`
                  : `No calendar tasks are scheduled for ${selectedDepartmentLabel} in ${toolbar.title}.`}
              </h2>
              <p className="muted">
                Holiday items can still appear in the calendar grid below. The task counters only include LMS quiz,
                assignment, meeting, and module calendar events.
              </p>
            </section>
          ) : null}

          {safeData.calendar_detail_rows?.length ? (
            <div className="card-grid react-calendar-detail-grid">
              {safeData.calendar_detail_rows.map((item) => (
                <article className="card compact-card react-calendar-detail-card" key={item.label}>
                  <span className="badge">{item.label}</span>
                  <strong>{item.value}</strong>
                  <p className="muted">{item.hint}</p>
                </article>
              ))}
            </div>
          ) : null}

          <CalendarFilterBar
            data={safeData}
            toolbarTitle={toolbar.title}
            selectedDepartmentLabel={selectedDepartmentLabel}
            onSelectDepartment={selectDepartment}
            onNavigate={navigate}
          />

          <HolidayFilterPanel
            holidayFilters={holidayFilters}
            selectedHolidayKeys={selectedHolidayKeys}
            onToggleHoliday={toggleHoliday}
            onSelectAllHolidays={selectAllHolidays}
            showTasks={showTasks}
            onToggleTasks={toggleTasks}
          />

          <section className="calendar-board-surface">
            <div className="calendar-grid calendar-header calendar-header-google">
              {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((day) => (
                <div key={day}>{day}</div>
              ))}
            </div>

            {safeData.weeks.map((week, weekIndex) => (
              <div className="calendar-grid calendar-grid-google" key={`week-${weekIndex}`}>
                {week.map((cell) => (
                  (() => {
                    const visibleEvents = cell.events.filter((event) => {
                      if (event.kind === "task") {
                        return showTasks;
                      }
                      if (event.kind === "holiday") {
                        return Boolean(event.holiday_calendar_key && selectedHolidayKeys.includes(event.holiday_calendar_key));
                      }
                      return true;
                    });

                    return (
                  <article
                    key={cell.iso_date}
                    className={`calendar-cell calendar-cell-google ${!cell.in_month ? "calendar-cell-muted" : ""} ${cell.is_today ? "calendar-cell-today-google" : ""}`}
                  >
                    {cell.create_url ? (
                      <a className="calendar-day-launch" href={cell.create_url}>
                        <div className="calendar-day-wrap calendar-day-wrap-google">
                          <div className={`calendar-day-number ${cell.is_today ? "calendar-day-number-today" : ""}`}>
                            {new Date(cell.iso_date).getDate()}
                          </div>
                          {cell.is_today ? <span className="calendar-today-pill">Today</span> : null}
                          <span className="calendar-day-add">Add task</span>
                        </div>
                      </a>
                    ) : (
                      <div className="calendar-day-wrap calendar-day-wrap-google">
                        <div className={`calendar-day-number ${cell.is_today ? "calendar-day-number-today" : ""}`}>
                          {new Date(cell.iso_date).getDate()}
                        </div>
                        {cell.is_today ? <span className="calendar-today-pill">Today</span> : null}
                      </div>
                    )}

                    <div className="calendar-events calendar-events-google">
                      {visibleEvents.length ? visibleEvents.map((event) =>
                        event.kind === "task" ? (
                          <button
                            key={event.id}
                            type="button"
                            className={`calendar-task-pill calendar-task-pill-${event.kind} calendar-task-pill-button`}
                            onClick={(nativeEvent) => openTaskOverview(nativeEvent, event)}
                            style={{ "--task-color": event.department_color || event.color } as TaskColorStyle}
                          >
                            <strong>{event.title}</strong>
                            <span>{event.type_label}</span>
                            {event.section_title ? <small>Section: {event.section_title}</small> : null}
                            <small>{event.subtitle}</small>
                          </button>
                        ) : (
                          <div
                            key={event.id}
                            className={`calendar-task-pill calendar-task-pill-${event.kind}`}
                            style={{ "--task-color": event.color } as TaskColorStyle}
                          >
                            <strong>{event.title}</strong>
                            <span>{event.type_label}</span>
                            <small>{event.subtitle}</small>
                          </div>
                        )
                      ) : (
                        <p className="calendar-empty-text">No visible items</p>
                      )}
                    </div>
                  </article>
                    );
                  })()
                ))}
              </div>
            ))}
          </section>

          <TaskOverviewModal
            task={activeTask}
            canManage={safeData.can_manage}
            onClose={closeTaskOverview}
          />
        </>
      ) : null}
    </section>
  );
}

const rootElement = document.getElementById("react-calendar-root");

if (rootElement) {
  const endpoint = rootElement.dataset.endpoint || "";
  const initialMonth = rootElement.dataset.initialMonth || String(new Date().getMonth() + 1);
  const initialYear = rootElement.dataset.initialYear || String(new Date().getFullYear());
  const initialDepartment = rootElement.dataset.initialDepartment || "";
  createRoot(rootElement).render(
    <CalendarApp
      endpoint={endpoint}
      initialMonth={initialMonth}
      initialYear={initialYear}
      initialDepartment={initialDepartment}
    />
  );
}
