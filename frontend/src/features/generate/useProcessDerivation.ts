import { useRef, useState, type Dispatch, type SetStateAction } from "react";
import { normalizeOkh } from "../../api/ohm/okh";

type Manifest = Record<string, unknown>;

/** Whether the draft's derived process fields match its process list. */
export type DerivationState = "current" | "updating" | "failed";

/** The fields the node derives from `manufacturing_processes`. */
const DERIVED = ["manufacturing_specs", "tsdc"] as const;

/**
 * Keeps a draft's process requirements and TSDC codes in line with its process
 * list (#562), so what is downloaded or matched never names a removed process.
 *
 * Asks the node on each change to the list; only the answer to the latest
 * list is applied, and only to the derived fields, so edits made meanwhile
 * survive. `load` replaces the draft and clears a failure from the last one.
 */
export function useProcessDerivation(
  manifest: Manifest | null,
  setManifest: Dispatch<SetStateAction<Manifest | null>>,
) {
  const ticket = useRef(0);
  const [state, setState] = useState<DerivationState>("current");

  const derive = (draft: Manifest) => {
    const mine = ++ticket.current;
    setState("updating");
    normalizeOkh(draft).then(
      (derived) => {
        if (mine !== ticket.current) return;
        setManifest((m) => m && withDerived(m, derived));
        setState("current");
      },
      () => {
        if (mine === ticket.current) setState("failed");
      },
    );
  };

  return {
    state,
    edit(next: Manifest) {
      setManifest(next);
      const before = JSON.stringify(manifest?.manufacturing_processes ?? []);
      if (JSON.stringify(next.manufacturing_processes ?? []) !== before) derive(next);
    },
    retry() {
      if (manifest) derive(manifest);
    },
    load(next: Manifest | null) {
      ticket.current++;
      setState("current");
      setManifest(next);
    },
  };
}

function withDerived(manifest: Manifest, derived: Manifest): Manifest {
  const next = { ...manifest };
  for (const key of DERIVED) if (key in derived) next[key] = derived[key];
  return next;
}
