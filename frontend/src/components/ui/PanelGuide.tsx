import Link from "next/link";

/**
 * One-line orientation under a settings/people panel title, plus an optional
 * docs link. Keeps intros consistent without a tour framework.
 */
export function PanelGuide({
  intro,
  docsHref,
  docsLabel = "Read the guide",
}: {
  intro: string;
  docsHref?: string;
  docsLabel?: string;
}) {
  return (
    <div className="mt-1 space-y-1 text-sm text-muted-foreground">
      <p>{intro}</p>
      {docsHref ? (
        <p>
          <Link
            href={docsHref}
            className="inline-flex min-h-11 items-center underline underline-offset-2"
          >
            {docsLabel}
          </Link>
        </p>
      ) : null}
    </div>
  );
}
