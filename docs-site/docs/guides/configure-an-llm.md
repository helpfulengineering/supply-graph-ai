---
title: Configure an LLM
area: llm
surface: selfhost
---

# Configure an LLM

OHM reads repositories and turns them into structured design records. Most of
that works without an LLM: it reads files, licences, versions and bills of
materials using direct extraction, pattern rules and language processing.

An LLM adds the part those cannot do — reading prose and saying *what the thing
is for*. It is **optional**, and OHM is designed to be honest about running
without one.

## Do you need one?

You do not need an LLM to use OHM. You will notice its absence in one specific
place.

Generating a design from a URL with no LLM configured produces a manifest with
most fields filled in, but leaves **`function`** empty — the one- or two-sentence
description of what the hardware does. `function` is required by OKH, so the
review screen asks you to write it before you can download the design or send it
to matching.

On a real project — the OpenFlexure Microscope — heuristic-only generation
filled in the title, version, documentation language, licensor and licence
correctly, and left exactly that one field for a human. If you are importing a
handful of designs, typing a sentence each time is fine. If you are importing
hundreds, an LLM is worth configuring.

## Three ways to configure one

### 1. In the web app (recommended)

**Settings → LLM providers.** Add a key for your provider; it is encrypted before
storage and never returned to the browser. Keys can be rotated or deleted from
the same screen, and take effect without restarting anything.

This is the option to use if you want your key stored with the node rather than
sitting in a shell profile or a deployment config.

### 2. An environment variable

Set the key your provider expects:

```bash
ANTHROPIC_API_KEY=sk-...        # or
OPENAI_API_KEY=sk-...           # or
AZURE_OPENAI_API_KEY=...
```

Convenient for local development, where a `.env` file is already how everything
else is configured.

### 3. A local model with ollama

No API key, no cloud provider, no per-request cost:

```bash
LLM_DEFAULT_PROVIDER=local
OLLAMA_BASE_URL=http://localhost:11434   # optional; this is the default
```

Ollama is **opt-in only**. Naming it as the provider, or setting its base URL,
is what enables it — OHM never assumes a local model is present just because
ollama's client would default to `localhost`. Otherwise every node would believe
it had a local model, and every generation would fail against nothing.

### The command line uses the same configuration

`ohm llm` commands read exactly what generation reads — including credentials
stored through **Settings**, which they previously could not see. So a key added
in the web app works on the command line too, without being repeated in the
environment.

## When several are configured

A stored credential wins over an environment variable for the same provider, so
rotating a key in **Settings** takes effect even if an old one is still in the
environment.

To choose between *different* providers, name one:

```bash
LLM_DEFAULT_PROVIDER=openai
```

An explicit choice is used **on its own**. If you name `openai` and no OpenAI
credential is configured, generation runs without an LLM rather than quietly
falling back to a different provider — being silently billed for a provider you
did not choose is worse than getting no LLM.

Leave it unset and OHM picks whichever provider is configured. With more than
one, it uses a fixed preference order and **logs which it chose**, so the
decision is never invisible. Ollama is only ever considered here if you have set
its base URL, and it is tried last — a node with both a cloud key and a local
model keeps using the cloud one.

## Turning it off without deleting anything

```bash
LLM_ENABLED=false
```

This is a **kill switch, not an enable switch**. Configuring a provider is what
turns the LLM on; this turns it off regardless of what is stored — useful if
costs spike, or a provider is having an outage, and you want generation to keep
working in its degraded-but-functional form without destroying your credentials.

## Knowing whether it actually ran

Every generated design reports what happened. The quality report carries
`llm_used`, and when the answer is no, `llm_status` says why:

| Status | Meaning | What to do |
|---|---|---|
| `used` | the LLM contributed | — |
| `not_configured` | no provider is set up | add a credential |
| `disabled` | `LLM_ENABLED=false` | turn the kill switch off |
| `failed` | configured, but unreachable | check the key is valid and the provider is up |
| `skipped` | extraction was already confident enough | nothing; this is a success |
| `not_requested` | the request asked for no LLM | nothing |

A degraded run also says so in plain language on the review screen, so you are
never left wondering whether a thin manifest reflects a thin repository or a
missing provider.

`failed` and `not_configured` are deliberately distinct: one means your key is
wrong, the other means you have no key. Reporting them as the same thing would
send you to fix the wrong problem.

## Controlling who can spend your budget

If your node is reachable by people you do not know, an LLM turns generation into
a way to spend your money.

```bash
GENERATE_FROM_URL_REQUIRE_AUTH_FOR_LLM=true
```

With this set, a request that would genuinely invoke an LLM requires an API key.
Requests that would not — because no provider is configured, or because the
caller asked for heuristic-only generation with `no_llm=true` — are unaffected.

It is safe to enable **before** configuring a provider. While there is nothing to
spend, it changes nothing; the moment you add a credential, the spend path is
already protected. That ordering is deliberate: it means there is no step to
remember at the moment it would be easiest to forget.

## Running in production

A node running with `ENVIRONMENT=production` — or any environment name other than
`development` or `test` — requires two values before it will start:

```bash
LLM_ENCRYPTION_SALT=...
LLM_ENCRYPTION_PASSWORD=...
```

These encrypt stored provider credentials. They are required **whether or not you
use an LLM**, because credential storage is initialised when configuration
loads. A node without them refuses to start rather than silently falling back to
default encryption keys.

Generate them as long random strings, keep them out of version control, and do
not change them once credentials are stored — the stored keys are encrypted with
them and cannot be recovered otherwise.

## Cost and quality notes

- Generation sends repository documentation to your provider. Do not point a
  shared or public node at a provider account you would mind seeing traffic on.
- OHM prefers a chunked strategy for large repositories, so a big project costs
  more than a small one.
- The LLM layer is one of several. If earlier extraction is already confident, it
  may be skipped entirely, and the report will say `skipped`.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Every design needs `function` typed in | No LLM configured — check the quality report's `llm_status` |
| Key added in Settings but nothing changed | Check `LLM_ENABLED` is not `false`, and that `LLM_DEFAULT_PROVIDER` (if set) names the provider you added |
| `llm_status: failed` | Key rejected, or provider unreachable. For ollama, check the base URL and that the model is pulled |
| Generation returns 401 | `GENERATE_FROM_URL_REQUIRE_AUTH_FOR_LLM` is on and a provider is configured — authenticate, or pass `no_llm=true` |
| Node will not start in production | `LLM_ENCRYPTION_SALT` / `LLM_ENCRYPTION_PASSWORD` are missing |
