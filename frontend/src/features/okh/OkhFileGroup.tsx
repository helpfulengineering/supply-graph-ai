import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { X } from "lucide-react";
import type { OkhFileRef } from "../../types/okh";
import { OkhFileDirectoryGroup } from "./OkhFileDirectoryGroup";
import { OkhFilePreviewContent } from "./OkhFilePreviewContent";
import { buildDirectoryTree } from "./okhFilePath";
import { CARD_TITLE } from "../../components/ui/typography";
import { cn } from "@/lib/utils";

interface Props {
  okhId: string;
  title: string;
  icon: ReactNode;
  files: OkhFileRef[];
}

export function OkhFileGroup({ okhId, title, icon, files }: Props) {
  const [previewFile, setPreviewFile] = useState<OkhFileRef | null>(null);
  const previewRef = useRef<HTMLDivElement>(null);
  const tree = useMemo(() => buildDirectoryTree(files), [files]);
  const topLevelCount = tree.children.length + (tree.files.length > 0 ? 1 : 0);
  const collapseByDefault = topLevelCount > 8;

  useEffect(() => {
    if (previewFile && previewRef.current) {
      previewRef.current.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
      });
    }
  }, [previewFile]);

  if (files.length === 0) return null;

  return (
    <div>
      <h3 className={cn(CARD_TITLE, "mb-2 flex items-center gap-1.5")}>
        <span aria-hidden="true" className="text-muted-foreground">
          {icon}
        </span>
        {title}
        <span className="ml-1 rounded-full bg-muted px-1.5 py-0.5 text-xs font-medium text-muted-foreground">
          {files.length}
        </span>
      </h3>

      {previewFile && (
        <div ref={previewRef} className="relative">
          <button
            type="button"
            onClick={() => setPreviewFile(null)}
            className="absolute right-2 top-2 z-10 rounded-md px-2 py-1 text-xs text-muted-foreground hover:bg-muted"
            aria-label="Close preview"
          >
            <X aria-hidden="true" className="h-3.5 w-3.5" />
          </button>
          <OkhFilePreviewContent okhId={okhId} file={previewFile} />
        </div>
      )}

      <div className="space-y-2">
        <OkhFileDirectoryGroup
          node={tree}
          okhId={okhId}
          selectedPath={previewFile?.path ?? null}
          onPreview={setPreviewFile}
          defaultCollapsed={collapseByDefault}
        />
      </div>
    </div>
  );
}
