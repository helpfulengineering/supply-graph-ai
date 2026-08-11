"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import type { OkhManifest } from "../../types/okh";
import { deriveCategories, UNCATEGORIZED } from "./categories";
import { formatOkhDisplayTitle } from "./formatOkhDisplayTitle";
import { normalizeHardwareLicense } from "./normalizeHardwareLicense";

interface Props {
  okh: OkhManifest;
}

export function OkhListRow({ okh }: Props) {
  const router = useRouter();
  const title = formatOkhDisplayTitle(okh.title);
  const category =
    deriveCategories(okh).find((c) => c !== UNCATEGORIZED) ?? UNCATEGORIZED;
  const author = okh.licensor?.name?.trim() || "—";
  const license = normalizeHardwareLicense(okh.license?.hardware) ?? "—";
  const processes = (okh.manufacturing_processes ?? []).slice(0, 3).join(", ");

  return (
    <div className="flex flex-col gap-2 border-b border-border py-3 last:border-0 sm:flex-row sm:items-center sm:gap-4">
      <Link
        href={`/okh/${okh.id}`}
        className="min-w-0 flex-1 no-underline hover:text-primary-ink"
      >
        <div className="font-medium text-foreground break-words">{title}</div>
        <div className="mt-0.5 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-muted-foreground">
          <span>{category}</span>
          {processes && <span>{processes}</span>}
          <span>{author}</span>
          {okh.version && <span>v{okh.version}</span>}
          <span>{license}</span>
        </div>
      </Link>
      <button
        onClick={() => router.push(`/match?okh_id=${okh.id}`)}
        className="shrink-0 self-start rounded-md bg-accent px-3 py-1 text-xs font-medium text-primary-ink hover:bg-accent transition-colors sm:self-center"
      >
        Run Match ⚡
      </button>
    </div>
  );
}
