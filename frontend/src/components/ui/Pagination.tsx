interface Props {
  page: number;
  totalPages: number;
  totalItems: number;
  pageSize: number;
  onPage: (p: number) => void;
}

export function Pagination({ page, totalPages, totalItems, pageSize, onPage }: Props) {
  if (totalPages <= 1) return null;

  const start = (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, totalItems);

  const pages: (number | "…")[] = [];
  if (totalPages <= 7) {
    for (let i = 1; i <= totalPages; i++) pages.push(i);
  } else {
    pages.push(1);
    if (page > 3) pages.push("…");
    for (let i = Math.max(2, page - 1); i <= Math.min(totalPages - 1, page + 1); i++) {
      pages.push(i);
    }
    if (page < totalPages - 2) pages.push("…");
    pages.push(totalPages);
  }

  return (
    <div className="flex flex-col items-center gap-3 sm:flex-row sm:justify-between">
      <p className="text-sm text-slate-500 dark:text-slate-400">
        {start}–{end} of {totalItems}
      </p>
      <div className="flex items-center gap-1">
        <PagBtn onClick={() => onPage(page - 1)} disabled={page === 1} label="← Prev" />
        {pages.map((p, i) =>
          p === "…" ? (
            <span key={`ellipsis-${i}`} className="px-2 text-slate-400">…</span>
          ) : (
            <PagBtn
              key={p}
              onClick={() => onPage(p)}
              disabled={p === page}
              active={p === page}
              label={String(p)}
            />
          )
        )}
        <PagBtn onClick={() => onPage(page + 1)} disabled={page === totalPages} label="Next →" />
      </div>
    </div>
  );
}

function PagBtn({
  onClick, disabled, active = false, label,
}: {
  onClick: () => void;
  disabled: boolean;
  active?: boolean;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={[
        "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
        active
          ? "bg-indigo-600 text-white"
          : disabled
            ? "cursor-not-allowed text-slate-300 dark:text-slate-600"
            : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800",
      ].join(" ")}
    >
      {label}
    </button>
  );
}
