# OHM Domain Glossary

This file defines the canonical domain language for the Open Hardware Manager project.
Do not add implementation details, specs, or plans — glossary terms only.

---

## Core Entities

**OKH Manifest** — A structured description of an open hardware design: what it is, how to build it, what files exist, and what standards it meets. The authoritative record for a hardware project.

**OKW Facility** — A structured description of a manufacturing or makerspace's capabilities: what processes it can perform, at what quality level, and where it is located.

**Component** — A distinct sub-assembly or purchased part within an OKH design. Trackable, replaceable, and salvageable as a unit. May optionally be backed by its own OKH manifest (enabling nested design structure). Examples: stepper motor, Raspberry Pi, printed housing.

**OKH Package** — A self-contained archive of an OKH manifest plus all externally-linked files (design files, manufacturing files, BOMs, etc.), organized into a standard directory structure.

---

## Processes

**Matching** — The process of finding OKW facilities capable of manufacturing the requirements described in an OKH manifest. Produces a ranked list of facility matches with explanations.

**Supply Tree** — The result of a matching process: a hierarchical structure describing how a design can be produced across one or more facilities, including sub-assembly dependencies.

**OKH Generation** — The automated extraction of an OKH manifest from an existing hardware repository (e.g., a GitHub repo), using LLM-assisted field extraction.

**Repair Triage** — The process of assessing a broken assembly to determine which components are salvageable in place, which can be harvested for use elsewhere, and which must be manufactured to restore function.

**Parts Harvesting** — Inventorying existing tools, machines, or assemblies as a source of spare components reusable for repairing or building other designs.

**Manual Federation** — The human-in-the-loop process of comparing and syncing OKH design collections between OHM instances, before automated federation support is available.

---

## Identity and Integrity

**Content Hash** — A SHA-256 digest of the canonical JSON representation of an OKH manifest, used as a stable, globally unique identity key for a design across systems. Truncated form serves as a human-readable short ID.

**Pinned Version** — A specific package version whose content hash has been explicitly locked by a user, signifying that the design files at that hash have been tested or certified. Enables reproducible builds and trusted distribution.

---

## System Modes (planned)

**Minimal Mode** — A system operating mode designed for crisis or low-data contexts. Runs coverage and dependency checks only; relaxed thresholds. Prioritizes producing a usable result quickly over completeness.

**Standard Mode** — The default operating mode. Adds quality and completeness checks on top of Minimal Mode behavior.

**Strict Mode** — Enforces all validations and thresholds. For certified or production-grade outputs.
