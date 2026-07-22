import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getOkwDisclosure,
  setOkwDisclosure,
  type DisclosureGroup,
  type DisclosureProfile,
} from "../../api/ohm/okw";
import { useAuth } from "../../context/AuthContext";

const GROUPS: { id: DisclosureGroup; label: string; hint: string }[] = [
  { id: "identity", label: "Identity", hint: "Name and status (always included)" },
  { id: "location", label: "Location", hint: "Address, access, loading dock" },
  { id: "equipment", label: "Equipment", hint: "Machines and tools" },
  { id: "operations", label: "Operations", hint: "Hours, contact, capacity" },
  { id: "supply", label: "Supply", hint: "Materials and products" },
];

function AudienceEditor({
  label,
  audience,
  profile,
  disabled,
  onChange,
}: {
  label: string;
  audience: "followers" | "public";
  profile: DisclosureProfile;
  disabled: boolean;
  onChange: (next: DisclosureProfile) => void;
}) {
  const selected = new Set(profile[audience].groups);
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
    <div className="space-y-2">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
        {label}
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

function Preview({ profile }: { profile: DisclosureProfile }) {
  const fmt = (groups: DisclosureGroup[]) =>
    groups.length ? groups.join(", ") : "identity";
  return (
    <div className="rounded-md bg-slate-50 p-3 text-xs text-slate-600 dark:bg-slate-950 dark:text-slate-300">
      <p className="font-semibold text-slate-700 dark:text-slate-200">Peers will see</p>
      <p className="mt-1">Followers: {fmt(profile.followers.groups)}</p>
      <p>Public: {fmt(profile.public.groups)}</p>
      <p className="mt-2 text-slate-500">
        Default is identity only until you opt in to location, equipment, or other groups.
      </p>
    </div>
  );
}

export function DisclosureControl({ id }: { id: string }) {
  const { hasWrite, reportAuthFailure } = useAuth();
  const queryClient = useQueryClient();
  const queryKey = ["okw", "disclosure", id];

  const query = useQuery({
    queryKey,
    queryFn: () => getOkwDisclosure(id),
  });

  const mutation = useMutation({
    mutationFn: (profile: DisclosureProfile) => setOkwDisclosure(id, profile),
    onSuccess: (data) => {
      queryClient.setQueryData(queryKey, data);
    },
    onError: reportAuthFailure,
  });

  const profile = query.data?.disclosure;

  return (
    <section
      aria-labelledby="okw-disclosure-heading"
      className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900"
    >
      <h2
        id="okw-disclosure-heading"
        className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400"
      >
        Sharing / disclosure
      </h2>

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
              onChange={(next) => mutation.mutate(next)}
            />
            <AudienceEditor
              label="Public"
              audience="public"
              profile={profile}
              disabled={!hasWrite || mutation.isPending}
              onChange={(next) => mutation.mutate(next)}
            />
          </div>
          <Preview profile={profile} />
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
    </section>
  );
}
