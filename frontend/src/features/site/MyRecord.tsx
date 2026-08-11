"use client";

import { cn } from "@/lib/utils";
import { useEffect, useId, useRef, useState, type FormEvent } from "react";
import { PANEL } from "../../components/ui/surface";
import { CAPTION, CARD_TITLE } from "../../components/ui/typography";
import { FIELD, LABEL } from "../../components/ui/field";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/Badge";
import { instant, since } from "../../lib/site/format";
import { deleteOwn, myRecord, updateOwnName, type Visitor } from "../../lib/site/stack";
import { useSiteQuery } from "../../lib/site/useSiteQuery";

interface MyRecordProps {
  visitor: Visitor;
  /** The row is gone: forget it on this device too. */
  onErased: () => void;
  onSignOut: () => void;
}

/**
 * The visitor's own row — the one record a visitor may read unmasked and
 * change, keyed by the email they claimed at the gate.
 *
 * THE CLAIM IS THE WHOLE PERMISSION, and the schema is built around that being
 * weak: an unauthenticated email can reach exactly the row that matches it,
 * and `is_admin` is unreachable from here at any price. So the honest scope of
 * this panel is self-service — rename yourself, erase yourself — and it says
 * so rather than implying the address was verified.
 *
 * Erase is the one that matters. The panel above used to promise a visitor
 * could "rename it, or erase it and every telemetry event attributed to it"
 * while offering neither control; the RPCs for both have been in schema.sql
 * since the v2 access model. A stated right to erasure with no button is worse
 * than no claim at all.
 */
export function MyRecord({ visitor, onErased, onSignOut }: MyRecordProps) {
  const record = useSiteQuery(() => myRecord(visitor.email), [visitor.email]);
  const [name, setName] = useState(visitor.name);
  const [saving, setSaving] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const fieldId = useId();

  /**
   * Whether the field is ahead of the server — a ref, not state, and that is
   * the whole point.
   *
   * The server's name should win once it arrives, because another tab or an
   * operator may have renamed this row since the device last wrote it down.
   * It must not win over something half-typed: the fetch settles after the
   * field is already interactive, so a sync that does not check would snatch
   * back a rename mid-word.
   *
   * A `useState` flag loses that check to batching. The handler's update and
   * the fetch's update land in one flush, so the effect can run in a commit
   * where the flag has not taken yet and overwrite the edit anyway. A ref is
   * written synchronously inside the handler, so by the time any effect reads
   * it, it is already true.
   */
  const edited = useRef(false);

  useEffect(() => {
    if (record.data && !edited.current) setName(record.data.name);
  }, [record.data]);

  async function onRename(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setSaving(true);
    setSaved(false);
    const result = await updateOwnName(visitor.email, name.trim());
    setSaving(false);
    setFailure(result.ok ? null : result.error);
    if (result.ok) {
      setSaved(true);
      // Saved, so the field is no longer ahead of the server and may follow it
      // again.
      edited.current = false;
      record.reload();
    }
  }

  async function onErase(): Promise<void> {
    const ok = window.confirm(
      `Erase the record for ${visitor.email}, and every telemetry event attributed to it? This cannot be undone.`,
    );
    if (!ok) return;
    const result = await deleteOwn(visitor.email);
    if (result.ok) onErased();
    else setFailure(result.error);
  }

  const seen = record.data;
  const unchanged = name.trim() === (seen?.name ?? visitor.name);

  return (
    <section className={PANEL} aria-labelledby={`${fieldId}-heading`}>
      <h2 id={`${fieldId}-heading`} className={CARD_TITLE}>
        My record{" "}
        {seen?.isAdmin && (
          <Badge variant="indigo" className="ml-1 align-middle">
            admin marker
          </Badge>
        )}
      </h2>
      <p className={cn("mt-1 font-mono", CAPTION)}>{visitor.email}</p>

      {seen && (
        <p className={cn("mt-2", CAPTION)}>
          First seen <time title={instant(seen.firstSeen)}>{since(seen.firstSeen)}</time>
          {" · "}last seen <time title={instant(seen.lastSeen)}>{since(seen.lastSeen)}</time>
        </p>
      )}
      {record.error && (
        <p className="mt-2 text-sm text-destructive" role="alert">
          {record.error}
        </p>
      )}

      <form onSubmit={onRename} className="mt-4 space-y-2">
        <label htmlFor={fieldId} className={LABEL}>
          Name
        </label>
        <input
          id={fieldId}
          value={name}
          maxLength={120}
          onChange={(e) => {
            setName(e.target.value);
            edited.current = true;
            setSaved(false);
          }}
          className={FIELD}
        />
        <div className="flex flex-wrap items-center gap-2">
          <Button type="submit" size="lg" disabled={saving || unchanged || !name.trim()}>
            {saving ? "Saving…" : "Rename"}
          </Button>
          {saved && (
            <span className="text-xs text-success-ink" role="status">
              Saved
            </span>
          )}
        </div>
      </form>

      {failure && (
        <p className="mt-3 text-sm text-destructive" role="alert">
          {failure}
        </p>
      )}

      <div className="mt-4 flex flex-wrap gap-2 border-t border-border pt-4">
        <Button type="button" variant="outline" size="lg" onClick={onSignOut}>
          Sign out
        </Button>
        <Button type="button" variant="destructive" size="lg" onClick={() => void onErase()}>
          Erase my record
        </Button>
      </div>
      <p className={cn("mt-2", CAPTION)}>
        Signing out forgets this record on this device. Erasing deletes the row
        and every telemetry event attributed to it.
      </p>
    </section>
  );
}
