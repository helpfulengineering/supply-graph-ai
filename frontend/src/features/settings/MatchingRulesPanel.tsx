"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  compareRules,
  exportRules,
  importRules,
  listRules,
  reloadRules,
  resetRules,
  validateRules,
} from "@/api/ohm/rules";
import type { RuleComparison, RuleValidation } from "@/api/ohm/rules";
import { validateFileTypes } from "@/api/ohm/file-types";
import {
  reloadProcessTaxonomy,
  validateProcessTaxonomy,
} from "@/api/ohm/taxonomy";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/button";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { FIELD, HINT, LABEL } from "@/components/ui/field";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import {
  PANEL,
  PANEL_BODY,
  PANEL_DANGER,
  PANEL_INSET,
} from "@/components/ui/surface";
import { BODY_MUTED, CAPTION } from "@/components/ui/typography";
import { useToast } from "@/components/ui/Toast";
import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";
import {
  groupRulesByDomain,
  guessRuleFormat,
  ruleSentence,
  summariseComparison,
} from "./rulesModel";

/**
 * The three files an operator edits on disk and cannot see from the app.
 *
 * Capability rules, the process taxonomy and the file-type taxonomy are all
 * YAML the server loads at startup, and all three have the same shape of
 * question: is my edit valid, and will you pick it up without a restart? One
 * panel, three sections, because three panels would be the same control
 * learned three times.
 */
