import { Inbox, type LucideIcon } from "lucide-react";

interface Props {
  icon?: LucideIcon;
  heading: string;
  body?: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({
  icon: Icon = Inbox,
  heading,
  body,
  action,
  className = "",
}: Props) {
  return (
    <div
      className={`flex flex-col items-center justify-center gap-3 py-20 text-center ${className}`}
    >
      <Icon aria-hidden="true" className="h-10 w-10 text-text-faint" strokeWidth={1.5} />
      <p className="text-base font-medium text-foreground">{heading}</p>
      {body && <p className="max-w-sm text-sm text-muted-foreground">{body}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
