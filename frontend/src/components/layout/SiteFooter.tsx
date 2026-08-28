import { Heart } from "lucide-react";
import { Logo } from "./Logo";

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
    <footer className="border-t border-border bg-card/90 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-center gap-x-4 gap-y-1 px-4 py-3 text-sm text-muted-foreground sm:justify-between sm:px-6">
        {/* The wordmark's one home. The header carries the mark alone, because
            on the dashboard a bar wordmark would sit directly above an h1
            saying the same words — down here nothing competes with it, and the
            app finally states its own name somewhere on every page. */}
        <span className="flex items-center gap-2">
          {/* Decorative here, unlike in the header: the mark's own accessible
              name is the product name, and the words are right beside it. */}
          <span aria-hidden="true" className="flex">
            <Logo className="h-4 w-4" />
          </span>
          <span className="font-medium text-foreground">
            Open Hardware Manager
          </span>
        </span>

        {/*
          A <p> of inline content, not a flex row of fragments. Flex blockifies
          its children, so as a flex item "OpenSource" stops being a link
          inside a line of text and becomes a standalone 81x20 target — under
          the 24x24 WCAG 2.5.8 minimum, with no way to pad it that does not
          break the line. Inline in a paragraph it is sized by the line-height
          of the words around it, which is exactly the condition 2.5.8's inline
          exception describes. e2e/responsive.spec.ts measures this.
        */}
        <p className="text-center">
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
