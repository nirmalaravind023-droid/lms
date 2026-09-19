import type { ReactNode } from "react";

import { Button, type ButtonProps } from "./Button";

type EmptyStateProps = {
  badge: string;
  title: string;
  children: ReactNode;
  action?: ButtonProps;
  className?: string;
};

export function EmptyState({ badge, title, children, action, className = "" }: EmptyStateProps) {
  return (
    <section className={["card compact-card react-empty-state", className].filter(Boolean).join(" ")}>
      <span className="badge">{badge}</span>
      <h2>{title}</h2>
      <p className="muted">{children}</p>
      {action ? (
        <div className="react-empty-state-actions">
          <Button {...action} />
        </div>
      ) : null}
    </section>
  );
}
