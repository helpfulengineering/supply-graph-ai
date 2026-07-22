import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getOkwDisclosure,
  getOkwVisibility,
  previewOkwDisclosure,
  setOkwDisclosure,
  type DisclosureAudience,
  type DisclosureGroup,
  type DisclosureProfile,
  type VisibilityLevel,
} from "../../api/ohm/okw";
import { useAuth } from "../../context/AuthContext";

const GROUPS: { id: DisclosureGroup; label: string; hint: string }[] = [
  { id: "identity", label: "Identity", hint: "Name and status (always included)" },
  { id: "location", label: "Location", hint: "Address, access, loading dock" },
  { id: "equipment", label: "Equipment", hint: "Machines and tools" },
  { id: "operations", label: "Operations", hint: "Hours, contact, capacity" },
  { id: "supply", label: "Supply", hint: "Materials and products" },
];

function activeAudience(visibility: VisibilityLevel | undefined): DisclosureAudience | null {
  if (visibility === "followers") return "followers";
  if (visibility === "public") return "public";
  return null;
}

function AudienceEditor({
  label,
  audience,
  profile,
  disabled,
  active,
  onChange,
}: {
  label: string;
  audience: DisclosureAudience;
  profile: DisclosureProfile;
  disabled: boolean;
  active: boolean;
  onChange: (next: DisclosureProfile) => void;
}) {
  const selected = new Set(profile[audience]?.groups ?? ["identity"]);
  const toggle = (g: DisclosureGroup) => {
    if (g === "identity") return;
    const next = new Set(selected);
    if (next.has(g)) next.delete(g);
    else next.add(g);
    next.add("identity");
    onChange({
      ...profile,
      [audience]: { groups: Array.from(next) as DisclosureGroup[] },
    });
  };

  return (
    <div
      className={`space-y-2 ${active ? "" : "opacity-60"}`}
      data-active-audience={active ? "true" : "false"}
    >
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
        {label}
        {active && (
          <span className="ml-2 font-normal normal-case text-indigo-600 dark:text-indigo-400">
            (active for export)
          </span>
        )}
      </p>
      <ul className="space-y-1.5">
        {GROUPS.map((g) => (
          <li key={g.id} className="flex items-start gap-2 text-sm">
            <input
              type="checkbox"
              className="mt-0.5"
              checked={selected.has(g.id)}
              disabled={disabled || g.id === "identity"}
              onChange={() => toggle(g.id)}
              id={`${audience}-${g.id}`}
            />
            <label htmlFor={`${audience}-${g.id}`} className="cursor-pointer">
              <span className="text-slate-800 dark:text-slate-100">{g.label}</span>
              <span className="block text-xs text-slate-500 dark:text-slate-400">{g.hint}</span>
            </label>
          </li>
        ))}
      </ul>
    </div>
  );
}

