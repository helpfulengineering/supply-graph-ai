"use client";

import { PageHero } from "../../components/layout/PageHero";
import { useSiteLayer } from "../../lib/site/useSiteLayer";
import { siteConfig } from "../../lib/site/config";

/**
 * Mission Control — the site layer's own surface: telemetry, visitor records,
 * whitelabel config.
 *
 * It is a SITE surface and must not appear to grant application powers. The
 * ten admin panels under /settings are gated by the backend's whoami and are
 * untouched by anything here.
 *
 * With the layer disabled this route 404s rather than rendering an explanation.
 * That is the point of "off is a first-class state": on the default deployment
 * the feature does not exist, so a page apologising for its absence would be
 * describing a misconfiguration that isn't one.
 */
export function MissionControl() {
  // The route is gated in the server component; this hook only supplies state.
  const { visitor, isOperator } = useSiteLayer();

  return (
    <div className="space-y-6">
      <PageHero
        title="Mission Control"
        crumb="telemetry · visitors · tiered access"
      />

      {!visitor && (
        <section className="rounded-xl border border-border bg-card p-4">
          <h2 className="text-sm font-semibold text-foreground">Not signed in</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Sign in at the gate to see your own record. Site sign-in is separate
            from your OHM API session and grants no application permissions.
          </p>
        </section>
      )}

      {visitor && (
        <section className="rounded-xl border border-border bg-card p-4">
          <h2 className="text-sm font-semibold text-foreground">My record</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {visitor.name} · {visitor.email}
          </p>
          <p className="mt-2 text-xs text-muted-foreground">
            You control this record: rename it, or erase it and every telemetry
            event attributed to it.
          </p>
        </section>
      )}

      <section className="rounded-xl border border-border bg-card p-4">
        <h2 className="text-sm font-semibold text-foreground">
          Operator{" "}
          <span className="ml-1 font-mono text-xs font-normal text-muted-foreground">
            {isOperator ? "verified" : "locked"}
          </span>
        </h2>
        <p className="mt-1 text-xs text-muted-foreground">
          Unmasked visitor and telemetry reads require the operator token,
          verified server-side and held in this tab only. Site-layer operator
          status is not OHM admin.
        </p>
      </section>

      <p className="font-mono text-xs text-muted-foreground">
        site layer connected · {new URL(siteConfig.url).host}
      </p>
    </div>
  );
}
