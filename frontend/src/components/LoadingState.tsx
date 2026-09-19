type LoadingStateProps = {
  badge?: string;
  title: string;
  description: string;
  compact?: boolean;
};

export function LoadingState({ badge = "Loading", title, description, compact = false }: LoadingStateProps) {
  return (
    <div className={compact ? "react-calendar-loading-overlay-card" : "react-calendar-loading"}>
      <div
        className={compact ? "react-calendar-loader react-calendar-loader-compact" : "react-calendar-loader"}
        aria-hidden="true"
      >
        <span />
        <span />
        <span />
      </div>
      {compact ? null : <span className="badge">{badge}</span>}
      {compact ? <strong>{title}</strong> : <h1>{title}</h1>}
      <p className="muted">{description}</p>
    </div>
  );
}