export function MatchingRulesPanel() {
  const queryClient = useQueryClient();
  const { showSuccess } = useToast();
  const [draft, setDraft] = useState("");
  const [validation, setValidation] = useState<RuleValidation | null>(null);
  const [comparison, setComparison] = useState<RuleComparison | null>(null);

  const rules = useQuery({
    queryKey: ["match-rules"],
    queryFn: () => listRules(),
  });

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["match-rules"] });
    setValidation(null);
    setComparison(null);
  };

  const check = useMutation({
    mutationFn: async () => {
      const format = guessRuleFormat(draft);
      const result = await validateRules(draft, format);
      // Only compare a file that parses: a comparison of an unparseable file
      // is a second error message about the same problem.
      const diff = result.valid ? await compareRules(draft, format) : null;
      return { result, diff };
    },
    onSuccess: ({ result, diff }) => {
      setValidation(result);
      setComparison(diff);
    },
  });

  const applyImport = useMutation({
    mutationFn: () => importRules(draft, guessRuleFormat(draft)),
    onSuccess: (result) => {
      showSuccess(`Imported ${result.imported} rule(s)`);
      setDraft("");
      invalidate();
    },
  });

  const reload = useMutation({
    mutationFn: reloadRules,
    onSuccess: (result) => {
      showSuccess(`Reloaded ${result.imported} rule(s) from disk`);
      invalidate();
    },
  });

  const download = useMutation({
    mutationFn: () => exportRules("yaml"),
    onSuccess: (content) => {
      const url = URL.createObjectURL(
        new Blob([content], { type: "application/yaml" }),
      );
      const link = document.createElement("a");
      link.href = url;
      link.download = "capability-rules.yaml";
      link.click();
      URL.revokeObjectURL(url);
    },
  });

  const reset = useMutation({
    mutationFn: resetRules,
    onSuccess: () => {
      showSuccess("Rules reset to the built-in set");
      invalidate();
    },
  });

  const taxonomyCheck = useMutation({ mutationFn: validateProcessTaxonomy });
  const taxonomyReload = useMutation({
    mutationFn: reloadProcessTaxonomy,
    onSuccess: (total) => {
      showSuccess(`Reloaded ${total} process(es)`);
      void queryClient.invalidateQueries({ queryKey: ["taxonomy"] });
    },
  });
  const fileTypesCheck = useMutation({ mutationFn: validateFileTypes });

  const summary = comparison ? summariseComparison(comparison) : null;
  const groups = groupRulesByDomain(rules.data?.rules ?? []);

  return (
    <div className="space-y-6">
      <p className={BODY_MUTED}>
        Capability rules decide which facility capabilities satisfy which design
        requirements — for every match on this node, not just yours. The process
        and file-type taxonomies name the vocabulary those rules are written in.
      </p>

      <section aria-labelledby="rules-file" className={cn(PANEL, PANEL_BODY)}>
        <SectionHeading id="rules-file" role="card">
          Capability rules
        </SectionHeading>

        <div className="mt-3 flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={download.isPending}
            onClick={() => download.mutate()}
          >
            Export
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={reload.isPending}
            onClick={() => reload.mutate()}
          >
            {reload.isPending ? "Reloading…" : "Reload from disk"}
          </Button>
        </div>
        <p className={cn(CAPTION, "mt-2")}>
          Reload picks up an edit made to the YAML on the server without a
          restart.
        </p>

        <div className="mt-4">
          <label className={LABEL} htmlFor="rules-draft">
            Check a rules file
          </label>
          <textarea
            id="rules-draft"
            rows={6}
            value={draft}
            onChange={(e) => {
              setDraft(e.target.value);
              setValidation(null);
              setComparison(null);
            }}
            placeholder="Paste a YAML or JSON rules file"
            className={`${FIELD} font-mono`}
          />
          <p className={HINT}>
            Nothing is written until you press Import, and Import stays disabled
            until this file has been checked.
          </p>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            disabled={!draft.trim() || check.isPending}
            onClick={() => check.mutate()}
          >
            {check.isPending ? "Checking…" : "Check"}
          </Button>
          <Button
            size="sm"
            // Import is reachable only through a clean compare: the point of
            // the step is that nobody writes a file they have not seen the
            // effect of.
            disabled={!validation?.valid || !summary || applyImport.isPending}
            onClick={() => applyImport.mutate()}
          >
            {applyImport.isPending ? "Importing…" : "Import"}
          </Button>
          {summary && <span className={CAPTION}>{summary.label}</span>}
        </div>

        {check.isError && (
          <p className={cn(CAPTION, "mt-2 text-destructive")} role="alert">
            {(check.error as Error).message}
          </p>
        )}

        {validation && !validation.valid && (
          <ul className="mt-3 space-y-1" role="alert">
            {validation.errors.map((message) => (
              <li key={message} className={cn(CAPTION, "text-destructive")}>
                {message}
              </li>
            ))}
          </ul>
        )}

        {summary && (
          <div className={cn(PANEL_INSET, "mt-3 text-sm")}>
            <p className="text-foreground">
              Importing would make {summary.label} across{" "}
              {summary.domains.join(", ")}.
            </p>
          </div>
        )}
      </section>

      <section
        aria-labelledby="rules-current"
        className={cn(PANEL, PANEL_BODY)}
      >
        <SectionHeading id="rules-current" role="card">
          Loaded rules
        </SectionHeading>
        {rules.isPending ? (
          <LoadingState message="Loading rules…" />
        ) : rules.isError ? (
          <ErrorState
            title="Could not load rules"
            description={(rules.error as Error)?.message}
            onRetry={() => void rules.refetch()}
          />
        ) : groups.length === 0 ? (
          // Not "nobody has written rules": an empty set means the YAML never
          // loaded, and Reload is the thing to try.
          <EmptyState
            title="No rules loaded on this node"
            description="Matching is running on whatever the built-in defaults provide. If you expected rules here, the YAML may not have loaded."
            action={
              <Button
                variant="outline"
                size="sm"
                onClick={() => reload.mutate()}
              >
                Reload from disk
              </Button>
            }
          />
        ) : (
          <div className="mt-3 space-y-4">
            {groups.map((group) => (
              <div key={group.domain}>
                <p className="text-sm font-medium text-foreground">
                  {group.domain}{" "}
                  <span className={CAPTION}>({group.rules.length})</span>
                </p>
                <ul className="mt-1 space-y-1">
                  {group.rules.map((rule) => (
                    <li key={`${rule.domain}:${rule.id}`} className="text-sm">
                      <span className="text-foreground">
                        {ruleSentence(rule)}
                      </span>{" "}
                      <Badge>{rule.direction}</Badge>{" "}
                      <span className={CAPTION}>
                        confidence {rule.confidence}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}
      </section>

      <section
        aria-labelledby="rules-taxonomies"
        className={cn(PANEL, PANEL_BODY)}
      >
        <SectionHeading id="rules-taxonomies" role="card">
          Taxonomies
        </SectionHeading>
        <p className={cn(CAPTION, "mt-1")}>
          Reloading the process taxonomy validates first and keeps the current
          one if the new file does not parse, so a bad edit changes nothing.
        </p>

        <div className="mt-3 flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={taxonomyCheck.isPending}
            onClick={() => taxonomyCheck.mutate()}
          >
            Check processes
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={taxonomyReload.isPending}
            onClick={() => taxonomyReload.mutate()}
          >
            {taxonomyReload.isPending ? "Reloading…" : "Reload processes"}
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={fileTypesCheck.isPending}
            onClick={() => fileTypesCheck.mutate()}
          >
            Check file types
          </Button>
        </div>

        {taxonomyCheck.data && (
          <p className={cn(CAPTION, "mt-2")} role="status">
            processes.yaml: {taxonomyCheck.data.valid ? "valid" : "invalid"} —{" "}
            {taxonomyCheck.data.total_processes} process(es) from{" "}
            {taxonomyCheck.data.source}
            {taxonomyCheck.data.errors.length > 0 &&
              ` · ${taxonomyCheck.data.errors.join("; ")}`}
          </p>
        )}
        {fileTypesCheck.data && (
          <p className={cn(CAPTION, "mt-2")} role="status">
            file types: {fileTypesCheck.data.valid ? "valid" : "invalid"} —{" "}
            {fileTypesCheck.data.total_file_types} type(s) from{" "}
            {fileTypesCheck.data.source}
            {fileTypesCheck.data.errors.length > 0 &&
              ` · ${fileTypesCheck.data.errors.join("; ")}`}
          </p>
        )}
      </section>

      <ResetSection onReset={() => reset.mutate()} pending={reset.isPending} />
    </div>
  );
}

/** Reset behind a typed confirmation, because it discards every loaded rule. */
function ResetSection({
  onReset,
  pending,
}: {
  onReset: () => void;
  pending: boolean;
}) {
  const { isAdmin } = useAuth();
  const [typed, setTyped] = useState("");
  if (!isAdmin) return null;

  return (
    <section
      aria-labelledby="rules-reset"
      className={cn(PANEL_DANGER, PANEL_BODY)}
    >
      <SectionHeading id="rules-reset" role="card">
        Reset rules
      </SectionHeading>
      <p className={cn(CAPTION, "mt-1")}>
        Discards every loaded rule and returns to the built-in set. Every match
        on this node is affected. Type <code>reset</code> to confirm.
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <label className="sr-only" htmlFor="rules-reset-confirm">
          Type reset to confirm
        </label>
        <input
          id="rules-reset-confirm"
          value={typed}
          onChange={(e) => setTyped(e.target.value)}
          placeholder="reset"
          className={FIELD}
        />
        <Button
          variant="outline"
          size="sm"
          disabled={typed !== "reset" || pending}
          onClick={onReset}
        >
          {pending ? "Resetting…" : "Reset rules"}
        </Button>
      </div>
    </section>
  );
}
