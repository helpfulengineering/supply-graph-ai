"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchCuratedList,
  listCuratedLists,
  publishCuratedList,
  replaceCuratedList,
  type CuratedList,
  type CuratedListWrite,
} from "../../api/ohm/federation";
import { ApiError } from "../../api/ohm/client";
import { PageHero } from "../../components/layout/PageHero";
import { Button } from "../../components/ui/button";
import { FIELD, FIELD_MONO, HINT, LABEL } from "../../components/ui/field";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { PANEL } from "../../components/ui/surface";
import { BODY_MUTED, SECTION_TITLE } from "../../components/ui/typography";
import { useAuth } from "../../context/AuthContext";
import { cn } from "@/lib/utils";

function pinLine(entry: CuratedList["entries"][number]): string {
  return entry.supersedes
    ? `${entry.content_hash} replaces ${entry.supersedes}`
    : entry.content_hash;
}

function pinsToText(list: CuratedList): string {
  return list.entries.map(pinLine).join("\n");
}

function entriesFromText(text: string): CuratedListWrite["entries"] {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [hash, replaced] = line.split(/\s+replaces\s+/);
      return replaced
        ? { content_hash: hash, supersedes: replaced.trim() }
        : { content_hash: hash };
    });
}

function PublishForm({
  initialName = "",
  initialPins = "",
  submitLabel,
  onSubmit,
  pending,
  showPublisher = true,
}: {
  initialName?: string;
  initialPins?: string;
  submitLabel: string;
  onSubmit: (body: CuratedListWrite) => void;
  pending: boolean;
  showPublisher?: boolean;
}) {
  const [name, setName] = useState(initialName);
  const [pins, setPins] = useState(initialPins);
  const [publisher, setPublisher] = useState("");

  return (
    <form
      className="space-y-3"
      onSubmit={(event) => {
        event.preventDefault();
        const body: CuratedListWrite = {
          name: name.trim(),
          entries: entriesFromText(pins),
        };
        if (showPublisher && publisher.trim()) body.publisher_did = publisher.trim();
        onSubmit(body);
      }}
    >
      <div className="space-y-1">
        <label className={LABEL} htmlFor="list-name">
          Name
        </label>
        <input
          id="list-name"
          className={FIELD}
          value={name}
          onChange={(event) => setName(event.target.value)}
          required
        />
      </div>
      <div className="space-y-1">
        <label className={LABEL} htmlFor="list-pins">
          Pins
        </label>
        <textarea
          id="list-pins"
          className={cn(FIELD_MONO, "min-h-24")}
          value={pins}
          onChange={(event) => setPins(event.target.value)}
          required
        />
        <p className={HINT}>
          One content hash per line. To bump a pin, write &quot;new-hash
          replaces old-hash&quot;.
        </p>
      </div>
      {showPublisher && (
        <div className="space-y-1">
          <label className={LABEL} htmlFor="list-publisher">
            Organisation
          </label>
          <input
            id="list-publisher"
            className={FIELD_MONO}
            value={publisher}
            onChange={(event) => setPublisher(event.target.value)}
            placeholder="Leave empty to publish as this node"
          />
        </div>
      )}
      <Button type="submit" disabled={pending}>
        {submitLabel}
      </Button>
    </form>
  );
}

function failure(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  if (err instanceof Error) return err.message;
  return "Could not publish the list";
}

export function CuratedListsPage() {
  const { signedIn, reportAuthFailure } = useAuth();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const lists = useQuery({
    queryKey: ["federation", "lists"],
    queryFn: listCuratedLists,
  });
  const publish = useMutation({
    mutationFn: publishCuratedList,
    onSuccess: () => {
      setError(null);
      void queryClient.invalidateQueries({ queryKey: ["federation", "lists"] });
    },
    onError: (err) => {
      reportAuthFailure(err);
      setError(failure(err));
    },
  });

  return (
    <div className="space-y-6">
      <PageHero
        title="Curated lists"
        crumb={[{ label: "named sets of pinned designs" }]}
      />
      {lists.isLoading && <LoadingSpinner message="Loading lists…" />}
      {lists.isError && (
        <p className="text-sm text-destructive" role="alert">
          {failure(lists.error)}
        </p>
      )}
      {lists.data && (
        <ul className="space-y-2">
          {lists.data.map((list) => (
            <li key={list.list_id}>
              <Link
                href={`/lists/${list.list_id}`}
                className="font-medium text-primary-ink underline-offset-2 hover:underline"
              >
                {list.name}
              </Link>
              <span className={cn(BODY_MUTED, "ml-2")}>
                sequence {list.sequence}
              </span>
            </li>
          ))}
          {lists.data.length === 0 && (
            <li className={BODY_MUTED}>No lists published yet.</li>
          )}
        </ul>
      )}
      {signedIn && (
        <section aria-labelledby="publish-list-heading" className={PANEL}>
          <h2 id="publish-list-heading" className={SECTION_TITLE}>
            Publish a list
          </h2>
          {error && (
            <p className="mb-3 text-sm text-destructive" role="alert">
              {error}
            </p>
          )}
          <PublishForm
            submitLabel="Publish"
            pending={publish.isPending}
            onSubmit={(body) => publish.mutate(body)}
          />
        </section>
      )}
    </div>
  );
}

export function CuratedListPage({ listId }: { listId: string }) {
  const { signedIn, reportAuthFailure } = useAuth();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const list = useQuery({
    queryKey: ["federation", "lists", listId],
    queryFn: () => fetchCuratedList(listId),
  });
  const replace = useMutation({
    mutationFn: (body: CuratedListWrite) => replaceCuratedList(listId, body),
    onSuccess: () => {
      setError(null);
      void queryClient.invalidateQueries({
        queryKey: ["federation", "lists", listId],
      });
    },
    onError: (err) => {
      reportAuthFailure(err);
      setError(failure(err));
    },
  });

  return (
    <div className="space-y-6">
      <PageHero
        title={list.data?.name ?? "Curated list"}
        breadcrumb={[
          { label: "Lists", href: "/lists" },
          { label: list.data?.name ?? listId },
        ]}
      />
      {list.isLoading && <LoadingSpinner message="Loading list…" />}
      {list.isError && (
        <p className="text-sm text-destructive" role="alert">
          {failure(list.error)}
        </p>
      )}
      {list.data && (
        <section className={PANEL}>
          <p className={BODY_MUTED}>
            Sequence {list.data.sequence}. Signed by {list.data.publisher_did}.
          </p>
          <ul className="mt-3 space-y-1 font-mono text-sm">
            {list.data.entries.map((entry) => (
              <li key={entry.content_hash}>
                {pinLine(entry)}
              </li>
            ))}
          </ul>
        </section>
      )}
      {signedIn && list.data && (
        <section aria-labelledby="edit-list-heading" className={PANEL}>
          <h2 id="edit-list-heading" className={SECTION_TITLE}>
            Publish the next version
          </h2>
          {error && (
            <p className="mb-3 text-sm text-destructive" role="alert">
              {error}
            </p>
          )}
          <PublishForm
            key={`${list.data.sequence}:${pinsToText(list.data)}`}
            initialName={list.data.name}
            initialPins={pinsToText(list.data)}
            submitLabel="Publish this version"
            showPublisher={false}
            pending={replace.isPending}
            onSubmit={(body) => replace.mutate(body)}
          />
        </section>
      )}
    </div>
  );
}
