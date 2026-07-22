import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getOkhVisibility,
  setOkhVisibility,
  type VisibilityLevel,
} from "../../api/ohm/okh";
import { getOkwVisibility, setOkwVisibility } from "../../api/ohm/okw";
import { useAuth } from "../../context/AuthContext";
import { Badge } from "../../components/ui/Badge";

const LEVELS: VisibilityLevel[] = ["private", "followers", "public"];

export function VisibilityControl({
  kind,
  id,
  variant = "card",
  hint,
}: {
  kind: "okh" | "okw";
  id: string;
  /** `plain` for embedding inside a parent Sharing panel. */
  variant?: "card" | "plain";
  /** Override the default okw hint; pass empty string to hide. */
  hint?: string;
}) {
  const { hasWrite, reportAuthFailure } = useAuth();
  const queryClient = useQueryClient();
  const queryKey = [kind, "visibility", id];

  const query = useQuery({
    queryKey,
    queryFn: () => (kind === "okh" ? getOkhVisibility(id) : getOkwVisibility(id)),
  });

  const mutation = useMutation({
    mutationFn: (visibility: VisibilityLevel) =>
      kind === "okh" ? setOkhVisibility(id, visibility) : setOkwVisibility(id, visibility),
    onSuccess: (data) => {
      queryClient.setQueryData(queryKey, data);
      if (kind === "okw") {
        void queryClient.invalidateQueries({
          queryKey: ["okw", "disclosure-preview", id],
        });
      }
    },
    onError: reportAuthFailure,
  });

  const level = query.data?.visibility;
  const showHint =
    hint !== undefined
      ? hint
      : kind === "okw"
        ? "private keeps the facility local; followers/public export a redacted projection controlled by disclosure below."
        : null;

  const body = (
    <>
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2
          id={`${kind}-visibility-heading`}
          className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400"
        >
          Who can receive this
        </h2>
        {level && <Badge variant="indigo">{level}</Badge>}
      </div>

      {query.isLoading && <p className="text-sm text-muted-foreground">Loading…</p>}
      {query.isError && (
        <p className="text-sm text-red-600 dark:text-red-400">
          {query.error instanceof Error ? query.error.message : "Failed to load visibility."}
        </p>
      )}

      {query.isSuccess && (
        <label className="block text-sm">
          <span className="sr-only">Visibility level</span>
          <select
            value={level ?? "private"}
            disabled={!hasWrite || mutation.isPending}
            onChange={(e) => mutation.mutate(e.target.value as VisibilityLevel)}
            className="mt-1 w-full max-w-xs rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-950 disabled:opacity-50"
          >
            {LEVELS.map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </select>
        </label>
      )}
      {showHint ? (
        <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">{showHint}</p>
      ) : null}

      {!hasWrite && (
        <p className="mt-2 text-xs text-muted-foreground">
          Changing visibility requires a write-capable API key.
        </p>
      )}
      {mutation.isError && (
        <p className="mt-2 text-sm text-red-600" role="alert">
          {mutation.error instanceof Error ? mutation.error.message : "Update failed."}
        </p>
      )}
    </>
  );

  if (variant === "plain") {
    return (
      <div aria-labelledby={`${kind}-visibility-heading`} className="space-y-1">
        {body}
      </div>
    );
  }

  return (
    <section
      aria-labelledby={`${kind}-visibility-heading`}
      className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900"
    >
      {body}
    </section>
  );
}
