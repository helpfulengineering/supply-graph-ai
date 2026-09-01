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

## Moving or erasing data

Two more modes, available from the CLI and the API. They are not in the panel:
one copies potentially a great deal of data, and the other destroys some, and
neither belongs behind a button you can press by accident.

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

Works between any two providers. Local to Azure, S3 to Google Cloud, whichever
pair.

It does **not** erase the source. If you want the old backend emptied, migrate
first, confirm the new one is serving, then wipe separately.

### Move and erase — the destructive one

```bash
# See what would go. Nothing is switched and nothing is deleted.
ohm storage config set --provider local --bucket ~/ohm-data \
  --mode abandon_and_wipe --wipe-confirm /old/path --dry-run

# Then for real.
ohm storage config set --provider local --bucket ~/ohm-data \
  --mode abandon_and_wipe --wipe-confirm /old/path
```

You have to type the name of the bucket being erased, and it refuses if it does
not match — a checkbox is something you tick without reading, and a name is
something you have to go and look up. A mismatch deletes nothing **and switches
nothing**.

Erasing happens **after** the switch succeeds, never before.

### Reading the current configuration

```bash
ohm storage config show
```

## Where the configuration lives

In an encrypted file beside the node's data, not in the object store it
configures — credentials for a new provider written into the old one would be
orphaned the moment the switch took effect.

If you installed with the installer, that file is already on a mounted volume,
so your configuration survives upgrading the container.

Credentials are encrypted with the node's own encryption secret. A node that
was never given one refuses to store them at all, rather than pretending that
encrypting with a published default key protects anything.
