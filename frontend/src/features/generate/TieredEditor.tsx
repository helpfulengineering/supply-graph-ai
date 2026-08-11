/**
 * Guided tiered review editor (Slice B).
 *
 * Scalars and simple lists get structured inputs. Nested structures are shown
 * read-only with a raw-JSON escape hatch, deliberately: a partial nested editor
 * that silently drops fields would be worse than an honest text area, and
 * materials/BOM are exactly the fields generation gets wrong most often.
 */

import { useState } from "react";
import { FIELD, FIELD_SM } from "../../components/ui/field";
import {
  getPath,
  humanizeKey,
  isEmptyValue,
  setPath,
  tier3Fields,
  TIER1,
  TIER2_GROUPS,
  type FieldSpec,
} from "./manifestTiers";

type Manifest = Record<string, unknown>;

interface EditorProps {
  manifest: Manifest;
  onChange: (next: Manifest) => void;
}

function asText(value: unknown): string {
  if (value === null || value === undefined) return "";
  return typeof value === "string" ? value : String(value);
}

function ScalarField({
  field,
  manifest,
  onChange,
}: EditorProps & { field: FieldSpec }) {
  const value = getPath(manifest, field.path);
  const empty = isEmptyValue(value);
  const long = field.path === "function" || field.path === "description";
  const id = `f-${field.path}`;
  return (
    <label htmlFor={id} className="block">
      <span className="block text-sm font-medium text-foreground">
        {field.label}
        {empty && (
          <span className="ml-2 text-xs text-warning">not extracted</span>
        )}
      </span>
      {field.hint && (
        <span className="mt-0.5 block text-xs text-muted-foreground">
          {field.hint}
        </span>
      )}
      {long ? (
        <textarea
          id={id}
          rows={3}
          value={asText(value)}
          onChange={(e) =>
            onChange(setPath(manifest, field.path, e.target.value))
          }
          className={`${FIELD} mt-1 w-full`}
        />
      ) : (
        <input
          id={id}
          type="text"
          value={asText(value)}
          onChange={(e) =>
            onChange(setPath(manifest, field.path, e.target.value))
          }
          className={`${FIELD} mt-1 w-full`}
        />
      )}
    </label>
  );
}

/** Simple string lists render as removable chips plus an add box. */
function ListField({
  field,
  manifest,
  onChange,
}: EditorProps & { field: FieldSpec }) {
  const [draft, setDraft] = useState("");
  const raw = getPath(manifest, field.path);
  const items = Array.isArray(raw) ? raw.map(asText) : [];
  const id = `f-${field.path}`;

  const commit = (next: string[]) =>
    onChange(setPath(manifest, field.path, next));

  return (
    <div>
      <span className="block text-sm font-medium text-foreground">
        {field.label}
      </span>
      {field.hint && (
        <span className="mt-0.5 block text-xs text-muted-foreground">
          {field.hint}
        </span>
      )}
      <ul
        className="mt-1 flex flex-wrap gap-1.5"
        aria-label={`${field.label} values`}
      >
        {items.map((item, i) => (
          <li
            key={`${item}-${i}`}
            className="inline-flex items-center gap-1 rounded-full bg-muted px-2.5 py-1 text-xs"
          >
            {item}
            <button
              type="button"
              aria-label={`Remove ${item}`}
              onClick={() => commit(items.filter((_, j) => j !== i))}
              className="text-muted-foreground hover:text-foreground"
            >
              ×
            </button>
          </li>
        ))}
        {items.length === 0 && (
          <li className="text-xs text-warning">nothing extracted</li>
        )}
      </ul>
      <div className="mt-1.5 flex gap-2">
        <input
          id={id}
          type="text"
          value={draft}
          placeholder={`Add ${field.label.toLowerCase()}…`}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && draft.trim()) {
              e.preventDefault();
              commit([...items, draft.trim()]);
              setDraft("");
            }
          }}
          className={`${FIELD} flex-1`}
        />
        <button
          type="button"
          onClick={() => {
            if (!draft.trim()) return;
            commit([...items, draft.trim()]);
            setDraft("");
          }}
          className={FIELD_SM}
        >
          Add
        </button>
      </div>
    </div>
  );
}

