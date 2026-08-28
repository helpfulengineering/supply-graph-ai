"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchPeerPackage,
  packageFetchSentence,
} from "../../api/ohm/federation";
import type { PeerState } from "../../api/ohm/federation";
import { Button } from "../../components/ui/button";
import {
  CHECKBOX,
  CHOICE_ROW,
  FIELD,
  HINT,
  LABEL,
} from "../../components/ui/field";
import { PANEL, PANEL_INSET } from "../../components/ui/surface";
import { CAPTION, SECTION_TITLE } from "../../components/ui/typography";
import { useAuth } from "../../context/AuthContext";
import { cn } from "@/lib/utils";

/**
 * Pull a package from a peer into this node.
 *
 * The outbound half of federation, and the only endpoint under
 * /api/federation that a browser should ever call — the rest of that router is
 * what other nodes call on us.
 *
 * The peer field is a select over the peers the panel already lists rather
 * than a URL box: a hand-typed peer is a typo waiting to become a confusing
 * network error, and the panel above already knows the answer.
 */
export function PeerPackageFetch({ peers }: { peers: PeerState[] }) {
  const { hasWrite, reportAuthFailure } = useAuth();
  const queryClient = useQueryClient();
  const [peerUrl, setPeerUrl] = useState("");
  const [bundleHash, setBundleHash] = useState("");
  const [allowRebuild, setAllowRebuild] = useState(true);

  const fetchIt = useMutation({
    mutationFn: () =>
      fetchPeerPackage({
        peerUrl,
        bundleHash: bundleHash.trim(),
        allowRebuild,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["package-list"] });
    },
    onError: reportAuthFailure,
  });

  const options = peers
    .map((p) => (p as { url?: string; did?: string }).url ?? "")
    .filter(Boolean);

  return (
    <section aria-labelledby="peer-package-heading" className={PANEL}>
      <h2 id="peer-package-heading" className={SECTION_TITLE}>
        Fetch a package from a peer
      </h2>
      <p className={cn(CAPTION, "mt-1")}>
        Copies a built package into this node, rebuilding it from the
        peer&rsquo;s manifest if the bytes are not available.
      </p>

      <form
        className="mt-4 space-y-3"
        onSubmit={(e) => {
          e.preventDefault();
          if (peerUrl && bundleHash.trim()) fetchIt.mutate();
        }}
      >
        <div>
          <label className={LABEL} htmlFor="peer-url">
            Peer
          </label>
          <select
            id="peer-url"
            value={peerUrl}
            onChange={(e) => setPeerUrl(e.target.value)}
            className={FIELD}
          >
            <option value="">Choose a peer…</option>
            {options.map((url) => (
              <option key={url} value={url}>
                {url}
              </option>
            ))}
          </select>
          <p className={HINT}>
            {options.length === 0
              ? "No peers followed yet — follow one above first."
              : "Peers this node follows."}
          </p>
        </div>

        <div>
          <label className={LABEL} htmlFor="bundle-hash">
            Bundle hash
          </label>
          <input
            id="bundle-hash"
            value={bundleHash}
            onChange={(e) => setBundleHash(e.target.value)}
            placeholder="sha256:…"
            className={`${FIELD} font-mono`}
          />
        </div>

        <label className={CHOICE_ROW}>
          <input
            type="checkbox"
            className={CHECKBOX}
            checked={allowRebuild}
            onChange={(e) => setAllowRebuild(e.target.checked)}
          />
          <span>
            Rebuild from the manifest if the peer cannot serve the bytes
          </span>
        </label>

        <Button
          type="submit"
          size="sm"
          disabled={
            !hasWrite || !peerUrl || !bundleHash.trim() || fetchIt.isPending
          }
          title={hasWrite ? undefined : "Fetching needs write access"}
        >
          {fetchIt.isPending ? "Fetching…" : "Fetch"}
        </Button>
      </form>

      {fetchIt.data && (
        // The `action` field IS the result — three outcomes that look identical
        // as a status code and mean different things to a reader.
        <p className={cn(PANEL_INSET, "mt-3 text-sm")} role="status">
          {packageFetchSentence(fetchIt.data)}
        </p>
      )}
      {fetchIt.isError && (
        <p className={cn(CAPTION, "mt-3 text-destructive")} role="alert">
          {(fetchIt.error as Error).message}
        </p>
      )}
    </section>
  );
}
