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

## Switching

Pick a provider, give it a bucket or container, fill in whatever credentials it
needs, and choose what happens to the data already there.

The node **checks the new backend before committing to anything**: it connects,
writes a probe object, reads it back, and confirms the directory structure —
then, and only then, switches. If any of that fails you get told which part
failed, and the node carries on serving from where it was. A wrong credential
costs you an error message, not your node.

### What happens to the data already there

Three answers, and you have to pick one:

| Mode | What it does |
|---|---|
| **Leave it** | Switch, and leave the old storage untouched. The data stays where it is — invisible to the node, still there on the old backend. |
| **Migrate** | Copy everything to the new backend, verify it, and then switch. |
| **Move and erase** | Switch, then delete everything on the old backend. |

**Migrate** copies first and switches last, so the node keeps serving from the
old storage for the whole copy. If it fails partway, or you give up on it, you
still have a working node on the storage you started with. Every object is read
back from the destination and compared before the switch happens — a copy that
says it verified, did.

Migration works between any two providers. Local to Azure, S3 to Google Cloud,
whichever pair.

**Move and erase** is the destructive one. It asks you to type the name of the
bucket being erased, and refuses if it does not match — a checkbox is something
you tick without reading, and a name is something you have to look up. A
mismatch deletes nothing and switches nothing. Ask for a dry run first: it
reports what would go, and how much, without touching any of it.

Erasing happens **after** the switch succeeds, never before.

## Doing it from the command line

The same three modes, if you would rather not use a browser:

```bash
ohm storage config show

ohm storage config set --provider local --bucket ~/ohm-data

ohm storage config set --provider azure_blob --bucket production \
  --mode migrate \
  --credential account_name=myaccount --credential account_key=secret

ohm storage config set --provider local --bucket ~/ohm-data \
  --mode abandon_and_wipe --wipe-confirm /old/path --dry-run
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
