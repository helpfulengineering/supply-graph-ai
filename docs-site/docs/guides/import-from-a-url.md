---
title: Import a design from a repository URL
area: okh
surface: web
---

# Import a design from a repository URL

Point OHM at a public GitHub or GitLab repository and it will read what's there
into a structured design record — then hand it to you for review.

This is the fastest way to get an existing project into OHM, and the main way an
organisation backfills a back catalogue without redocumenting years of work.

## Doing it

**Designs** → **Generate from URL**, paste the repository address, and generate.

Only the URL is needed. Everything else is decided for you.

Most repositories come back in a few seconds. Large, mature projects — hundreds
of files, years of documentation — take longer. On nodes with async jobs enabled,
the web UI submits background jobs and shows real progress, so generation is no
longer capped by the two-minute proxy timeout. You can paste several URLs
separated by commas; each becomes its own job.

!!! info "On a node you run, this is already on"

    `docker compose up` starts a worker and enables jobs, so background import
    works out of the box — see [run your own node](run-your-own-node.md). It is
    what `JOBS_ENABLED=true` plus a running `ohm-worker` gets you.

    If you assembled a node by hand and background import is unavailable, those
    two things are what's missing. On Azure Container Apps, set
    `enable_jobs = true` when you
    [deploy a node](deploy-a-node-on-azure.md).

Operators and scripts can use the HTTP job API or the CLI:

```bash
ohm okh generate-jobs submit https://github.com/org/project --no-llm
ohm okh generate-jobs wait <job_id>
```

!!! note "Sync path still exists"

    `POST /api/okh/generate-from-url` still runs generation in the request. Prefer
    `POST /api/okh/generate-from-url/jobs` for anything that might take more than
    a minute, or when submitting multiple URLs.

!!! tip "Whether an LLM is involved changes what you get back"

    Without one, extraction fills in most fields but leaves **`function`** —
    what the hardware is *for* — for you to write. That is usually the only
    field the review screen still needs. The generated design reports whether an
    LLM contributed and, if not, why, so a thin result is never a mystery.

    See [Configure an LLM](configure-an-llm.md), including how to run a local
    model with ollama and no cloud key at all.

## Then review it — this part is not optional

What comes back is a **draft**, and treating it as finished is the main way to
get a bad record into the world.

Extraction reads what a repository actually says. Where documentation is
implicit, inconsistent, or absent, extraction is a best guess. The review step
exists because that guess needs a human.

The form is ordered by what actually needs your attention:

**Required** — title, version, function, documentation language, licensor, and
hardware licence. A design can't be downloaded until these are filled in. Any
that couldn't be extracted are marked.

**What drives matching** — manufacturing processes, materials, bill of
materials. These decide which workshops can build this, so they're worth more of
your time than anything else on the page. **Check the materials especially** —
they're the most error-prone part of extraction, and prose gets misread as
components more often than we'd like.

**Being found** — description, repository, keywords.

**Everything else** — collapsed, but present. Nothing extracted is hidden from
you.

Processes and keywords edit as removable tags. Nested structures like materials
and the bill of materials are shown as-is with a JSON editor, rather than a
half-built structured form that might quietly drop a field.

## Then download it

When the required fields are valid, download the design as **YAML** or **JSON**.

YAML is the better choice if a person will read or edit the file afterwards —
much of the OKH ecosystem uses it, and it's far easier to scan than JSON. JSON
is the better choice if software is going to consume it directly.

!!! note "Generated designs aren't saved to the catalogue"

    They're yours to download, not ours to keep. Without user accounts there's
    no owner and no provenance for a generated record, and adding unattributed
    records to a shared catalogue would degrade it for everyone. Saving arrives
    with accounts.

## What the generator did, and why

Every run also produces a **provenance record** — a second file beside the
manifest, not part of it:

```
manifest.okh.json          the design
manifest.provenance.json   how it was produced
```

It carries the stage timeline and, for each field, which layer produced it, by
what method, at what confidence, and from where:

```json
{
  "fields": {
    "title":       {"layer": "direct", "method": "metadata_name",
                    "confidence": 0.91, "source": "metadata.name"},
    "description": {"layer": "nlp", "method": "readme_summary",
                    "confidence": 0.62, "source": "README.md"}
  }
}
```

That is what makes review possible rather than guesswork. A field read straight
from repository metadata and a field inferred from prose are not equally
trustworthy, and the record tells you which you are looking at.

`source` is a short label — `metadata.name`, `README.md`, `no_version_found` —
naming where the extractor looked. It is not an excerpt, and does not point at
a line.

!!! note "Why it is a separate file"

    A manifest's content hash is taken over the whole file, and that hash is
    what pins a package and dedups the federation catalogue. Recording *how* a
    design was made inside the design itself would give the same design two
    different addresses. So the manifest stays exactly what it would have been,
    and the record travels beside it.

It is always produced — there is no flag to remember, because the run worth
explaining is invariably the one you did not think to ask about.

## When it doesn't work

**"That repository couldn't be read."** Private, misspelled, or moved. Only
public repositories work — private ones need credentials that belong to you,
which needs accounts.

**"The shared rate limit has been reached."** Everyone using the hosted instance
shares one quota for reading repositories, so heavy use by one person affects
others. Waiting is the fix. This goes away if you
[run your own node](run-your-own-node.md) with your own credentials.

**It read the repository but got little out of it.** That's a documentation
signal, not a failure. A repository that doesn't say what its parts are made of
gives extraction nothing to find. Fill in what you know and move on.

## A realistic expectation

Extraction on the hosted instance runs on rules rather than a language model.
It's fast, free, predictable, and works offline — and it's less clever than you
might expect. It finds what's stated plainly and misses what's implied.

That's the trade, and the guided review is how it's made to work. Assume you'll
correct something on every design, and it will rarely disappoint you.
