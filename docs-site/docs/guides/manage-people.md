---
title: Manage people on a node
area: identity
surface: web
---

# Manage people on a node

**People** is where this node decides who may join, who is already here, and
who may act for an organisation. It is not Settings: Settings is storage,
language-model credentials, and identity machinery. Your own keys and sessions
stay under **Account**.

| Drawer | For |
|---|---|
| **People → Invites** | Mint and revoke registration links |
| **People → Members** | See who is on the node and their facilities |
| **People → Organisations** | Affiliate people so they can publish for an org — [Publish for an organisation](publish-for-an-organisation.md) |

An **admin** sees all three. A **coordinator** sees Invites and Members. A
member who administers an organisation sees Organisations. Everyone else uses
Account.

## Who may join

Self-service registration is a setting you store. It overrides the security
mode. Unset, `peacetime` and `crisis` are open and `shielded` is closed. You
can open registration on a shielded node, or close it on a peacetime one.

```bash
ohm identity registration --set invite
```

`open`, `invite`, or `closed`. This needs an admin key.

| Setting | What happens at `/register` |
|---|---|
| `open` | Anyone can create an account. No link required. |
| `invite` | Signup only with a valid invite link. |
| `closed` | Every signup is refused, including one that carries an invite. |

### Mint an invite

When the setting is `invite`, mint a link from **People → Invites**, or:

```bash
ohm identity invite mint --ttl-days 14
ohm identity invite mint --ttl-days 14 --use-limit 20
ohm identity invite list
ohm identity invite revoke INVITE_ID
```

Mint prints `/register?invite=...` once. Share that URL. The link works until
it expires, you revoke it, or it reaches the use limit you set. Multi-use is
the default until you set a limit.

The page a person opens names this node and who runs it
(`OHM_FEDERATION_NODE_NAME`, `OHM_NODE_OPERATOR`). What they see after that is
[Join a node](join-a-node.md).

Only an admin changes who may register. A coordinator mints and revokes
invites; they cannot flip `open` / `invite` / `closed`.

## Coordinator reach

A coordinator helps run membership without holding the admin key. Grant it
from **Settings → Grants** (Identity group), or:

```bash
ohm identity coordinate did:key:z...
```

The grant lasts **180 days in every** security mode. The command and the
Grants panel both show the expiry.

### What they get

**People → Invites** and **People → Members**.

Members lists each account's display name and username, and each member's
facilities: the name, the processes, and the visibility. The street address
and the rest of the facility record stay out — that is deliberate.

### What they do not get

A coordinator does not get storage, language-model credentials, the security
mode, or **who may register**. A coordinator **does not read a private
record**, and their list of designs is the same as any other member's.
Affiliating someone to an organisation stays with that organisation's admin —
see [Publish for an organisation](publish-for-an-organisation.md).

`members` visibility (signed-in accounts on this node) is only as private as
your registration setting. On an open node, treat it accordingly; invite or
closed registration is the usual pairing. Details:
[Who can see your data](who-can-see-your-data.md).

## Where this sits next to Settings

| Task | Where |
|---|---|
| Paste an admin key / session | Settings → Session (Access) |
| Grant coordinate | Settings → Grants (Identity) |
| Mint invites, see members | **People** |
| Storage, LLM, federation | Settings → Node |
| Your own keys and recovery | Account |

Installing the node itself is still [Run your own node](run-your-own-node.md).
This page is the membership work after it is up.
