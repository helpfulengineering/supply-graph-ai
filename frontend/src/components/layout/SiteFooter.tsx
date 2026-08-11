import { Heart } from "lucide-react";

/**
 * The repository this build came from.
 *
 * Branch is injected at build time so a preview deployment points at the branch
 * it was built from rather than always at main — in open source the useful
 * question from a running instance is "where is the code that made THIS", and
 * an always-main link answers a different one. Falls back to main for local
 * builds, where the answer is whatever is checked out anyway.
 */
const REPO = "https://github.com/binaryLady/OHM";
const BRANCH = process.env.NEXT_PUBLIC_GIT_BRANCH || "main";
const SOURCE_URL = `${REPO}/tree/${BRANCH}`;

export function SiteFooter() {
  return (
    <footer className="border-t border-border bg-card">
      <div className="mx-auto flex max-w-7xl items-center justify-center gap-1.5 px-6 py-4 text-sm text-muted-foreground">
        made with
        <Heart aria-hidden="true" className="h-4 w-4 text-primary-ink" fill="currentColor" />
        <span className="sr-only">heart</span>
        by{" "}
        <a
          href={SOURCE_URL}
          target="_blank"
          rel="noreferrer"
          title={`Source for this build — ${BRANCH}`}
          className="font-medium text-primary-ink underline-offset-2 hover:underline"
        >
          OpenSource
        </a>
      </div>
    </footer>
  );
}
