"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Badge } from "../../components/ui/Badge";
import type { OkhManifest } from "../../types/okh";
import { deriveCategories, UNCATEGORIZED } from "./categories";
import { formatOkhDisplayTitle } from "./formatOkhDisplayTitle";
import { normalizeHardwareLicense } from "./normalizeHardwareLicense";

interface Props {
  okh: OkhManifest;
}

const PROCESS_COLORS: Record<string, "indigo" | "blue" | "green" | "yellow"> = {
  "3DP": "indigo",
  "3D Printing": "indigo",
  PCB: "blue",
  CNC: "green",
  Assembly: "yellow",
  Laser: "blue",
  "Laser Cutting": "blue",
  Welding: "yellow",
};

function processColor(
  p: string,
): "indigo" | "blue" | "green" | "yellow" | "default" {
  return PROCESS_COLORS[p] ?? "default";
}

export function OkhCard({ okh }: Props) {
  const router = useRouter();
  const title = formatOkhDisplayTitle(okh.title);
  const categories = deriveCategories(okh).filter((c) => c !== UNCATEGORIZED);
  const author = okh.licensor?.name?.trim() || null;
  const license = normalizeHardwareLicense(okh.license?.hardware);

  return (
    <div className="group flex flex-col rounded-xl border border-border bg-card shadow-sm transition-shadow hover:shadow-md">
      <Link
        href={`/okh/${okh.id}`}
        className="flex flex-1 flex-col gap-3 p-5 no-underline"
      >
        <h3 className="font-semibold text-foreground group-hover:text-primary-ink transition-colors break-words">
          {title}
        </h3>

        {(categories.length > 0 || okh.manufacturing_processes.length > 0) && (
          <div className="flex flex-wrap gap-1">
            {categories.slice(0, 3).map((c) => (
              <Badge key={`cat-${c}`} variant="default">
                {c}
              </Badge>
            ))}
            {okh.manufacturing_processes.slice(0, 4).map((p) => (
              <Badge key={`proc-${p}`} variant={processColor(p)}>
                {p}
              </Badge>
            ))}
            {okh.manufacturing_processes.length > 4 && (
              <Badge variant="default">
                +{okh.manufacturing_processes.length - 4}
              </Badge>
            )}
          </div>
        )}

        <div className="mt-auto flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
          {author && <span className="truncate max-w-[180px]">{author}</span>}
          {okh.version && <span>v{okh.version}</span>}
          {license && <span className="truncate max-w-[140px]">{license}</span>}
        </div>
      </Link>

      <div className="flex items-center justify-end border-t border-border px-5 py-3">
        <button
          onClick={(e) => {
            e.stopPropagation();
            router.push(`/match?okh_id=${okh.id}`);
          }}
          className="rounded-md bg-accent px-3 py-1 text-xs font-medium text-primary-ink hover:bg-accent transition-colors"
        >
          Run Match
        </button>
      </div>
    </div>
  );
}
