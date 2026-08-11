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
      {/*
        A sentence, laid out as one. It was a flex row of fragments, which
        blockifies its children — so "OpenSource" stopped being a link inside a
        line of text and became a standalone 81x20 target, under the 24x24
        WCAG 2.5.8 minimum with no way to pad it without breaking the line.
        As inline content in a <p> it is sized by the line-height of the text
        around it, which is the condition 2.5.8's inline exception describes.
      */}
      <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6">
        <p className="text-center text-sm text-muted-foreground">
          made with{" "}
          <Heart
            aria-hidden="true"
            className="inline h-4 w-4 align-text-bottom text-primary-ink"
            fill="currentColor"
          />
          <span className="sr-only">heart</span> by{" "}
          <a
            href={SOURCE_URL}
            target="_blank"
            rel="noreferrer"
            title={`Source for this build — ${BRANCH}`}
            className="font-medium text-primary-ink underline-offset-2 hover:underline"
          >
            OpenSource
          </a>
        </p>
      </div>
    </footer>
  );
}
