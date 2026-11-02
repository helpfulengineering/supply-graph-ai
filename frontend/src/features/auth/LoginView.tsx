"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { PageHero } from "../../components/layout/PageHero";
import { useToast } from "../../components/ui/Toast";
import { FIELD, LABEL } from "../../components/ui/field";
import { PANEL } from "../../components/ui/surface";
import { SECTION_TITLE } from "../../components/ui/typography";
import { useAuth } from "../../context/AuthContext";
import { loginPerson } from "../../api/ohm/identity";

/**
 * Username and password. The session arrives as a cookie the page cannot read.
 */
export function LoginView() {
  const { noteSession, signedIn, user } = useAuth();
  const { showSuccess, showError } = useToast();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [insecure, setInsecure] = useState(false);

  useEffect(() => {
    setInsecure(window.location.protocol === "http:");
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!username.trim() || !password) return;
    setSubmitting(true);
    try {
      await loginPerson(username.trim(), password);
      await noteSession();
      setDone(true);
      showSuccess("Signed in", {
        description: `Signed in as ${username.trim()}.`,
      });
    } catch (err) {
      showError(err);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <PageHero title="Sign in" />
      {done || (signedIn && user) ? (
        <section className={PANEL}>
          <h2 className={SECTION_TITLE}>You are signed in</h2>
          <p className="mt-3 text-sm text-muted-foreground">
            <Link href="/account" className="underline">
              Your records
            </Link>
          </p>
        </section>
      ) : (
        <section className={PANEL}>
          <h2 className={SECTION_TITLE}>Sign in to this node</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Use the username and password you chose when you registered.
          </p>
          {insecure && (
            <p className="mt-2 text-sm text-warning">
              This page is not using HTTPS. A password sent here can be read on
              the network.
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
                autoComplete="current-password"
                required
                className={`${FIELD} mt-1 w-full`}
              />
            </label>
            <button
              type="submit"
              disabled={submitting || !username.trim() || !password}
              className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-on-accent hover:bg-primary disabled:opacity-50"
            >
              {submitting ? "Signing in…" : "Sign in"}
            </button>
          </form>
          <p className="mt-4 text-sm text-muted-foreground">
            No account yet?{" "}
            <Link href="/register" className="underline">
              Register
            </Link>
          </p>
        </section>
      )}
    </>
  );
}
