import type { AnchorHTMLAttributes, ButtonHTMLAttributes, ReactNode } from "react";

type ButtonTone = "primary" | "secondary";

type BaseButtonProps = {
  children: ReactNode;
  tone?: ButtonTone;
  className?: string;
};

type NativeButtonProps = BaseButtonProps &
  ButtonHTMLAttributes<HTMLButtonElement> & {
    href?: never;
  };

type LinkButtonProps = BaseButtonProps &
  AnchorHTMLAttributes<HTMLAnchorElement> & {
    href: string;
  };

export type ButtonProps = NativeButtonProps | LinkButtonProps;

function buttonClassName({ tone = "primary", className = "" }: Pick<BaseButtonProps, "tone" | "className">) {
  const toneClass = tone === "secondary" ? "button-secondary" : "";
  return ["button", toneClass, className].filter(Boolean).join(" ");
}

export function Button(props: ButtonProps) {
  const { children, tone = "primary", className = "" } = props;
  const mergedClassName = buttonClassName({ tone, className });

  if (props.href) {
    const { href, tone: _tone, className: _className, children: _children, ...anchorProps } = props as LinkButtonProps;
    return (
      <a {...anchorProps} className={mergedClassName} href={href}>
        {children}
      </a>
    );
  }

  const {
    type = "button",
    tone: _tone,
    className: _className,
    children: _children,
    ...buttonProps
  } = props as NativeButtonProps;
  return (
    <button {...buttonProps} className={mergedClassName} type={type}>
      {children}
    </button>
  );
}
