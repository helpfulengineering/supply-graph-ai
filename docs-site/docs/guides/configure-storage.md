---
title: Configure storage
area: storage
surface: selfhost
---

# Configure storage

A node keeps designs, facilities, packages and saved matches in object storage.
A fresh node starts on **local storage** — files on the machine it runs on —
which works, and is where the installer leaves you.

You can point it somewhere else at any time, from the running node. There is no
redeploy and no configuration file to edit.

This is an operator task: `/settings/storage` needs an admin key.

## What you are looking at

The panel shows two things that are easy to confuse, and separates them on
purpose:

- **The configuration** — the provider and bucket the node is set to use.
- **What answered** — what it is actually connected to, and how many designs
  and facilities are in there.

When storage misbehaves, the gap between those two is usually the answer.

It also shows which credentials are set, by **name only**. The node cannot show
you a credential value: it does not keep one it could read back. Credentials
here are write-only — you can replace one, never read it.

## Switching, in the panel

Pick a provider, give it a bucket or container, and fill in whatever
credentials it needs.

The node **checks the new backend before committing to anything**: it connects,
writes a probe object, reads it back, and confirms the directory structure —
then, and only then, switches. If any of that fails you are told which part
failed, and the node carries on serving from where it was. A wrong credential
costs you an error message, not your node.

**The panel leaves your existing data where it is.** It switches which backend
the node reads and writes; nothing is copied and nothing is deleted. The old
data stays on the old backend — invisible to the node, still there.

That is usually what you want. If you need the data to come with you, or the
old backend emptied, use the command line.

## Switching from the command line

`ohm storage config set` works from a shell on the node, but it is a separate
process from the running node. It saves the new configuration, and **the running node
does not pick it up until it is restarted** — until then it keeps serving from the
old storage. The panel does not have this limit: a switch made there takes effect
straight away.

So after a command-line switch, restart the node's API, then check `/settings/storage`
shows the new backend as what answered.

## Moving or erasing data

Moving data is available from the command line only. It is not in the panel: it
copies potentially a great deal of data, and does not belong behind a button you can
press by accident.

### Migrate — bring the data with you

```bash
ohm storage config set --provider azure_blob --bucket production \
  --mode migrate \
  --credential account_name=myaccount --credential account_key=secret
```

Copies everything to the new backend, verifies it, and only then switches. The
node keeps serving from the old storage for the whole copy, so a migration that
fails partway — or that you give up on — leaves a working node on the storage
you started with. Every object is read back from the destination and compared
before the switch happens: a copy that says it verified, did.

!!! note "Migrate is a command-line operation"
    `--mode migrate` works from the CLI. Requested over the API it is refused with a
    `400` that points at the CLI, and changes nothing: the background job it used to
    start could never find the storage it was meant to copy from.

!!! warning "Restart right after, and stop writers first if it must be complete"
    The running node keeps writing to the old storage until you restart it. Anything
    written between the start of the copy and the restart is not in the new storage,
    and something deleted in that window stays there. Restart straight after
    migrating; if the move has to be complete, stop whatever writes to the node
    before you start.

Works between any two providers. Local to Azure, S3 to Google Cloud, whichever
pair.

It does **not** erase the source. If you want the old backend emptied, migrate
first, **restart the node**, confirm the new one is serving, then wipe separately.

### Erasing the old storage

There is no single command that switches *and* erases: it has been retired, because
run from the command line it deleted the old storage while the running node was still
serving from it. `--mode abandon_and_wipe` now answers with an explanation and changes
nothing.

Until a guarded wipe exists, erasing is a manual step, taken after you are sure the
node no longer needs the old storage:

1. Switch (in the panel, or from the command line followed by a restart).
2. Confirm `/settings/storage` shows the new backend as what answered, and that your
   designs and facilities are there.
3. Delete the old data yourself.

### Reading the current configuration

```bash
ohm storage config show
```

## Background jobs

A node deployed with Docker Compose or on Azure also runs a **worker** for background
jobs such as importing a design from a URL. Those jobs do not read or write your
object storage, so switching storage does not affect them and there is nothing to
change on the worker.

## Where the configuration lives

In an encrypted file beside the node's data, not in the object store it
configures — credentials for a new provider written into the old one would be
orphaned the moment the switch took effect.

If you installed with the installer, that file is already on a mounted volume,
so your configuration survives upgrading the container.

Credentials are encrypted with the node's own encryption secret. A node that
was never given one refuses to store them at all, rather than pretending that
encrypting with a published default key protects anything.
