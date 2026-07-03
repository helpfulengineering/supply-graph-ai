import { useState } from "react";
import type { OkhFileRef } from "../../types/okh";
import { buildFileTree, pickHeadlineFiles, type FileTreeNode } from "./fileTree";
import { cn } from "@/lib/utils";

function TreeNode({ node, depth }: { node: FileTreeNode; depth: number }) {
  const [open, setOpen] = useState(true);
  const pad = { paddingLeft: `${depth * 16}px` };

  if (node.file) {
    return (
      <div className="flex items-center gap-2 py-0.5 text-sm text-slate-700 dark:text-slate-200" style={pad}>
        <span aria-hidden="true">📄</span>
        <span className="truncate">{node.name}</span>
      </div>
    );
  }
  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 py-0.5 text-sm font-medium text-slate-700 dark:text-slate-200"
        style={pad}
      >
        <span aria-hidden="true">{open ? "📂" : "📁"}</span>
        {node.name}
        <span className="text-xs text-slate-400 dark:text-slate-500">({node.children.length})</span>
      </button>
      {open && node.children.map((c) => <TreeNode key={c.path} node={c} depth={depth + 1} />)}
    </div>
  );
}

export function OkhFilesView({ files }: { files: OkhFileRef[] }) {
  const [mode, setMode] = useState<"headline" | "tree">("headline");
  const tree = buildFileTree(files);
  const headline = pickHeadlineFiles(files);

  return (
    <div>
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          Files &amp; Documentation ({files.length})
        </h2>
        <div className="inline-flex overflow-hidden rounded-md border border-input text-xs">
          {(["headline", "tree"] as const).map((m) => (
            <button
              key={m}
              type="button"
              aria-pressed={mode === m}
              onClick={() => setMode(m)}
              className={cn(
                "px-2.5 py-1 capitalize transition-colors",
                mode === m ? "bg-primary text-primary-foreground" : "bg-background hover:bg-accent",
              )}
            >
              {m === "tree" ? "File tree" : "Headline"}
            </button>
          ))}
        </div>
      </div>

      {files.length === 0 ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">No file references attached.</p>
      ) : mode === "headline" ? (
        headline.length === 0 ? (
          <p className="text-sm text-slate-500 dark:text-slate-400">
            No headline files identified — switch to File tree to browse all {files.length}.
          </p>
        ) : (
          <ul className="space-y-1">
            {headline.map((f) => (
              <li
                key={f.path}
                className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-200"
              >
                <span aria-hidden="true">📄</span>
                <span className="truncate">{f.title || f.path}</span>
              </li>
            ))}
          </ul>
        )
      ) : (
        <div className="max-h-96 overflow-auto">
          {tree.children.map((c) => (
            <TreeNode key={c.path} node={c} depth={0} />
          ))}
        </div>
      )}
    </div>
  );
}
