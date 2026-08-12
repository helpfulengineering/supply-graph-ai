"use client";

import { useState, type FormEvent } from "react";
import { FIELD, FIELD_SM, LABEL } from "../../components/ui/field";
import Link from "next/link";
import { PageHero } from "../../components/layout/PageHero";
import { useRouter } from "next/navigation";
import { useAuth } from "../../context/AuthContext";
import { ApiError } from "../../api/ohm/client";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/Badge";
import type { ValidationResult } from "../../api/ohm/okh";

type CreateFn = (
  content: Record<string, unknown>,
  opts: { author?: string; onBehalfOf?: string },
) => Promise<{ id: string }>;

type ValidateFn = (
  content: Record<string, unknown>,
) => Promise<ValidationResult>;

interface Props {
  title: string;
  listHref: string;
  listLabel: string;
  detailHref: (id: string) => string;
  validate: ValidateFn;
  create: CreateFn;
  /**
   * Text the editor opens with, for a record that came from somewhere else —
   * a converted OKH-LOSH file, a datasheet. Read once, at mount: this is a
   * starting point, not a controlled value, and re-seeding it under a typing
   * cursor would discard the edits it is there to invite.
   */
  initialJson?: string;
}

export function CreateJsonRecordPage({
  title,
  listHref,
  listLabel,
  detailHref,
  validate,
  create,
  initialJson = "",
}: Props) {
  const router = useRouter();
  const { hasWrite, reportAuthFailure } = useAuth();
  const [jsonText, setJsonText] = useState(initialJson);
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
      setError(
        "Creating requires a write-capable API key. Connect one in Settings.",
      );
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
      router.push(detailHref(id));
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
      <nav className="flex items-center gap-2 text-sm text-muted-foreground">
        <Link href={listHref} className="hover:text-primary-ink">
          {listLabel}
        </Link>
        <span aria-hidden="true">›</span>
        <span className="text-foreground">New</span>
      </nav>

      <PageHero
        title={title}
        description="Paste or upload JSON, optionally validate, then create. Visibility defaults to private on the server."
      />

      {!hasWrite && (
        <p className={`${FIELD} border-warning/30 bg-warning/10 text-warning`}>
          You need a write-capable API key to create. Browse still works;
          connect a key in Settings if you are an admin.
        </p>
      )}

      <form onSubmit={onCreate} className="space-y-4">
        <label className={LABEL}>
          JSON
          <textarea
            value={jsonText}
            onChange={(e) => setJsonText(e.target.value)}
            rows={16}
            spellCheck={false}
            className={`${FIELD_SM} mt-1 w-full`}
            placeholder="{ … }"
            required
          />
        </label>

        <label className={LABEL}>
          Or upload a file
          <input
            type="file"
            accept=".json,application/json"
            className="mt-1 block text-sm"
            onChange={(e) => onFile(e.target.files?.[0])}
          />
        </label>

        <div className="grid gap-3 sm:grid-cols-2">
          <label className={LABEL}>
            Author (optional)
            <input
              value={author}
              onChange={(e) => setAuthor(e.target.value)}
              placeholder="did:key:… or external id"
              className={`${FIELD} mt-1 w-full`}
            />
          </label>
          <label className={LABEL}>
            On behalf of (optional)
            <input
              value={onBehalfOf}
              onChange={(e) => setOnBehalfOf(e.target.value)}
              placeholder="space DID"
              className={`${FIELD} mt-1 w-full`}
            />
          </label>
        </div>

        {error && (
          <p className="text-sm text-destructive" role="alert">
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
