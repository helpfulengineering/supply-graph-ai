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
import { RecoveryKeep } from "./RecoveryKeep";
import {
  fetchSecurityPolicy,
  registerPerson,
  registrationIsOpen,
  type RegistrationResponse,
} from "../../api/ohm/identity";

/**
 * Self-service registration.
 *
 * A node operator should not be the only way to become someone on a node —
 * that is what would make one node structurally special rather than merely
 * well-known. A visitor chooses a username and a password and is signed in
 * by the cookie the response sets. The recovery code shown afterwards is the
 * one thing to keep.
 */
export function RegisterView() {
  const { noteSession, user } = useAuth();
  const { showSuccess, showError } = useToast();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
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
    if (!name || !username.trim() || !password) return;
    setSubmitting(true);
    try {
      const result = await registerPerson({
        username: username.trim(),
        password,
        display_name: name,
      });
      setRegistered(result);
      await noteSession();
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
  const registration = policy.data?.registration;
  if (policy.data && !registrationIsOpen(policy.data)) {
    const invite = registration === "invite";
    return (
      <>
        <PageHero title="Register" />
        <EmptyState
          icon={UserPlus}
          heading={
            invite
              ? "An invite is required"
              : "This node does not accept registrations"
          }
          body={
            invite
              ? "This node only accepts a registration that carries an invite."
              : registration === "closed"
                ? "This node is not accepting registrations. Ask an operator to create an account."
                : `Its security posture is "${policy.data.mode}". Ask an operator to create an account, then connect the key they give you.`
          }
          action={
            <div className="flex gap-3">
              <Link href="/login" className="text-sm underline">
                Sign in
              </Link>
              <Link href="/settings/session" className="text-sm underline">
                Connect a key
              </Link>
            </div>
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
          {registered.recovery_code && (
            <RecoveryKeep
              code={registered.recovery_code}
              heading="Save your recovery code"
              description="This is the way back in if you forget your password. Put it in a password manager — not in this browser."
            />
          )}

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
            Choose a username and a password. Nothing else is asked for, and no
            email is involved.
          </p>
          {user && (
            <p className="mt-2 text-sm text-muted-foreground">
              You are already signed in as {user.name}. Registering again
              replaces this tab&apos;s session.
            </p>
          )}
          <form onSubmit={onSubmit} className="mt-4 space-y-3">
            <label className={LABEL}>
              Username
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                required
                className={`${FIELD} mt-1 w-full`}
              />
            </label>
            <label className={LABEL}>
              Password
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="new-password"
                required
                className={`${FIELD} mt-1 w-full`}
              />
            </label>
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
              disabled={
                submitting ||
                !displayName.trim() ||
                !username.trim() ||
                !password
              }
              className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-on-accent hover:bg-primary disabled:opacity-50"
            >
              {submitting ? "Registering…" : "Register"}
            </button>
          </form>
          <p className="mt-4 text-sm text-muted-foreground">
            Already registered?{" "}
            <Link href="/login" className="underline">
              Sign in
            </Link>
          </p>
        </section>
      )}
    </>
  );
}
