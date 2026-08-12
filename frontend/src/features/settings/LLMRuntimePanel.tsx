"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchLLMHealth, fetchLLMProviders } from "../../api/ohm/llm";
import { Badge } from "../../components/ui/Badge";
import { PANEL, PANEL_INSET } from "../../components/ui/surface";
import {
  BODY_MUTED,
  CAPTION,
  SECTION_TITLE,
} from "../../components/ui/typography";
import { cn } from "@/lib/utils";

/** Health string → badge hue. Unknown states stay neutral rather than alarming. */
function healthTone(status: string): "green" | "yellow" | "red" | "default" {
  if (status === "healthy") return "green";
  if (status === "degraded") return "yellow";
  if (status === "unavailable") return "red";
  return "default";
}

/**
 * Whether generation will work right now.
 *
 * The credentials form below can set a key and test it; neither answers the
 * question a caller has when /okh/generate quietly falls back to heuristic
 * extraction, which is what happens on a node with no provider configured.
 *
 * An unconfigured LLM service is a normal deployment, not a fault, so a failing
 * health call degrades to a neutral line rather than a red alert — and both
 * queries are pinned the way the federation panel pins its status, so a node
 * without the service does not print an error on every navigation.
 */
export function LLMRuntimePanel() {
  const health = useQuery({
    queryKey: ["llm", "health"],
    queryFn: fetchLLMHealth,
    retry: false,
    retryOnMount: false,
    staleTime: Infinity,
  });

  const providers = useQuery({
    queryKey: ["llm", "providers"],
    queryFn: fetchLLMProviders,
    retry: false,
    retryOnMount: false,
    staleTime: Infinity,
  });

  const live = providers.data?.providers ?? [];
  const unavailable = health.isError || providers.isError;

  return (
    <section aria-labelledby="llm-runtime-heading" className={PANEL}>
      <h2 id="llm-runtime-heading" className={SECTION_TITLE}>
        Runtime
      </h2>

      {unavailable ? (
        <p className={cn(BODY_MUTED, "mt-3")}>
          Provider status is unavailable on this node.
        </p>
      ) : health.isPending ? (
        <p className={cn(BODY_MUTED, "mt-3")}>Checking…</p>
      ) : (
        <>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Badge variant={healthTone(health.data?.health_status ?? "")}>
              {health.data?.health_status ?? "unknown"}
            </Badge>
            {providers.data?.default_provider && (
              <span className={CAPTION}>
                default: {providers.data.default_provider}
              </span>
            )}
          </div>

          {live.length === 0 ? (
            <p className={cn(BODY_MUTED, "mt-3")}>
              No LLM provider is active — generating a design from a URL will
              fall back to heuristic extraction.
            </p>
          ) : (
            <ul className="mt-3 space-y-2">
              {live.map((provider) => (
                <li
                  key={provider.name}
                  className={cn(
                    PANEL_INSET,
                    "flex flex-wrap items-center gap-x-3 gap-y-1 text-sm",
                  )}
                >
                  <span className="font-medium text-foreground">
                    {provider.name}
                  </span>
                  <Badge variant={healthTone(provider.status)}>
                    {provider.status}
                  </Badge>
                  {provider.model && (
                    <span className={cn(CAPTION, "font-mono")}>
                      {provider.model}
                    </span>
                  )}
                  {provider.is_connected === false && (
                    <span className={CAPTION}>not connected</span>
                  )}
                  {provider.error && (
                    <span className={cn(CAPTION, "min-w-0 flex-1 truncate")}>
                      {provider.error}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  );
}
