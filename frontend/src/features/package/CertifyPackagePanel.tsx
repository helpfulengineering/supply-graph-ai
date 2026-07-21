import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { certifyRelease } from "../../api/ohm/identity";
import type { PinRecord } from "../../api/package";
import { useAuth } from "../../context/AuthContext";

interface Props {
  version: string;
  pin: { pin_record: PinRecord; bundle_hash: string } | null;
}

/** Certify a release after pin; manual hash fields when no pin yet. */
export function CertifyPackagePanel({ version, pin }: Props) {
  const { isAdmin, reportAuthFailure, user } = useAuth();
  const queryClient = useQueryClient();
  const [subjectDid, setSubjectDid] = useState(user?.subject_did ?? "");
  const [advBundle, setAdvBundle] = useState("");
  const [advManifest, setAdvManifest] = useState("");
  const [advVersion, setAdvVersion] = useState(version);

  const bundle_hash = pin?.bundle_hash || advBundle.trim();
  const certifyVersion = pin ? version : advVersion.trim() || version;

  const certify = useMutation({
    mutationFn: () =>
      certifyRelease({
        subject_did: subjectDid.trim(),
        bundle_hash,
        version: certifyVersion,
        manifest_content_hash:
          pin?.pin_record.manifest_content_hash || advManifest.trim() || null,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["identity", "attestations"] });
    },
    onError: reportAuthFailure,
  });

  if (!isAdmin) return null;

  const canSubmit = Boolean(subjectDid.trim() && bundle_hash);

  return (
    <section
      aria-labelledby="certify-heading"
      className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900"
    >
      <h2 id="certify-heading" className="text-lg font-semibold text-foreground">
        Certify release
      </h2>
      <p className="mt-1 text-sm text-muted-foreground">
        Issue a <code className="text-xs">certified</code> attestation binding a firm DID to
        this package&apos;s bundle hash.
      </p>

      {pin ? (
        <p className="mt-3 break-all font-mono text-xs text-slate-600 dark:text-slate-300">
          bundle {pin.bundle_hash}
        </p>
      ) : (
        <p className="mt-3 text-sm text-amber-800 dark:text-amber-200">
          Pin the package first, or enter hash fields below.
        </p>
      )}

      <form
        className="mt-4 space-y-3"
        onSubmit={(e) => {
          e.preventDefault();
          if (canSubmit) certify.mutate();
        }}
      >
        <label className="block text-sm font-medium">
          Subject DID (firm / space)
          <input
            value={subjectDid}
            onChange={(e) => setSubjectDid(e.target.value)}
            className="mt-1 w-full max-w-xl rounded-md border border-slate-300 px-3 py-2 font-mono text-sm dark:border-slate-600 dark:bg-slate-950"
            required
          />
        </label>

        {!pin && (
          <div className="space-y-3">
            <label className="block text-sm font-medium">
              Bundle hash
              <input
                value={advBundle}
                onChange={(e) => setAdvBundle(e.target.value)}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 font-mono text-sm dark:border-slate-600 dark:bg-slate-950"
                required
              />
            </label>
            <label className="block text-sm font-medium">
              Version
              <input
                value={advVersion}
                onChange={(e) => setAdvVersion(e.target.value)}
                className="mt-1 w-40 rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-950"
              />
            </label>
            <label className="block text-sm font-medium">
              Manifest content hash (optional)
              <input
                value={advManifest}
                onChange={(e) => setAdvManifest(e.target.value)}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 font-mono text-sm dark:border-slate-600 dark:bg-slate-950"
              />
            </label>
          </div>
        )}

        <button
          type="submit"
          disabled={certify.isPending || !canSubmit}
          className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
        >
          {certify.isPending ? "Certifying…" : "Certify"}
        </button>
        {certify.isError && (
          <p className="text-sm text-red-600" role="alert">
            {certify.error instanceof Error ? certify.error.message : "Certify failed"}
          </p>
        )}
        {certify.isSuccess && (
          <p className="text-sm text-green-700 dark:text-green-300" role="status">
            Certified as {certify.data.type} ({certify.data.attestation_id})
          </p>
        )}
      </form>
    </section>
  );
}
