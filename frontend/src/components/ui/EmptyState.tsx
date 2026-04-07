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
      <p className="text-base font-medium text-slate-700 dark:text-slate-300">{heading}</p>
      {body && <p className="max-w-sm text-sm text-slate-500 dark:text-slate-400">{body}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
