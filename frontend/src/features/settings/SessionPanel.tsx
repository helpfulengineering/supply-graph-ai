import { useState, type FormEvent } from "react";
import { FIELD_MONO, FIELD_SM } from "../../components/ui/field";
import { Badge } from "../../components/ui/Badge";
import { useAuth } from "../../context/AuthContext";

export function SessionPanel() {
  const { token, user, isLoading, authError, setToken, clear } = useAuth();
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);

  async function onSave(e: FormEvent) {
    e.preventDefault();
    if (!draft.trim()) return;
    setSaving(true);
    try {
      await setToken(draft.trim());
      setDraft("");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      <section
        aria-labelledby="session-key-heading"
        className="rounded-xl border border-border bg-card p-5"
      >
        <h2
          id="session-key-heading"
          className="text-lg font-semibold text-foreground"
        >
          API key
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Paste a Bearer token for this browser tab (stored in sessionStorage
          only).
        </p>

        <form onSubmit={onSave} className="mt-4 space-y-3">
          <label className="block text-sm font-medium text-foreground">
            Token
            <input
              type="password"
              autoComplete="off"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder={token ? "•••••••• (replace current)" : "ohm_…"}
              className={`${FIELD_MONO} mt-1 w-full`}
            />
          </label>
          <div className="flex flex-wrap gap-2">
            <button
              type="submit"
              disabled={saving || !draft.trim()}
              className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-on-accent hover:bg-primary disabled:opacity-50"
            >
              {saving ? "Saving…" : "Save"}
            </button>
            <button
              type="button"
              onClick={() => clear()}
              disabled={!token}
              className={`${FIELD_SM} font-medium hover:bg-background dark:hover:bg-muted`}
            >
              Clear session
            </button>
          </div>
        </form>
      </section>

      <section
        aria-labelledby="session-identity-heading"
        className="rounded-xl border border-border bg-card p-5"
      >
        <h2
          id="session-identity-heading"
          className="text-lg font-semibold text-foreground"
        >
          Current identity
        </h2>
        {!token && (
          <p className="mt-2 text-sm text-muted-foreground">
            No API key in this session.
          </p>
        )}
        {token && isLoading && (
          <p className="mt-2 text-sm text-muted-foreground">Loading whoami…</p>
        )}
        {token && authError && (
          <p className="mt-2 text-sm text-destructive" role="alert">
            {authError.message}
          </p>
        )}
        {user && (
          <dl className="mt-3 space-y-2 text-sm">
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Name
              </dt>
              <dd className="text-foreground">{user.name}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Account
              </dt>
              <dd className="font-mono text-xs text-foreground">
                {user.account_id}
              </dd>
            </div>
            {user.subject_did && (
              <div>
                <dt className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  DID
                </dt>
                <dd className="break-all font-mono text-xs text-foreground">
                  {user.subject_did}
                </dd>
              </div>
            )}
            <div>
              <dt className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Permissions
              </dt>
              <dd className="flex flex-wrap gap-1.5">
                {user.permissions.map((p) => (
                  <Badge key={p} variant={p === "admin" ? "indigo" : "blue"}>
                    {p}
                  </Badge>
                ))}
              </dd>
            </div>
          </dl>
        )}
      </section>
    </div>
  );
}
