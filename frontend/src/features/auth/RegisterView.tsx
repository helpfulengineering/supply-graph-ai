"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { UserPlus } from "lucide-react";
import { PageHero } from "../../components/layout/PageHero";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { EmptyState } from "../../components/ui/EmptyState";
import { useToast } from "../../components/ui/Toast";
import { FIELD, LABEL } from "../../components/ui/field";
import { PANEL } from "../../components/ui/surface";
import { SECTION_TITLE } from "../../components/ui/typography";
import { useAuth } from "../../context/AuthContext";
import { TokenOnce } from "./TokenOnce";
import {
  fetchSecurityPolicy,
  registerPerson,
  type RegistrationResponse,
} from "../../api/ohm/identity";

/**
 * Self-service registration.
 *
 * A node operator should not be the only way to become someone on a node —
 * that is what would make one node structurally special rather than merely
 * well-known. A visitor registers here and is signed in by the time the form
 * submits: the token goes straight into the session, so there is no second
 * paste step, and the copy shown afterwards is for keeping, not for using now.
 */
export function RegisterView() {
  const { setToken, user } = useAuth();
  const { showSuccess, showError } = useToast();
  const [displayName, setDisplayName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [registered, setRegistered] = useState<RegistrationResponse | null>(
    null,
  );

  const policy = useQuery({
    queryKey: ["identity", "security-policy"],
    queryFn: fetchSecurityPolicy,
    staleTime: 5 * 60_000,
    retry: false,
  });

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const name = displayName.trim();
    if (!name) return;
    setSubmitting(true);
    try {
      const result = await registerPerson(name);
      setRegistered(result);
      // Adopt the session immediately. The visitor asked to join, not to be
      // handed a credential and told to come back with it.
      if (result.key.token) await setToken(result.key.token);
      showSuccess("Registered", { description: `Signed in as ${name}.` });
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

  // A node that does not accept registrations shows no registration form —
  // not a form that fails on submit.
  if (policy.data && !policy.data.open_registration) {
    return (
      <>
        <PageHero title="Register" />
        <EmptyState
          icon={UserPlus}
          heading="This node does not accept registrations"
          body={`Its security posture is "${policy.data.mode}". Ask an operator to create an account, then connect the key they give you.`}
          action={
            <Link href="/settings/session" className="text-sm underline">
              Connect a key
            </Link>
          }
        />
      </>
    );
  }

  return (
    <>
      <PageHero title="Register" />

      {registered ? (
        <div className="space-y-4">
          <TokenOnce
            token={registered.key.token ?? ""}
            description="You are already signed in on this tab. Keep the token to sign in again on another device."
          />

          <section className={PANEL}>
            <h2 className={SECTION_TITLE}>You are signed in</h2>
            <dl className="mt-3 space-y-2 text-sm">
              <div>
                <dt className="text-muted-foreground">Name</dt>
                <dd className="text-foreground">{registered.display_name}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">DID</dt>
                <dd className="break-all font-mono text-xs text-foreground">
                  {registered.did}
                </dd>
              </div>
            </dl>
            <p className="mt-4 text-sm text-muted-foreground">
              Anything you create starts private — only you can see it until you
              share it.{" "}
              <Link href="/account" className="underline">
                Your records
              </Link>
            </p>
          </section>
        </div>
      ) : (
        <section className={PANEL}>
          <h2 className={SECTION_TITLE}>Create an identity on this node</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            You get a key pair and an API token. Nothing else is asked for, and
            no email is involved.
          </p>
          {user && (
            <p className="mt-2 text-sm text-muted-foreground">
              You are already signed in as {user.name}. Registering again
              replaces this tab&apos;s session.
            </p>
          )}
          <form onSubmit={onSubmit} className="mt-4 space-y-3">
            <label className={LABEL}>
              Display name
              <input
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="Ada Lovelace"
                autoComplete="name"
                required
                className={`${FIELD} mt-1 w-full`}
              />
            </label>
            <button
              type="submit"
              disabled={submitting || !displayName.trim()}
              className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-on-accent hover:bg-primary disabled:opacity-50"
            >
              {submitting ? "Registering…" : "Register"}
            </button>
          </form>
        </section>
      )}
    </>
  );
}
