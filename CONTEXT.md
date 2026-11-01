# OHM Domain Glossary

This file defines the canonical domain language for the Open Hardware Manager project.
Do not add implementation details, specs, or plans — glossary terms only.

---

## Core Entities

**OKH Manifest** — A structured description of an open hardware design: what it is, how to build it, what files exist, and what standards it meets. The authoritative record for a hardware project.

**OKW Facility** — A structured description of a place's manufacturing capabilities: what processes it can perform, at what quality level, and where it is located. Ranges from a makerspace or factory down to a single member's home 3D printer; a member's equipment is a facility authored by that member, not an attribute of their account.

**Component** — A distinct sub-assembly or purchased part within an OKH design. Trackable, replaceable, and salvageable as a unit. May optionally be backed by its own OKH manifest (enabling nested design structure). Examples: stepper motor, Raspberry Pi, printed housing.

**OKH Package** — A self-contained archive of an OKH manifest plus all externally-linked files (design files, manufacturing files, BOMs, etc.), organized into a standard directory structure.

---

## Processes

**Matching** — The process of finding OKW facilities capable of manufacturing the requirements described in an OKH manifest. Produces a ranked list of facility matches with explanations.

**Supply Tree** — The result of a matching process: a hierarchical structure describing how a design can be produced across one or more facilities, including sub-assembly dependencies.

**OKH Generation** — The automated extraction of an OKH manifest from an existing hardware repository (e.g., a GitHub repo), using LLM-assisted field extraction.

**Repair Triage** — The process of assessing a broken assembly to determine which components are salvageable in place, which can be harvested for use elsewhere, and which must be manufactured to restore function.

**Parts Harvesting** — Inventorying existing tools, machines, or assemblies as a source of spare components reusable for repairing or building other designs.

**Follow** — One node choosing to accept and pull everything another node shares.

**Curated List** — A named, signed set of pinned versions of designs, published by a node or an organisation, e.g. "Distribute Aid: field-validated designs". An author's later edit does not change the list; the publisher must bump the entry. Being on a list never changes a design's visibility.
_Avoid_: calling a list entry a "release" — that word means an OHM software release.

**Subscribe** — Following a single curated list instead of a whole node: the subscriber pulls exactly the designs on that list, including later additions. The selective form of follow.

**Manual Federation** — The human-in-the-loop process of comparing and syncing OKH design collections between OHM instances, before automated federation support is available.

---

## Network

**Node** — A running OHM instance, operated by an organisation or individual, holding its own records and accounts. Example: the node Distribute Aid operates for its relief network.

**Edge Node** — A node that only syncs outbound: it publishes to and pulls from other nodes but does not accept inbound sync. The lightweight way for an individual to run their own node.

**Member** — An individual with an account registered on a node they do not operate. A member installs nothing; the node holds their identity. A member may later graduate to running their own edge node under the same identity.
_Avoid_: calling a member an "edge node" or "user node".

**Coordinator** — A member a node's operator has entrusted with running its membership: inviting people and seeing who has joined and what equipment they offer. Less than an operator: cannot change how the node is configured, and cannot see anyone's private records.

**Organisation** — An identity that members publish on behalf of, administered by one or more persons. A makerspace is one kind; a relief organisation such as Distribute Aid is another. Independent of nodes: an organisation may run its own node, or be one of several hosted on someone else's.
_Avoid_: "space" outside code (it reads as makerspace only).

**Affiliation** — An organisation's signed, revocable, expiring permission for a person to publish on its behalf. A person may hold several. Only an affiliated person may publish on behalf of an organisation; a lapsed affiliation stops new records naming the organisation but does not change records made while it was held. Distinct from being a member of a node.

---

## Identity and Integrity

**Content Hash** — A SHA-256 digest of the canonical JSON representation of an OKH manifest, used as a stable, globally unique identity key for a design across systems. Truncated form serves as a human-readable short ID.

**Visibility** — How far a record may travel from the node that holds it. One of: *private* (its creator only), *members* (any member of this node; never leaves the node), *followers* (anyone, and shared with nodes that follow this one), *public* (anyone, and eligible for broader listing).

**Pinned Version** — A specific package version whose content hash has been explicitly locked by a user, signifying that the design files at that hash have been tested or certified. Enables reproducible builds and trusted distribution.

---

## System Modes (planned)

**Minimal Mode** — A system operating mode designed for crisis or low-data contexts. Runs coverage and dependency checks only; relaxed thresholds. Prioritizes producing a usable result quickly over completeness.

**Standard Mode** — The default operating mode. Adds quality and completeness checks on top of Minimal Mode behavior.

**Strict Mode** — Enforces all validations and thresholds. For certified or production-grade outputs.
