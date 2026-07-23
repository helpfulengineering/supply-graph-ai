import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../../context/AuthContext";
import { ApiError } from "../../api/ohm/client";
import { createOkw, updateOkw, validateOkw } from "../../api/ohm/okw";
import { fetchProcessTaxonomy } from "../../api/ohm/taxonomy";
import { Button } from "../../components/ui/button";
import { ProcessTaxonomyPicker } from "./ProcessTaxonomyPicker";
import {
  ACCESS_TYPES,
  FACILITY_STATUSES,
  emptyFacilityForm,
  facilityToForm,
  formClientErrors,
  formToOkwContent,
  formToUpdateBody,
  importJsonToForm,
  type FacilityFormState,
  type TaxonomyProcess,
} from "./facilityFormModel";

const fieldClass =
  "mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-950";
const compactClass =
  "rounded-md border border-slate-300 px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-950";

type Mode = "create" | "edit";

interface Props {
  mode: Mode;
  facilityId?: string;
  initialFacility?: Parameters<typeof facilityToForm>[0];
}

export function FacilityForm({ mode, facilityId, initialFacility }: Props) {
  const navigate = useNavigate();
  const { hasWrite, reportAuthFailure } = useAuth();
  const taxonomyQuery = useQuery({
    queryKey: ["taxonomy", "processes"],
    queryFn: fetchProcessTaxonomy,
    staleTime: 60_000,
  });
  const taxonomy: TaxonomyProcess[] = taxonomyQuery.data ?? [];

  const [state, setState] = useState<FacilityFormState>(() =>
    initialFacility ? facilityToForm(initialFacility, []) : emptyFacilityForm(),
  );
  // Re-map process selection once taxonomy loads (edit mode).
  const [hydrated, setHydrated] = useState(!initialFacility);
  useEffect(() => {
    if (!initialFacility || !taxonomy.length || hydrated) return;
    setState(facilityToForm(initialFacility, taxonomy));
    setHydrated(true);
  }, [initialFacility, taxonomy, hydrated]);

  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [importText, setImportText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const patch = (partial: Partial<FacilityFormState>) =>
    setState((s) => ({ ...s, ...partial }));

  const processOptions = useMemo(() => {
    const ids = new Set([
      ...state.selectedParents,
      ...state.selectedSubtypes,
      ...state.equipment.map((e) => e.processId),
    ]);
    return taxonomy.filter((p) => ids.has(p.canonical_id) || !p.parent);
  }, [taxonomy, state.selectedParents, state.selectedSubtypes, state.equipment]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (!hasWrite) {
      setError(
        "Saving requires a write-capable API key. Follow the steps above to connect one.",
      );
      reportAuthFailure(new ApiError(401, "Authentication required"));
      return;
    }

    const clientErrs = formClientErrors(state);
    if (clientErrs.length) {
      setError(clientErrs.join(". "));
      return;
    }

    const content = formToOkwContent(state, taxonomy);
    setBusy(true);
    try {
      const result = await validateOkw(content);
      if (!result.is_valid) {
        const msgs = (result.errors ?? [])
          .map((err) =>
            typeof err === "string"
              ? err
              : ((err as { message?: string }).message ?? JSON.stringify(err)),
          )
          .filter(Boolean);
        setError(
          msgs.length
            ? `Validation failed: ${msgs.join("; ")}`
            : "Validation failed. Fix the issues and try again.",
        );
        return;
      }

      if (mode === "create") {
        const { id } = await createOkw(content, {
          author: state.author.trim() || undefined,
          onBehalfOf: state.onBehalfOf.trim() || undefined,
        });
        navigate(`/facilities/${id}?created=1`);
        return;
      }

      if (!facilityId) throw new Error("Missing facility id");
      await updateOkw(
        facilityId,
        formToUpdateBody(state, taxonomy) as Parameters<typeof updateOkw>[1],
      );
      navigate(`/facilities/${facilityId}`);
    } catch (err) {
      reportAuthFailure(err);
      setError(err instanceof Error ? err.message : "Save failed.");
    } finally {
      setBusy(false);
    }
  }

  function applyImport() {
    const { form, error: importError } = importJsonToForm(importText, taxonomy);
    if (importError || !form) {
      setError(importError ?? "Import failed.");
      return;
    }
    setState(form);
    setError(null);
    setAdvancedOpen(true);
  }

  const title = mode === "create" ? "New facility" : "Edit facility";

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <nav className="flex items-center gap-2 text-sm text-slate-500">
        <Link to="/facilities" className="hover:text-indigo-600">
          Facilities
        </Link>
        <span aria-hidden="true">›</span>
        <span className="text-slate-700 dark:text-slate-200">{title}</span>
      </nav>

      <div>
        <h1 className="text-2xl font-bold text-foreground">{title}</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Useful details up front; hours, equipment, and JSON import are optional. Visibility
          defaults to private until you share.
        </p>
      </div>

      {!hasWrite && (
        <div
          className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-100"
          role="status"
        >
          <p className="font-medium">Connect a write-capable API key to save</p>
          <ol className="mt-2 list-decimal space-y-1 pl-5">
            <li>
              Open{" "}
              <Link to="/settings/session" className="underline font-medium">
                Settings → Session
              </Link>{" "}
              and paste a key with <code className="text-xs">write</code> (or{" "}
              <code className="text-xs">admin</code>).
            </li>
            <li>
              On a new node, start from the env <code className="text-xs">API_KEYS</code>{" "}
              bootstrap token, then create a named key under Keys &amp; accounts if you are an
              admin.
            </li>
            <li>Return here and save the facility.</li>
          </ol>
          <p className="mt-2 text-xs opacity-90">
            Details: <code className="text-xs">docs/auth/frontend.md</code>
          </p>
        </div>
      )}

      <form onSubmit={(e) => void onSubmit(e)} className="space-y-6">
        <section className="space-y-3 rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
            Basics
          </h2>
          <label className="block text-sm font-medium">
            Name *
            <input
              value={state.name}
              onChange={(e) => patch({ name: e.target.value })}
              className={fieldClass}
              required
            />
          </label>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block text-sm font-medium">
              Status
              <select
                value={state.facilityStatus}
                onChange={(e) =>
                  patch({ facilityStatus: e.target.value as FacilityFormState["facilityStatus"] })
                }
                className={fieldClass}
              >
                {FACILITY_STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm font-medium">
              Access
              <select
                value={state.accessType}
                onChange={(e) =>
                  patch({ accessType: e.target.value as FacilityFormState["accessType"] })
                }
                className={fieldClass}
              >
                {ACCESS_TYPES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            <label className="block text-sm font-medium">
              City *
              <input
                value={state.city}
                onChange={(e) => patch({ city: e.target.value })}
                className={fieldClass}
                required
              />
            </label>
            <label className="block text-sm font-medium">
              Region
              <input
                value={state.region}
                onChange={(e) => patch({ region: e.target.value })}
                className={fieldClass}
              />
            </label>
            <label className="block text-sm font-medium">
              Country *
              <input
                value={state.country}
                onChange={(e) => patch({ country: e.target.value })}
                className={fieldClass}
                required
              />
            </label>
          </div>
          <label className="block text-sm font-medium">
            Street (optional)
            <input
              value={state.street}
              onChange={(e) => patch({ street: e.target.value })}
              className={fieldClass}
            />
          </label>
          <label className="block text-sm font-medium">
            Description
            <textarea
              value={state.description}
              onChange={(e) => patch({ description: e.target.value })}
              rows={3}
              className={fieldClass}
            />
          </label>
        </section>

        <section className="space-y-3 rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
            Processes
          </h2>
          <p className="text-xs text-muted-foreground">
            Select parent types; expand a parent to pick more specific subtypes when you want.
          </p>
          {taxonomyQuery.isLoading && (
            <p className="text-sm text-muted-foreground">Loading taxonomy…</p>
          )}
          {taxonomyQuery.isError && (
            <p className="text-sm text-red-600">
              {taxonomyQuery.error instanceof Error
                ? taxonomyQuery.error.message
                : "Failed to load taxonomy."}
            </p>
          )}
          {taxonomy.length > 0 && (
            <ProcessTaxonomyPicker
              taxonomy={taxonomy}
              selectedParents={state.selectedParents}
              selectedSubtypes={state.selectedSubtypes}
              disabled={busy}
              onChange={({ parents, subtypes }) =>
                patch({ selectedParents: parents, selectedSubtypes: subtypes })
              }
            />
          )}
        </section>

        {mode === "create" && (
          <section className="space-y-3 rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
              Attribution (optional)
            </h2>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="block text-sm font-medium">
                Author
                <input
                  value={state.author}
                  onChange={(e) => patch({ author: e.target.value })}
                  placeholder="did:key:… or name:…"
                  className={fieldClass}
                />
              </label>
              <label className="block text-sm font-medium">
                On behalf of (space)
                <input
                  value={state.onBehalfOf}
                  onChange={(e) => patch({ onBehalfOf: e.target.value })}
                  placeholder="space DID"
                  className={fieldClass}
                />
              </label>
            </div>
          </section>
        )}

        <div>
          <button
            type="button"
            className="text-sm font-medium text-indigo-600 hover:underline dark:text-indigo-400"
            onClick={() => setAdvancedOpen((o) => !o)}
            aria-expanded={advancedOpen}
          >
            {advancedOpen ? "Hide advanced" : "Show advanced"} — hours, contact, equipment, import
          </button>
        </div>

        {advancedOpen && (
          <div className="space-y-4">
            <section className="space-y-3 rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                Hours &amp; contact
              </h2>
              <label className="block text-sm font-medium">
                Opening hours
                <input
                  value={state.openingHours}
                  onChange={(e) => patch({ openingHours: e.target.value })}
                  className={fieldClass}
                />
              </label>
              <div className="grid gap-3 sm:grid-cols-3">
                <label className="block text-sm font-medium">
                  Email
                  <input
                    value={state.contactEmail}
                    onChange={(e) => patch({ contactEmail: e.target.value })}
                    className={fieldClass}
                  />
                </label>
                <label className="block text-sm font-medium">
                  Phone
                  <input
                    value={state.contactPhone}
                    onChange={(e) => patch({ contactPhone: e.target.value })}
                    className={fieldClass}
                  />
                </label>
                <label className="block text-sm font-medium">
                  URL
                  <input
                    value={state.contactUrl}
                    onChange={(e) => patch({ contactUrl: e.target.value })}
                    className={fieldClass}
                  />
                </label>
              </div>
            </section>

            <section className="space-y-3 rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                Equipment details
              </h2>
              <p className="text-xs text-muted-foreground">
                Rows with make or model are saved; empty rows are ignored.
              </p>
              {state.equipment.map((row, i) => (
                <div key={i} className="grid gap-2 sm:grid-cols-4">
                  <select
                    value={row.processId}
                    onChange={(e) => {
                      const equipment = [...state.equipment];
                      equipment[i] = { ...row, processId: e.target.value };
                      patch({ equipment });
                    }}
                    className={compactClass}
                  >
                    <option value="">Process…</option>
                    {processOptions.map((p) => (
                      <option key={p.canonical_id} value={p.canonical_id}>
                        {p.display_name}
                      </option>
                    ))}
                  </select>
                  <input
                    placeholder="Make"
                    value={row.make}
                    onChange={(e) => {
                      const equipment = [...state.equipment];
                      equipment[i] = { ...row, make: e.target.value };
                      patch({ equipment });
                    }}
                    className={compactClass}
                  />
                  <input
                    placeholder="Model"
                    value={row.model}
                    onChange={(e) => {
                      const equipment = [...state.equipment];
                      equipment[i] = { ...row, model: e.target.value };
                      patch({ equipment });
                    }}
                    className={compactClass}
                  />
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() =>
                      patch({ equipment: state.equipment.filter((_, j) => j !== i) })
                    }
                  >
                    Remove
                  </Button>
                </div>
              ))}
              <Button
                type="button"
                variant="outline"
                onClick={() =>
                  patch({
                    equipment: [
                      ...state.equipment,
                      {
                        processId: state.selectedSubtypes[0] || state.selectedParents[0] || "",
                        make: "",
                        model: "",
                      },
                    ],
                  })
                }
              >
                Add equipment
              </Button>
            </section>

            <section className="space-y-3 rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                Import JSON
              </h2>
              <p className="text-xs text-muted-foreground">
                Paste OKW JSON to fill the form. For YAML, convert first or use the CLI.
              </p>
              <textarea
                value={importText}
                onChange={(e) => setImportText(e.target.value)}
                rows={6}
                spellCheck={false}
                className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 font-mono text-xs dark:border-slate-600 dark:bg-slate-950"
                placeholder="{ … }"
              />
              <Button type="button" variant="outline" onClick={applyImport}>
                Apply import to form
              </Button>
            </section>
          </div>
        )}

        {error && (
          <p className="text-sm text-red-600 dark:text-red-400" role="alert">
            {error}
          </p>
        )}

        <div className="flex flex-wrap gap-2">
          <Button type="submit" disabled={!hasWrite || busy || taxonomyQuery.isLoading}>
            {busy
              ? "Saving…"
              : mode === "create"
                ? "Create facility"
                : "Save changes"}
          </Button>
          <Button type="button" variant="outline" onClick={() => navigate(-1)}>
            Cancel
          </Button>
        </div>
      </form>
    </div>
  );
}
