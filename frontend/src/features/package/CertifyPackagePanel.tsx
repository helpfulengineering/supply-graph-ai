import { useState } from "react";
import { FIELD, FIELD_MONO, LABEL } from "../../components/ui/field";
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
      void queryClient.invalidateQueries({
        queryKey: ["identity", "attestations"],
      });
    },
    onError: reportAuthFailure,
  });

  if (!isAdmin) return null;

  const canSubmit = Boolean(subjectDid.trim() && bundle_hash);

  return (
    <section
      aria-labelledby="certify-heading"
      className="rounded-xl border border-border bg-card p-5"
    >
      <h2
        id="certify-heading"
        className="text-lg font-semibold text-foreground"
      >
        Certify release
      </h2>
      <p className="mt-1 text-sm text-muted-foreground">
        Issue a <code className="text-xs">certified</code> attestation binding a
        firm DID to this package&apos;s bundle hash.
      </p>

      {pin ? (
        <p className="mt-3 break-all font-mono text-xs text-muted-foreground">
          bundle {pin.bundle_hash}
        </p>
      ) : (
        <p className="mt-3 text-sm text-warning">
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
        <label className={LABEL}>
          Subject DID (firm / space)
          <input
            value={subjectDid}
            onChange={(e) => setSubjectDid(e.target.value)}
            className={`${FIELD_MONO} mt-1 w-full max-w-xl`}
            required
          />
        </label>

        {!pin && (
          <div className="space-y-3">
            <label className={LABEL}>
              Bundle hash
              <input
                value={advBundle}
                onChange={(e) => setAdvBundle(e.target.value)}
                className={`${FIELD_MONO} mt-1 w-full`}
                required
              />
            </label>
            <label className={LABEL}>
              Version
              <input
                value={advVersion}
                onChange={(e) => setAdvVersion(e.target.value)}
                className={`${FIELD} mt-1 w-40`}
              />
            </label>
            <label className={LABEL}>
              Manifest content hash (optional)
              <input
                value={advManifest}
                onChange={(e) => setAdvManifest(e.target.value)}
                className={`${FIELD_MONO} mt-1 w-full`}
              />
            </label>
          </div>
        )}

        <button
          type="submit"
          disabled={certify.isPending || !canSubmit}
          className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-on-accent disabled:opacity-50"
        >
          {certify.isPending ? "Certifying…" : "Certify"}
        </button>
        {certify.isError && (
          <p className="text-sm text-destructive" role="alert">
            {certify.error instanceof Error
              ? certify.error.message
              : "Certify failed"}
          </p>
        )}
        {certify.isSuccess && (
          <p className="text-sm text-success" role="status">
            Certified as {certify.data.type} ({certify.data.attestation_id})
          </p>
        )}
      </form>
    </section>
  );
}
