---
title: Glossary
---

# Glossary

Plain-language definitions of terms used across this site. You shouldn't need any
of these to use OHM — they're here for when you meet one and want to check.

---

**Design**
:   A piece of open hardware someone has documented well enough that another
    person could build it. On this site, "design" always means the documentation
    and files, never a physical object.

**Facility** *(also: workshop, space)*
:   Somewhere things get made — a makerspace, a fab lab, a university workshop, a
    small manufacturer. In OHM a facility is a record describing what that place
    can produce and where it is.

**Component**
:   A distinct part or sub-assembly within a design, which can be tracked,
    replaced, or salvaged on its own. A stepper motor, a circuit board, a printed
    housing. A component can have a design of its own, which is how larger designs
    nest inside each other.

**Matching**
:   Working out which facilities can build a given design. Produces a ranked list
    with an explanation for each — what it satisfied, what it didn't, and why.

**Supply tree**
:   The plan that comes out of matching: how a design can actually be produced,
    across one facility or several, including which parts depend on which. When
    no single workshop can perform every process, the supply tree is what spans
    them.

**Process**
:   Something that has to be done to produce a design — 3D printing, laser
    cutting, machining, soldering, assembly. Designs require processes; facilities
    perform them. Matching is largely the business of lining those two up.

**Package**
:   A design plus all the files it points at, bundled into one self-contained
    archive. Useful when you need the whole thing in one piece — to hand to a
    workshop, to archive, or to work offline.

**Federation**
:   The arrangement whereby many independent OHM instances each hold their own
    records and choose which others to follow. There is no central instance. See
    [federation and sovereignty](../about/federation-and-sovereignty.md).

**Instance** *(also: node)*
:   One running copy of OHM, holding its own records. The one at
    openhardwaremanager.org is an instance; so is one you run yourself.

**Peer**
:   Another instance that yours has chosen to follow. Their records flow into your
    view; yours flow to them only as far as your visibility settings allow.

**Visibility**
:   The setting on each record that controls what leaves your instance, and how
    much. Not simply on or off — a facility can be discoverable while its address
    stays private.

**Provenance**
:   The record of where a piece of information came from and who asserted it.
    Matters in a federated network, where a record may have travelled through
    several instances before reaching you.

**Normalisation**
:   Translating inconsistent descriptions into one consistent form so they can be
    compared. Most of what OHM does internally. See
    [the problem](../about/the-problem.md).

**OKH** *(Open Know-How)*
:   The standard way OHM describes a design. See
    [OKH and OKW](okh-and-okw.md).

**OKW** *(Open Know-Where)*
:   The standard way OHM describes a facility. See
    [OKH and OKW](okh-and-okw.md).

**RFQ** *(request for quotation)*
:   The document you'd send a workshop to ask what it would take for them to build
    something. OHM can generate these, though this isn't yet available in the web
    app.
