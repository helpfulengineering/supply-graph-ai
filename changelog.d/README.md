# Changelog fragments

Don't edit `CHANGELOG.md`'s `[Unreleased]` section directly — `make ready`
refuses it (`scripts/render_changelog.py --check`). Every PR that hand-edited
those lines conflicted with the next one that did, at the same lines, and
"strip the hunk, land one consolidated PR at the end" by hand got forgotten
often enough that it kept happening anyway. This is that fix, automated.

## Adding an entry

Add a file here instead:

```
changelog.d/<issue-or-pr-number>.<category>.md
```

`category` is one of Keep a Changelog's own sections: `added`, `changed`,
`deprecated`, `removed`, `fixed`, `security`. The file's content is exactly
the bullet body — no leading `- `, that gets added when it's folded in. It
can span multiple lines, same as any existing CHANGELOG.md entry.

Two PRs adding two different files never touch the same line, so they never
conflict — this is the entire point. If a filename collides with something
already in flight, add a short slug: `547.added.wipe-cli.md`.

Example, `changelog.d/547.added.md`:

```markdown
Standalone, guarded `ohm storage wipe` (#547), the replacement for the
combined switch-and-wipe mode retired in #543. Refuses to erase a backend
that is pending a restart, the saved configuration, or what a running API's
marker says it is live on.
```

## Folding fragments in

Not something a feature PR does. It's a deliberate, standalone step —
typically right before cutting a release (see `docs/RELEASE.md`) — because if
every PR consolidated on its own, two of them would go right back to editing
the same lines of `CHANGELOG.md` and conflicting on merge.

```bash
python scripts/render_changelog.py --consolidate
```

Reads every fragment, groups it under the right `### Category` heading in
`[Unreleased]` (creating the heading if it's not there yet, in Keep a
Changelog's order), deletes the fragment files, and re-records the section's
hash. Commit the result.

## Why a hash, not a diff

`make ready`'s check compares the current `[Unreleased]` section's SHA-256
against `.unreleased.sha256`, not a git diff against a base branch — a diff
needs history a shallow CI checkout may not have; a hash just needs the file
in front of it, the same shape as `bump_version.py --check`. If you edit
`[Unreleased]` by hand for a real reason (cutting a release's dated section,
say), re-baseline afterward:

```bash
python scripts/render_changelog.py --refreeze
```
