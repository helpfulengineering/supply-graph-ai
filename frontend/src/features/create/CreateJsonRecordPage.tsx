import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { ApiError } from "../../api/ohm/client";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/Badge";
import type { ValidationResult } from "../../api/ohm/okh";

type CreateFn = (
  content: Record<string, unknown>,
  opts: { author?: string; onBehalfOf?: string },
) => Promise<{ id: string }>;

type ValidateFn = (content: Record<string, unknown>) => Promise<ValidationResult>;

interface Props {
  title: string;
  listHref: string;
  listLabel: string;
  detailHref: (id: string) => string;
  validate: ValidateFn;
  create: CreateFn;
}

export function CreateJsonRecordPage({
  title,
  listHref,
  listLabel,
  detailHref,
  validate,
  create,
}: Props) {
  const navigate = useNavigate();
  const { hasWrite, reportAuthFailure } = useAuth();
  const [jsonText, setJsonText] = useState("");
  const [author, setAuthor] = useState("");
  const [onBehalfOf, setOnBehalfOf] = useState("");
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<"validate" | "create" | null>(null);

  function parseContent(): Record<string, unknown> | null {
    try {
      const parsed = JSON.parse(jsonText) as unknown;
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
        setError("JSON must be an object.");
        return null;
      }
      return parsed as Record<string, unknown>;
    } catch {
      setError("Invalid JSON.");
      return null;
    }
  }

  async function onValidate() {
    const content = parseContent();
    if (!content) return;
    setBusy("validate");
    setError(null);
    try {
      setValidation(await validate(content));
    } catch (e) {
      setValidation(null);
      setError(e instanceof Error ? e.message : "Validation failed.");
    } finally {
      setBusy(null);
    }
  }

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    if (!hasWrite) {
      setError("Creating requires a write-capable API key. Connect one in Settings.");
      reportAuthFailure(new ApiError(401, "Authentication required"));
      return;
    }
    const content = parseContent();
    if (!content) return;
    setBusy("create");
    setError(null);
    try {
      const { id } = await create(content, {
        author: author.trim() || undefined,
        onBehalfOf: onBehalfOf.trim() || undefined,
      });
      navigate(detailHref(id));
    } catch (err) {
      reportAuthFailure(err);
      setError(err instanceof Error ? err.message : "Create failed.");
    } finally {
      setBusy(null);
    }
  }

  function onFile(file: File | undefined) {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === "string") setJsonText(reader.result);
    };
    reader.readAsText(file);
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <nav className="flex items-center gap-2 text-sm text-slate-500">
        <Link to={listHref} className="hover:text-indigo-600">
          {listLabel}
        </Link>
        <span aria-hidden="true">›</span>
        <span className="text-slate-700 dark:text-slate-200">New</span>
      </nav>

      <div>
        <h1 className="text-2xl font-bold text-foreground">{title}</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Paste or upload JSON, optionally validate, then create. Visibility defaults to
          private on the server.
        </p>
      </div>

      {!hasWrite && (
        <p className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-100">
          You need a write-capable API key to create. Browse still works; connect a key in
          Settings if you are an admin.
        </p>
      )}

      <form onSubmit={onCreate} className="space-y-4">
        <label className="block text-sm font-medium">
          JSON
          <textarea
            value={jsonText}
            onChange={(e) => setJsonText(e.target.value)}
            rows={16}
            spellCheck={false}
            className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 font-mono text-xs dark:border-slate-600 dark:bg-slate-950"
            placeholder="{ … }"
            required
          />
        </label>

        <label className="block text-sm font-medium">
          Or upload a file
          <input
            type="file"
            accept=".json,application/json"
            className="mt-1 block text-sm"
            onChange={(e) => onFile(e.target.files?.[0])}
          />
        </label>

        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block text-sm font-medium">
            Author (optional)
            <input
              value={author}
              onChange={(e) => setAuthor(e.target.value)}
              placeholder="did:key:… or external id"
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-950"
            />
          </label>
          <label className="block text-sm font-medium">
            On behalf of (optional)
            <input
              value={onBehalfOf}
              onChange={(e) => setOnBehalfOf(e.target.value)}
              placeholder="space DID"
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-950"
            />
          </label>
        </div>

        {error && (
          <p className="text-sm text-red-600 dark:text-red-400" role="alert">
            {error}
          </p>
        )}

        {validation && (
          <div className="flex items-center gap-2 text-sm">
            <Badge variant={validation.is_valid ? "green" : "yellow"}>
              {validation.is_valid ? "Valid" : "Needs attention"}
            </Badge>
            <span className="text-muted-foreground">
              score {Math.round(validation.score * 100)}%
            </span>
          </div>
        )}

        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="outline"
            disabled={busy !== null || !jsonText.trim()}
            onClick={() => void onValidate()}
          >
            {busy === "validate" ? "Validating…" : "Validate"}
          </Button>
          <Button type="submit" disabled={busy !== null || !jsonText.trim()}>
            {busy === "create" ? "Creating…" : "Create"}
          </Button>
        </div>
      </form>
    </div>
  );
}
