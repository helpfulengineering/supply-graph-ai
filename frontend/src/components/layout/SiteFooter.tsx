import { Heart } from "lucide-react";

export function SiteFooter() {
  return (
    <footer className="border-t border-border bg-card">
      <div className="mx-auto flex max-w-7xl items-center justify-center gap-1.5 px-6 py-6 text-sm text-muted-foreground">
        made with
        <Heart
          aria-hidden="true"
          className="h-4 w-4 text-primary-ink"
          fill="currentColor"
        />
        <span className="sr-only">heart</span>
        by OpenSource
      </div>
    </footer>
  );
}
