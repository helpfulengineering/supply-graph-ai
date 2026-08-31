"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { SegmentedControl } from "../../components/ui/SegmentedControl";
import { Badge } from "../../components/ui/Badge";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { ErrorMessage } from "../../components/ui/ErrorMessage";
import { FIELD, LABEL } from "../../components/ui/field";
import { PANEL } from "../../components/ui/surface";
import { SECTION_TITLE } from "../../components/ui/typography";
import {
  fetchOkhInventory,
  fetchOkwInventory,
  type InventoryRow,
} from "../../api/ohm/okh";

type Kind = "designs" | "facilities";

function bytes(size: number | null | undefined): string {
  if (!size) return "—";
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${Math.round(size / 1024)} KB`;
  return `${(size / 1048576).toFixed(1)} MB`;
}

/**
 * What an operator may see, which is not what a record says.
 *
 * An admin's record scope is identical to any other user's — they do not read
 * private records. This is the replacement, and it is deliberately not a browse
 * surface: no row expands, and there is no title here, because a title states
 * intent and intent is most of what a private draft is.
 *
 * It is also the first of several inventory surfaces — storage migration and
 * orphan cleanup want the same shape — so the row contract and this table are
 * meant to be reused rather than reinvented.
 */
export function InventoryPanel() {
  const [kind, setKind] = useState<Kind>("designs");
  const [onlyPrivate, setOnlyPrivate] = useState(false);
  const [owner, setOwner] = useState("");

  const inventory = useQuery({
    queryKey: ["inventory", kind],
    queryFn: kind === "designs" ? fetchOkhInventory : fetchOkwInventory,
  });

  const rows = useMemo(() => {
    let list: InventoryRow[] = inventory.data?.rows ?? [];
    if (onlyPrivate) list = list.filter((r) => r.visibility === "private");
    const needle = owner.trim().toLowerCase();
    if (needle) {
      list = list.filter((r) =>
        `${r.created_by_did ?? ""} ${r.created_by_account ?? ""}`
          .toLowerCase()
          .includes(needle),
      );
    }
    return list;
  }, [inventory.data, onlyPrivate, owner]);

  return (
    <section className={PANEL} aria-labelledby="inventory-heading">
      <h2 id="inventory-heading" className={SECTION_TITLE}>
        Record inventory
      </h2>
      <p className="mt-1 text-sm text-muted-foreground">
        Every record on this node, by its metadata. Content is deliberately not
        shown — including titles. Use this to find, attribute and remove a
        record without reading it.
      </p>

      <div className="mt-4 flex flex-wrap items-end gap-3">
        <SegmentedControl
          label="Record type"
          value={kind}
          onChange={(next) => setKind(next as Kind)}
          options={[
            { value: "designs", label: "Designs" },
            { value: "facilities", label: "Facilities" },
          ]}
        />
        <label className={`${LABEL} min-w-48 flex-1`}>
          Owner
          <input
            value={owner}
            onChange={(e) => setOwner(e.target.value)}
            placeholder="did:key:… or account id"
            className={`${FIELD} mt-1 w-full`}
          />
        </label>
        <label className="flex items-center gap-2 pb-1.5 text-sm">
          <input
            type="checkbox"
            checked={onlyPrivate}
            onChange={(e) => setOnlyPrivate(e.target.checked)}
            className="h-4 w-4"
          />
          Only records nobody else can see
        </label>
      </div>

      {inventory.isPending && (
        <div className="py-8">
          <LoadingSpinner />
        </div>
      )}
      {inventory.error && <ErrorMessage error={inventory.error} />}

      {inventory.data && (
        <>
          <p className="mt-4 text-sm text-muted-foreground">
            {inventory.data.total} record(s), {inventory.data.privateTotal}{" "}
            visible only to their owner.
          </p>
          <div className="mt-2 overflow-x-auto">
            <table className="w-full text-sm">
              <caption className="sr-only">
                Record inventory: identifiers and metadata only
              </caption>
              <thead>
                <tr className="border-b border-border text-left">
                  <th scope="col" className="py-2 pr-3 font-medium">Id</th>
                  <th scope="col" className="py-2 pr-3 font-medium">Owner</th>
                  <th scope="col" className="py-2 pr-3 font-medium">Visibility</th>
                  <th scope="col" className="py-2 pr-3 font-medium">Size</th>
                  <th scope="col" className="py-2 font-medium">Last write</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id} className="border-b border-border/60">
                    <td className="py-2 pr-3 font-mono text-xs">{row.id}</td>
                    <td className="py-2 pr-3 break-all font-mono text-xs">
                      {row.created_by_did ?? row.created_by_account ?? "—"}
                    </td>
                    <td className="py-2 pr-3">
                      <Badge
                        variant={row.visibility === "private" ? "yellow" : "green"}
                      >
                        {row.visibility}
                      </Badge>
                    </td>
                    <td className="py-2 pr-3 tabular-nums">{bytes(row.size_bytes)}</td>
                    <td className="py-2 tabular-nums text-muted-foreground">
                      {row.modified_at ? row.modified_at.slice(0, 10) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {rows.length === 0 && (
            <p className="mt-3 text-sm text-muted-foreground">
              {inventory.data.total === 0
                ? "This node holds no records yet."
                : "No records match those filters."}
            </p>
          )}
        </>
      )}
    </section>
  );
}
