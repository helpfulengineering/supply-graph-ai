"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createAsset } from "@/api/ohm/asset";
import { PageHero } from "@/components/layout/PageHero";
import { Button, buttonVariants } from "@/components/ui/button";
import { FIELD, HINT, LABEL } from "@/components/ui/field";
import { PANEL, PANEL_BODY } from "@/components/ui/surface";
import { CAPTION } from "@/components/ui/typography";
import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";
import { NEW_ASSET_CRUMB } from "./crumbs";
import {
  EMPTY_ASSET_FORM,
  assetFormErrors,
  isAssetFormValid,
  toCreateRequest,
} from "./assetFormModel";
import { useDesignTitles } from "./useDesignTitles";

/** Register a physical unit against a design. */
export function CreateAssetPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { hasWrite, reportAuthFailure } = useAuth();
  const designTitles = useDesignTitles();
  const [form, setForm] = useState(EMPTY_ASSET_FORM);
  const [touched, setTouched] = useState(false);

  const errors = assetFormErrors(form);

  const create = useMutation({
    mutationFn: () => createAsset(toCreateRequest(form)),
    onSuccess: (asset) => {
      void queryClient.invalidateQueries({ queryKey: ["asset-list"] });
      router.push(`/assets/${asset.id}`);
    },
    onError: reportAuthFailure,
  });

  return (
    <div className="mx-auto max-w-2xl px-4 py-6">
      <PageHero
        title="Register an asset"
        breadcrumb={[
          { label: "Assets", href: "/assets" },
          { label: "New asset" },
        ]}
        crumb={NEW_ASSET_CRUMB}
        description="Record a physical unit so its condition can be tracked and its parts found."
      />

      {!hasWrite ? (
        <div className={cn(PANEL, PANEL_BODY)}>
          <p className="text-sm text-foreground">
            Registering a unit needs write access.
          </p>
          <Link
            href="/settings/session"
            className={cn(
              buttonVariants({ variant: "outline", size: "sm" }),
              "no-underline",
              "mt-3",
            )}
          >
            Add an API key
          </Link>
        </div>
      ) : (
        <form
          className={cn(PANEL, PANEL_BODY, "space-y-4")}
          onSubmit={(e) => {
            e.preventDefault();
            setTouched(true);
            if (isAssetFormValid(form)) create.mutate();
          }}
        >
          <div>
            <label className={LABEL} htmlFor="asset-design">
              Design
            </label>
            <select
              id="asset-design"
              value={form.manifestId}
              onChange={(e) => setForm({ ...form, manifestId: e.target.value })}
              className={FIELD}
            >
              <option value="">Choose a design…</option>
              {[...designTitles].map(([id, title]) => (
                <option key={id} value={id}>
                  {title}
                </option>
              ))}
            </select>
            <p className={HINT}>What this unit was built from.</p>
            {touched && errors.manifestId && (
              <p className={cn(CAPTION, "mt-1 text-destructive")}>
                {errors.manifestId}
              </p>
            )}
          </div>

          <div>
            <label className={LABEL} htmlFor="asset-tag">
              Asset tag
            </label>
            <input
              id="asset-tag"
              value={form.assetTag}
              onChange={(e) => setForm({ ...form, assetTag: e.target.value })}
              placeholder="OHM-0042"
              className={FIELD}
            />
            <p className={HINT}>
              A serial number or location code — how people refer to it.
            </p>
            {touched && errors.assetTag && (
              <p className={cn(CAPTION, "mt-1 text-destructive")}>
                {errors.assetTag}
              </p>
            )}
          </div>

          <div>
            <label className={LABEL} htmlFor="asset-location">
              Location
            </label>
            <input
              id="asset-location"
              value={form.location}
              onChange={(e) => setForm({ ...form, location: e.target.value })}
              placeholder="Bay 3"
              className={FIELD}
            />
            <p className={HINT}>Optional. Where someone would go to find it.</p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Registering…" : "Register asset"}
            </Button>
            <Link
              href="/assets"
              className={cn(
                buttonVariants({ variant: "outline" }),
                "no-underline",
              )}
            >
              Cancel
            </Link>
            {create.isError && (
              <span className={cn(CAPTION, "text-destructive")} role="alert">
                {(create.error as Error).message}
              </span>
            )}
          </div>
        </form>
      )}
    </div>
  );
}