function PeerPreview({
  id,
  audience,
  visibility,
}: {
  id: string;
  audience: DisclosureAudience | null;
  visibility: VisibilityLevel | undefined;
}) {
  const previewAudience = audience ?? "followers";
  const query = useQuery({
    queryKey: ["okw", "disclosure-preview", id, previewAudience],
    queryFn: () => previewOkwDisclosure(id, previewAudience),
  });

  if (visibility === "private") {
    return (
      <div className="rounded-md bg-slate-50 p-3 text-xs text-slate-600 dark:bg-slate-950 dark:text-slate-300">
        <p className="font-semibold text-slate-700 dark:text-slate-200">Peers will see</p>
        <p className="mt-1" role="status">
          Nothing is exported while visibility is private. Promote to followers or public to
          share a redacted projection.
        </p>
        {query.data && (
          <div className="mt-2">
            <p className="text-slate-500">If promoted to followers, peers would see fields:</p>
            <pre className="mt-1 max-h-40 overflow-auto rounded bg-white p-2 text-[11px] dark:bg-slate-900">
              {JSON.stringify(query.data.facility, null, 2)}
            </pre>
          </div>
        )}
      </div>
    );
  }

  if (query.isLoading) {
    return <p className="text-xs text-muted-foreground">Loading peer preview…</p>;
  }
  if (query.isError || !query.data) {
    return (
      <p className="text-xs text-red-600 dark:text-red-400">
        {query.error instanceof Error ? query.error.message : "Failed to load preview."}
      </p>
    );
  }

  const keys = Object.keys(query.data.facility);
  return (
    <div className="rounded-md bg-slate-50 p-3 text-xs text-slate-600 dark:bg-slate-950 dark:text-slate-300">
      <p className="font-semibold text-slate-700 dark:text-slate-200">Peers will see</p>
      <p className="mt-1">
        Visibility <span className="font-medium">{visibility}</span> exports the{" "}
        <span className="font-medium">{previewAudience}</span> profile
        {query.data.exported ? "" : " (not currently exported)"}.
      </p>
      <p className="mt-1 text-slate-500">
        Groups: {query.data.groups.join(", ") || "identity"} · Fields:{" "}
        {keys.length ? keys.join(", ") : "(none)"}
      </p>
      <pre
        className="mt-2 max-h-48 overflow-auto rounded bg-white p-2 text-[11px] dark:bg-slate-900"
        data-testid="disclosure-preview-json"
      >
        {JSON.stringify(query.data.facility, null, 2)}
      </pre>
    </div>
  );
}

export function DisclosureControl({
  id,
  variant = "card",
}: {
  id: string;
  /** `plain` for embedding inside a parent Sharing panel. */
  variant?: "card" | "plain";
}) {
  const { hasWrite, reportAuthFailure } = useAuth();
  const queryClient = useQueryClient();
  const queryKey = ["okw", "disclosure", id];

  const visibilityQuery = useQuery({
    queryKey: ["okw", "visibility", id],
    queryFn: () => getOkwVisibility(id),
  });
  const visibility = visibilityQuery.data?.visibility;
  const active = activeAudience(visibility);

  const query = useQuery({
    queryKey,
    queryFn: () => getOkwDisclosure(id),
  });

  const mutation = useMutation({
    mutationFn: (profile: DisclosureProfile) => setOkwDisclosure(id, profile),
    onSuccess: (data) => {
      queryClient.setQueryData(queryKey, data);
      void queryClient.invalidateQueries({
        queryKey: ["okw", "disclosure-preview", id],
      });
    },
    onError: reportAuthFailure,
  });

  const profile = query.data?.disclosure;

  const body = (
    <>
      <h2
        id="okw-disclosure-heading"
        className="mb-1 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400"
      >
        How much they see
      </h2>
      <p className="mb-3 text-xs text-slate-500 dark:text-slate-400">
        Field groups included in the federated projection per audience. Identity is always on;
        default is identity only until you opt in.
      </p>

      {query.isLoading && <p className="text-sm text-muted-foreground">Loading…</p>}
      {query.isError && (
        <p className="text-sm text-red-600 dark:text-red-400">
          {query.error instanceof Error ? query.error.message : "Failed to load disclosure."}
        </p>
      )}

      {profile && (
        <div className="space-y-5">
          <div className="grid gap-6 sm:grid-cols-2">
            <AudienceEditor
              label="Followers"
              audience="followers"
              profile={profile}
              disabled={!hasWrite || mutation.isPending}
              active={active === "followers"}
              onChange={(next) => mutation.mutate(next)}
            />
            <AudienceEditor
              label="Public"
              audience="public"
              profile={profile}
              disabled={!hasWrite || mutation.isPending}
              active={active === "public"}
              onChange={(next) => mutation.mutate(next)}
            />
          </div>
          <PeerPreview id={id} audience={active} visibility={visibility} />
        </div>
      )}

      {!hasWrite && (
        <p className="mt-2 text-xs text-muted-foreground">
          Changing disclosure requires a write-capable API key.
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
      <div aria-labelledby="okw-disclosure-heading" className="space-y-1">
        {body}
      </div>
    );
  }

  return (
    <section
      aria-labelledby="okw-disclosure-heading"
      className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900"
    >
      {body}
    </section>
  );
}