/** Nested values: read-only view plus a raw-JSON editor that validates on change. */
function NestedField({
  field,
  manifest,
  onChange,
}: EditorProps & { field: FieldSpec }) {
  const value = getPath(manifest, field.path);
  const [open, setOpen] = useState(false);
  const [text, setText] = useState(() =>
    JSON.stringify(value ?? null, null, 2),
  );
  const [error, setError] = useState<string | null>(null);

  return (
    <div>
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-foreground">
          {field.label}
        </span>
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className="text-xs text-primary-ink"
        >
          {open ? "Done" : "Edit as JSON"}
        </button>
      </div>
      {field.hint && (
        <span className="mt-0.5 block text-xs text-muted-foreground">
          {field.hint}
        </span>
      )}
      {open ? (
        <>
          <textarea
            aria-label={`${field.label} JSON`}
            rows={8}
            value={text}
            onChange={(e) => {
              setText(e.target.value);
              try {
                onChange(
                  setPath(manifest, field.path, JSON.parse(e.target.value)),
                );
                setError(null);
              } catch {
                setError(
                  "Not valid JSON — changes are not applied while this is broken.",
                );
              }
            }}
            className={`${FIELD_SM} mt-1 w-full`}
          />
          {error && (
            <p role="alert" className="mt-1 text-xs text-destructive">
              {error}
            </p>
          )}
        </>
      ) : (
        <pre className="mt-1 max-h-40 overflow-auto rounded-md bg-background p-2 font-mono text-xs">
          {isEmptyValue(value)
            ? "nothing extracted"
            : JSON.stringify(value, null, 2)}
        </pre>
      )}
    </div>
  );
}

function Field(props: EditorProps & { field: FieldSpec }) {
  if (props.field.kind === "list") return <ListField {...props} />;
  if (props.field.kind === "nested") return <NestedField {...props} />;
  return <ScalarField {...props} />;
}

export function TieredEditor({ manifest, onChange }: EditorProps) {
  const [showTier3, setShowTier3] = useState(false);
  const extras = tier3Fields(manifest);

  return (
    <div className="space-y-6">
      <section aria-labelledby="tier1">
        <h3 id="tier1" className="text-sm font-semibold text-foreground">
          Required
        </h3>
        <p className="mt-0.5 text-xs text-muted-foreground">
          A design can't be saved without these.
        </p>
        <div className="mt-3 grid gap-4 sm:grid-cols-2">
          {TIER1.map((field) => (
            <Field
              key={field.path}
              field={field}
              manifest={manifest}
              onChange={onChange}
            />
          ))}
        </div>
      </section>

      {TIER2_GROUPS.map((group) => (
        <section key={group.id} aria-labelledby={`tier2-${group.id}`}>
          <h3
            id={`tier2-${group.id}`}
            className="text-sm font-semibold text-foreground"
          >
            {group.title}
          </h3>
          {group.blurb && (
            <p className="mt-0.5 text-xs text-muted-foreground">
              {group.blurb}
            </p>
          )}
          <div className="mt-3 space-y-4">
            {group.fields.map((field) => (
              <Field
                key={field.path}
                field={field}
                manifest={manifest}
                onChange={onChange}
              />
            ))}
          </div>
        </section>
      ))}

      {extras.length > 0 && (
        <section aria-labelledby="tier3">
          <button
            type="button"
            id="tier3"
            onClick={() => setShowTier3((s) => !s)}
            className="text-sm font-semibold text-primary-ink"
          >
            {showTier3 ? "Hide" : "Show"} everything else ({extras.length})
          </button>
          {showTier3 && (
            <div className="mt-3 space-y-4">
              {extras.map((field) => (
                <Field
                  key={field.path}
                  field={{ ...field, label: humanizeKey(field.path) }}
                  manifest={manifest}
                  onChange={onChange}
                />
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
