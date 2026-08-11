---
title: Publish your workshop to Maps of Making
area: okw
surface: api
---

# Publish your workshop to Maps of Making

OHM reads [Maps of Making](https://mapsofmaking.org), and most of the workshops
you can see here came from it. This is the other direction: putting a workshop
you maintain in OHM onto that map, without describing it twice.

## Why this exists

Maps of Making works by reading. A space publishes a small file at a URL it
controls, the map fetches it every ten minutes, and the space stays the owner of
its own record. Nothing is copied into a registry you have to log into.

That design has a useful consequence: anything that can serve a file at a URL
can be a source. OHM can. So instead of maintaining your details here and again
over there, you enrich the record once and hand the map an address to read.

This is also the honest answer to a question the other guides raise. [List or
enrich your facility](list-or-enrich-your-facility.md) used to end by suggesting
that if your space was already on Maps of Making, you were better off improving
it at the source than duplicating effort in OHM. That was true when the two were
separate chores. It isn't now.

## What you need

A facility record in OHM with, at minimum, a name and **GPS coordinates**.
Without coordinates the map has nowhere to put a pin and will reject the
document. Processes are what make it findable by capability — see [list or
enrich your facility](list-or-enrich-your-facility.md).

## Get the URL

```bash
ohm okw spaceapi <facility-id> --url
```

That prints the address to register. Drop the `--url` to see the document
itself, which is worth doing once before you publish anything:

```bash
ohm okw spaceapi <facility-id>
```

The command tells you whether the URL is actually being served, and warns if the
record has no coordinates or no recognized processes — both of which produce a
disappointing result on the map.

## Make it public

**Nothing is served until you say so.** A new record is `private`, and the
publishing endpoint answers "not found" for anything that isn't `public`:

```bash
ohm okw visibility set <facility-id> public
```

`followers` is deliberately not enough here, even though it is enough for other
parts of OHM to share a record. Followers means peer instances that asked to
follow yours, where the receiving node still decides what to pass on. A public
map is broader than that, so publishing outward asks for the setting that says
so. See [who can see your data](who-can-see-your-data.md).

## Register it

1. Go to [mapsofmaking.org](https://mapsofmaking.org).
2. Open the **Add your space** drawer.
3. Paste the URL.

Maps of Making fetches it, validates it, and adds your pin. From then on it
re-reads that URL every ten minutes, so anything you improve in OHM later —
adding a process, correcting the hours — reaches the map on its own.

If your space is already on the map as a grey seeded pin, submitting the URL
upgrades it in place rather than creating a duplicate.

## What actually gets published

| Sent | Not sent |
|---|---|
| Name, coordinates, country code | Street address, postcode |
| Website, opening hours, description | Email, phone, any contact details |
| Processes, as activity tags | Equipment detail, materials, capacity |
| Whether the workshop is active, planned, or closed | Anything from a `private` record |

**The street address is deliberately withheld.** Publishing sends data into a
system we don't run, where it is cached and re-served, so the document carries
less than OHM's own API does rather than more. Coordinates are what put the pin
on the map; the street adds nothing the map needs. This matters because
`location` is currently a single disclosure group — a profile cannot yet keep
coordinates while withholding the street — so the decision is made here instead.

Two consequences worth knowing:

- **Coordinates are published.** They are precise, not fuzzed to a city. If your
  workshop is your home, that is the thing to weigh before setting `public`.
- **Your processes become tags.** OHM's process vocabulary is translated into the
  activity tags Maps of Making filters on, which is the point — it is the detail
  a directory usually can't express. Processes OHM doesn't recognize are left out
  of the tags rather than passed through as noise.

    A caveat worth setting expectations on: Maps of Making has its own activity
    vocabulary, and it currently has a concept for about eight of OHM's process
    types — 3D printing, CNC milling, laser cutting, vinyl cutting, PCB
    fabrication, welding, painting, sewing. The rest are still published and
    stored against your space, but won't become filter chips there until that
    vocabulary grows. Closing that gap is a conversation with the people who
    maintain it, which is the right place for it — see [standards and
    ecosystem](../reference/standards-and-ecosystem.md).

## Over HTTP

If you would rather not use the CLI, the endpoint is public and takes no key:

```
GET /v1/api/okw/{facility-id}/spaceapi
```

It returns the document for a `public` facility, and 404 for anything else —
including records that exist but haven't been published, so the response never
confirms an id you weren't already entitled to know about.
