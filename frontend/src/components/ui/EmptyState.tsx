interface Props {
  icon?: string;
  heading: string;
  body?: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({ icon = "📭", heading, body, action, className = "" }: Props) {
  return (
    <div className={`flex flex-col items-center justify-center gap-3 py-20 text-center ${className}`}>
      <span className="text-4xl" aria-hidden="true">{icon}</span>
      <p className="text-base font-medium text-foreground">{heading}</p>
      {body && <p className="max-w-sm text-sm text-muted-foreground">{body}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
