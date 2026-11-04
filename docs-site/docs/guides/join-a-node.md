---
title: Join a node
area: identity
surface: web
---

# Join a node

You can read OHM without an account. Browsing designs, searching facilities,
running a match — none of it needs a credential. An account is what lets you
**write**: add a design, list a facility, save a match.

Whether you can make one yourself is a setting the operator stores: `open`,
`invite`, or `closed`. That choice overrides the security mode. Unset,
`peacetime` and `crisis` are open and `shielded` is closed. An operator can
open registration on a shielded node, or close it on a peacetime one.

## Register

### Open, invite, or closed

**Open.** Go to `/register`. No link is required. The same form also opens
where you are — on Generate, when saving, or when the language model asks for
an account.

**Invite.** The form appears when you open a link you were sent,
`/register?invite=...`. It names the node and who runs it. The link registers
you only while the setting is `invite`, and only until it expires, is revoked,
or runs out of uses. Opening `/register` with no link shows *"An invite is
required"*. A link does not register you on a node set to `closed`.

**Closed.** You see *"This node does not accept registrations"* instead of a
form, including when the address still carries an old invite. Ask whoever runs
the node for an account. A script still uses an API key they issue — see
[Get a write key](get-a-write-key.md).

### The form

Choose a username, a password and a display name. The node creates an account
and signs you in. The browser holds that session in a cookie. There is no
token to copy.

The form names this node and who runs it: `OHM_FEDERATION_NODE_NAME` (default
`OHM Node`) and `OHM_NODE_OPERATOR` (default `the operator of this node`). They
are shown whether or not federation is turned on.

One thing appears once: a **recovery code**. Copy it or download it, and
confirm you have saved it somewhere other than this browser, before
continuing. It is the way back in if you forget the password.

Nothing asks for an email address, because the node does not want one. There is
nothing to verify and nothing to leak.

Signing in later is `/login`, with the same username and password.

A script still uses an API key. `ohm identity register` prints one, and a key
you already have can be pasted under Settings. That pasted key stays on this
tab only. The website session does not.

## Your account

`/account` is yours. Settings is for operators; this page is for you.

It shows who you are — display name, account id, your DID — and what your key
can do. From here you can:

- **Create a key** for a script. Signup does not hand one out.
- **See your keys**, when each was created, and how long each has left.
- **Renew** one before it expires.
- **Revoke** one you no longer want, or **revoke every other key** if you think
  one has leaked.

Keys expire. That is deliberate: a key that lives forever is one that is still
valid years after the laptop it was typed into was sold. The lifetime depends
on the node's posture — 180 days in `peacetime`, 365 in `crisis`, 30 in
`shielded`.

## If you lose your key

Go to `/recover`, enter your recovery code, and choose a new password. The node
signs you in on this browser, revokes every key and session the account had,
and shows a replacement recovery code.

A recovery code works **once**. Using it invalidates it and gives you a new one
— save that too. The command-line recovery, `ohm identity recover --code`,
still prints an API token, for one release.

If you have lost both the key and the code, there is nothing to recover with.
An operator can create you a new account, but your old one is not reachable:
the node never had anything that could prove you were you except those two
secrets. Nodes in `shielded` posture do not offer recovery at all.

## Staying signed in

A session from the website lasts until you sign out, you are idle for 30 days,
or 90 days pass. Closing the tab does not sign you out.

A key you *pasted* into Settings lasts for that tab only. Pasting an admin key
into a shared machine should not outlive the window.

## What an account does not do

It does not make your records public. New records are private, and stay that
way until you say otherwise. See
[Who can see your data](who-can-see-your-data.md).
