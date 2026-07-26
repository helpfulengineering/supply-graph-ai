---
title: Share a design as a package
area: package
surface: web
---

# Share a design as a package

A design usually isn't one file. It's a description plus the things it points
at — CAD files, drawings, a bill of materials, assembly instructions — often
scattered across several places on the internet, any of which can move or
disappear.

A **package** is all of it, collected into one self-contained archive.

If you've used Docker, the analogy is close: a description gets built into a
fixed, complete artefact you can hand to someone.

## When you'd want one

**Handing a design to a workshop.** One archive beats a list of links, and it
still works when someone's link has rotted.

**Working offline.** The archive contains everything, so it doesn't matter
whether the original sources are reachable — or whether *you* are online. This is
the difference between a design being theoretically available and actually usable
in a crisis.

**Archiving.** Keeping a copy of what a design was at a moment in time, rather
than what its various hosts happen to serve today.

## Building one

Go to **Packages**, find the design, and build. OHM fetches the linked files and
assembles them into a standard layout — design files, manufacturing files,
instructions, and the manifest itself, each in a predictable place, so anyone
receiving one knows where to look without being told.

Then download it. You can also download several at once.

## What a package fixes in place

A package records exactly which files it contains. Two people with the same
package have the same thing — not "the same design, probably, depending on when
they downloaded it."

That matters whenever *which version* is a real question: when a design has been
tested, when a workshop is quoting against specific files, or when something has
to be reproducible later.

## What it can't do

A package can only contain what a design actually links to. If documentation
references a file that was never published, or points somewhere no longer
reachable, that gap is in the design and the package will reflect it rather than
conceal it.
