---
title: Join a node
area: identity
surface: web
---

# Join a node

You can read OHM without an account. Browsing designs, searching facilities,
running a match — none of it needs a credential. An account is what lets you
**write**: add a design, list a facility, save a match.

On most nodes you can make one yourself.

## Register

Go to `/register`, enter a display name, and submit. The node creates an
account, mints you an identity, and issues your first API key — and signs you
in with it, so there is no key to copy back in.

Two things appear once and only once:

- **Your API key.** Save it. The node stores only a digest, so nobody can read
  it back to you — not an operator, not a support request.
- **A recovery code.** Save that too, somewhere different. It is the only way
  back if you lose the key.

Neither asks for an email address, because the node does not want one. There is
nothing to verify and nothing to leak.

### If the node will not let you

You will see *"This node does not accept registrations"* instead of a form.
That is the node's choice: open registration is on in the `peacetime` and
`crisis` postures and off in `shielded`. Ask whoever runs it for a key — see
[Get a write key](get-a-write-key.md).

## Your account

`/account` is yours. Settings is for operators; this page is for you.

It shows who you are — display name, account id, your DID — and what your key
can do. From here you can:

- **See your keys**, when each was last used, and when each expires.
- **Renew** one before it expires.
- **Revoke** one you no longer want, or **revoke every other key** if you think
  one has leaked.

Keys expire. That is deliberate: a key that lives forever is one that is still
valid years after the laptop it was typed into was sold. The lifetime depends
on the node's posture — 180 days in `peacetime`, 365 in `crisis`, 30 in
`shielded`.

## If you lose your key

Go to `/recover` and enter your recovery code. The node checks it and issues a
fresh key.

A recovery code works **once**. Using it invalidates it and gives you a new one
— save that too.

If you have lost both the key and the code, there is nothing to recover with.
An operator can create you a new account, but your old one is not reachable:
the node never had anything that could prove you were you except those two
secrets. Nodes in `shielded` posture do not offer recovery at all.

## Staying signed in

A session you got by registering **persists** — close the tab, come back
tomorrow, still signed in. A key you *pasted* into Settings does not: it lasts
for that tab only.

The difference is how the session began, not what it can do. Pasting an admin
key into a shared machine should not outlive the window; registering on your
own laptop should not make you re-enter a 43-character secret every morning.

## What an account does not do

It does not make your records public. New records are private, and stay that
way until you say otherwise. See
[Who can see your data](who-can-see-your-data.md).
