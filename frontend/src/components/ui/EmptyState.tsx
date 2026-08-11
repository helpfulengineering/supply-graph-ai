import { Inbox } from "lucide-react";

/** Any icon component that renders an svg — lucide glyph or illustration. */
type IconComponent = (props: { className?: string }) => React.ReactNode;

interface Props {
  icon?: IconComponent;
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
      <Icon className="h-10 w-10 text-text-faint" />
      <p className="text-base font-medium text-foreground">{heading}</p>
      {body && <p className="max-w-sm text-sm text-muted-foreground">{body}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
