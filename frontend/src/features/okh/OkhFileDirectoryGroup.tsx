import { useState } from "react";
import { okhFileHref } from "./okhFileHref";
import type { DirectoryTreeNode } from "./okhFilePath";
import type { OkhFileRef } from "../../types/okh";
import { canPreviewFile, filePrimaryLabel, ROOT_DIRECTORY_LABEL } from "./okhFilePath";

interface FileRowProps {
  okhId: string;
  file: OkhFileRef;
  selected: boolean;
  onPreview: (file: OkhFileRef) => void;
}

function FileRow({ okhId, file, selected, onPreview }: FileRowProps) {
  const href = okhFileHref(okhId, file);
  const label = filePrimaryLabel(file);
  const typeBadge = file.file_type_display ?? file.file_type ?? "";

  return (
    <li
      className={`flex items-center justify-between gap-3 rounded-lg border px-3 py-2 ${
        selected
          ? "border-indigo-300 bg-indigo-50 dark:border-indigo-700 dark:bg-indigo-950/30"
          : "border-slate-100 bg-slate-50 dark:border-slate-800 dark:bg-slate-800/50"
      }`}
    >
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-slate-700 dark:text-slate-200">
          {label}
        </p>
        <p className="truncate font-mono text-xs text-slate-500 dark:text-slate-400">
          {file.display_path ?? file.path}
        </p>
        {file.metadata && Object.keys(file.metadata).length > 0 && (
          <p className="text-xs text-slate-500 dark:text-slate-500">
            {Object.entries(file.metadata)
              .map(([k, v]) => `${k}: ${v}`)
              .join(" · ")}
          </p>
        )}
        {typeBadge && (
          <p className="mt-0.5 text-xs text-slate-400">{typeBadge}</p>
        )}
      </div>
      <div className="flex shrink-0 gap-1.5">
        {canPreviewFile(file) && (
          <button
            type="button"
            onClick={() => onPreview(file)}
            className="rounded bg-white px-2 py-0.5 text-xs font-medium text-indigo-600 shadow-sm ring-1 ring-slate-200 hover:ring-indigo-300 dark:bg-slate-700 dark:text-indigo-400 dark:ring-slate-600"
          >
            Preview
          </button>
        )}
        <a
          href={href}
          download
          className="rounded bg-white px-2 py-0.5 text-xs font-medium text-slate-500 shadow-sm ring-1 ring-slate-200 hover:text-indigo-600 hover:ring-indigo-300 dark:bg-slate-700 dark:text-slate-300 dark:ring-slate-600"
        >
          Download
        </a>
      </div>
    </li>
  );
}

interface Props {
  node: DirectoryTreeNode;
  okhId: string;
  selectedPath: string | null;
  onPreview: (file: OkhFileRef) => void;
  depth?: number;
  defaultCollapsed?: boolean;
}

export function OkhFileDirectoryGroup({
  node,
  okhId,
  selectedPath,
  onPreview,
  depth = 0,
  defaultCollapsed = false,
}: Props) {
  const isRoot = node.directory === ROOT_DIRECTORY_LABEL;
  const [collapsed, setCollapsed] = useState(
    isRoot ? false : defaultCollapsed && depth > 0,
  );

  const hasContent = node.files.length > 0 || node.children.length > 0;
  if (!hasContent) return null;

  const dirLabel = isRoot ? "/" : `${node.name}/`;
  const fileCount =
    node.files.length +
    node.children.reduce((sum, child) => sum + countFiles(child), 0);

  return (
    <div className={depth > 0 ? "ml-3 border-l border-slate-200 pl-3 dark:border-slate-700" : ""}>
      <button
        type="button"
        onClick={() => setCollapsed((c) => !c)}
        title={isRoot ? "/" : `${node.directory}/`}
        className="flex w-full items-center gap-2 rounded-md px-1 py-0.5 text-left text-xs font-semibold tracking-wide text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
        aria-expanded={!collapsed}
      >
        <span aria-hidden="true">{collapsed ? "▸" : "▾"}</span>
        <span className="truncate font-mono">{dirLabel}</span>
        <span className="ml-auto shrink-0 text-slate-400">{fileCount}</span>
      </button>
      {!collapsed && (
        <div className="mt-1.5 space-y-1.5">
          {node.files.length > 0 && (
            <ul className="space-y-1.5">
              {node.files.map((f, i) => (
                <FileRow
                  key={`${f.path}-${i}`}
                  okhId={okhId}
                  file={f}
                  selected={selectedPath === f.path}
                  onPreview={onPreview}
                />
              ))}
            </ul>
          )}
          {node.children.map((child) => (
            <OkhFileDirectoryGroup
              key={child.directory}
              node={child}
              okhId={okhId}
              selectedPath={selectedPath}
              onPreview={onPreview}
              depth={depth + 1}
              defaultCollapsed={defaultCollapsed}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function countFiles(node: DirectoryTreeNode): number {
  return (
    node.files.length +
    node.children.reduce((sum, child) => sum + countFiles(child), 0)
  );
}
