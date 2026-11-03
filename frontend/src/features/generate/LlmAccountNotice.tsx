"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  fetchSecurityPolicy,
  registrationIsOpen,
} from "../../api/ohm/identity";
import { PANEL_DANGER } from "../../components/ui/surface";
import { cn } from "@/lib/utils";

/**
 * Shown when a node refuses anonymous LLM generation (#565).
 *
 * The API's 401 tells a developer to pass a Bearer token; a first-time visitor
 * needs to hear that an account is the answer, where to get one, and that they
 * can still generate without the model meanwhile (#561). Register opens on
 * this page, so the repository address they typed is still there afterwards.
 * It is offered only when this node accepts registrations, as `AuthBanner` does.
 */
export function LlmAccountNotice({
  onContinueWithoutLlm,
  onRegister,
}: {
  onContinueWithoutLlm: () => void;
  onRegister: () => void;
}) {
  const policy = useQuery({
    queryKey: ["identity", "security-policy"],
    queryFn: fetchSecurityPolicy,
    staleTime: 5 * 60_000,
    retry: false,
  });
  const canRegister = registrationIsOpen(policy.data);

  return (
    <div role="alert" className={cn(PANEL_DANGER, "space-y-3 text-sm")}>
      <p className="text-foreground">
        Generating with the language model needs an account on this node.{" "}
        {canRegister && (
          <>
            <button
              type="button"
              onClick={onRegister}
              className="font-medium underline"
            >
              Register
            </button>
            {" or "}
          </>
        )}
        <Link href="/settings/session" className="font-medium underline">
          Sign in
        </Link>
        , then generate again.
      </p>
      <button
        type="button"
        onClick={onContinueWithoutLlm}
        className="rounded-md border border-border px-3 py-1.5 font-medium hover:bg-muted"
      >
        Generate without the language model
      </button>
    </div>
  );
}
