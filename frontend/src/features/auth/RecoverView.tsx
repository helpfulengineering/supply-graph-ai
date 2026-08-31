"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { KeyRound } from "lucide-react";
import { PageHero } from "../../components/layout/PageHero";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { EmptyState } from "../../components/ui/EmptyState";
import { useToast } from "../../components/ui/Toast";
import { FIELD_MONO, LABEL } from "../../components/ui/field";
import { PANEL } from "../../components/ui/surface";
import { SECTION_TITLE } from "../../components/ui/typography";
import { useAuth } from "../../context/AuthContext";
import {
  fetchSecurityPolicy,
  redeemRecoveryCode,
  type RegistrationResponse,
} from "../../api/ohm/identity";
import { TokenOnce } from "./TokenOnce";

/**
 * The way back in.
 *
 * Registration collects no email, no password and no second factor, so without
 * this a lost token is a permanently unreachable identity — and every private
 * record it made goes with it, unreachable by everyone including the operator.
 *
 * Redeeming revokes the account's other keys and spends the code, which is what
 * both cases it serves want: a token that was lost, and a token that leaked.
 */
export function RecoverView() {
  const { setToken } = useAuth();
  const { showSuccess, showError } = useToast();
  const [code, setCode] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [recovered, setRecovered] = useState<RegistrationResponse | null>(null);

  const policy = useQuery({
    queryKey: ["identity", "security-policy"],
    queryFn: fetchSecurityPolicy,
    staleTime: 5 * 60_000,
    retry: false,
  });

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const value = code.trim();
    if (!value) return;
    setSubmitting(true);
    try {
      const result = await redeemRecoveryCode(value);
      setRecovered(result);
      setCode("");
      if (result.key.token) await setToken(result.key.token, "minted");
      showSuccess("Account recovered", {
        description: `Signed in as ${result.display_name}.`,
      });
    } catch (err) {
      showError(err);
    } finally {
      setSubmitting(false);
    }
  }

  if (policy.isPending) {
    return (
      <div className="flex justify-center py-16">
        <LoadingSpinner />
      </div>
    );
  }

  if (policy.data && !policy.data.open_registration) {
    return (
      <>
        <PageHero title="Recover your account" />
        <EmptyState
          icon={KeyRound}
          heading="This node does not accept self-service recovery"
          body={`Its security posture is "${policy.data.mode}". Ask an operator to reissue a key for you.`}
        />
      </>
    );
  }

  return (
    <>
      <PageHero title="Recover your account" />

      {recovered ? (
        <div className="space-y-4">
          <TokenOnce
            token={recovered.key.token ?? ""}
            description="Your previous keys have been revoked. This is their replacement."
          />
          {recovered.recovery_code && (
            <TokenOnce
              token={recovered.recovery_code}
              heading="Save your new recovery code"
              description="The code you just used is spent. This one replaces it — put it in a password manager, not in this browser."
            />
          )}
          <section className={PANEL}>
            <h2 className={SECTION_TITLE}>You are signed in</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Same account, same identity — everything you made is yours again.{" "}
              <Link href="/account" className="underline">
                Your records
              </Link>
            </p>
          </section>
        </div>
      ) : (
        <section className={PANEL}>
          <h2 className={SECTION_TITLE}>Use your recovery code</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            The code you saved when you registered. It gets you a new key on the
            same account and identity, and revokes any keys you still hold.
          </p>
          <form onSubmit={onSubmit} className="mt-4 space-y-3">
            <label className={LABEL}>
              Recovery code
              <input
                value={code}
                onChange={(e) => setCode(e.target.value)}
                autoComplete="off"
                spellCheck={false}
                required
                className={`${FIELD_MONO} mt-1 w-full`}
              />
            </label>
            <button
              type="submit"
              disabled={submitting || !code.trim()}
              className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-on-accent hover:bg-primary disabled:opacity-50"
            >
              {submitting ? "Checking…" : "Recover account"}
            </button>
          </form>
          <p className="mt-4 text-sm text-muted-foreground">
            Lost the code as well?{" "}
            <Link href="/register" className="underline">
              Register again
            </Link>{" "}
            — a new identity, and the records made under the old one stay where
            they are.
          </p>
        </section>
      )}
    </>
  );
}
