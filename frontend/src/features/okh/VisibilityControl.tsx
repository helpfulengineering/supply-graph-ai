import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "../../components/ui/button";
import { FIELD, LABEL } from "../../components/ui/field";
import {
  getOkhVisibility,
  setOkhVisibility,
  type VisibilityLevel,
} from "../../api/ohm/okh";
import { getOkwVisibility, setOkwVisibility } from "../../api/ohm/okw";
import { useAuth } from "../../context/AuthContext";
import { Badge } from "../../components/ui/Badge";
import { PANEL } from "../../components/ui/surface";
import { SECTION_LABEL } from "../../components/ui/typography";

export const LEVELS: VisibilityLevel[] = [
  "private",
  "members",
  "followers",
  "public",
];

/** Who receives a record at each level — shown before a change applies (#576). */
export const AUDIENCE: Record<VisibilityLevel, string> = {
  private:
    "Only you. Nobody else can list, search or open it, and it is never sent to another node.",
  members:
    "Everyone signed in to this node. Anonymous visitors and other nodes do not receive it.",
  followers:
    "Anyone visiting this node, signed in or not, and the nodes that follow this one.",
  public:
    "Anyone who asks this node for its catalogue: every visitor and any other node.",
};

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
  const [chosen, setChosen] = useState<VisibilityLevel | null>(null);

  const query = useQuery({
    queryKey,
    queryFn: () =>
      kind === "okh" ? getOkhVisibility(id) : getOkwVisibility(id),
  });

  const mutation = useMutation({
    mutationFn: (visibility: VisibilityLevel) =>
      kind === "okh"
        ? setOkhVisibility(id, visibility)
        : setOkwVisibility(id, visibility),
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
  const pending = chosen && chosen !== level ? chosen : null;
  const showHint =
    hint !== undefined
      ? hint
      : kind === "okw"
        ? "private keeps the facility to you; members shows it to everyone signed in here; followers/public export a redacted projection controlled by disclosure below."
        : null;

  const body = (
    <>
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 id={`${kind}-visibility-heading`} className={SECTION_LABEL}>
          Who can receive this
        </h2>
        {level && <Badge variant="indigo">{level}</Badge>}
      </div>

      {query.isLoading && (
        <p className="text-sm text-muted-foreground">Loading…</p>
      )}
      {query.isError && (
        <p className="text-sm text-destructive">
          {query.error instanceof Error
            ? query.error.message
            : "Failed to load visibility."}
        </p>
      )}

      {query.isSuccess && (
        <label className={LABEL}>
          <span className="sr-only">Visibility level</span>
          <select
            value={pending ?? level ?? "private"}
            disabled={!hasWrite || mutation.isPending}
            onChange={(e) => setChosen(e.target.value as VisibilityLevel)}
            className={`${FIELD} mt-1 w-full max-w-xs`}
          >
            {LEVELS.map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </select>
        </label>
      )}
      {pending && (
        <div className="mt-3 space-y-2 text-sm" role="status">
          <p className="text-foreground">
            <span className="font-medium">Who will see this: </span>
            {AUDIENCE[pending]}
          </p>
          <div className="flex gap-2">
            <Button
              size="sm"
              disabled={mutation.isPending}
              onClick={() => mutation.mutate(pending)}
            >
              {mutation.isPending ? "Applying…" : `Apply ${pending}`}
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={mutation.isPending}
              onClick={() => setChosen(null)}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}
      {showHint ? (
        <p className="mt-2 text-xs text-muted-foreground">{showHint}</p>
      ) : null}

      {!hasWrite && (
        <p className="mt-2 text-xs text-muted-foreground">
          Changing visibility requires a write-capable API key.
        </p>
      )}
      {mutation.isError && (
        <p className="mt-2 text-sm text-destructive" role="alert">
          {mutation.error instanceof Error
            ? mutation.error.message
            : "Update failed."}
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
    <section aria-labelledby={`${kind}-visibility-heading`} className={PANEL}>
      {body}
    </section>
  );
}
