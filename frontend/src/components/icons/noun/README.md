# Licensed icons

Icons from The Noun Project, used under a purchased royalty-free licence held
by TheTechMargin. Attribution is not required under that licence; this note
records provenance so a future contributor does not have to guess where the
files came from or whether they may be redistributed with the source.

Four sets are drawn on:

| Set | Iconset id | Used for |
|---|---|---|
| Makerspace tools | 63541 | hand tools, saws, welding, grinding |
| Workshop | 268291 | machines, benches, safety, measuring |
| Additive manufacturing 2 | 244512 | 3D printing, filament, laser melting |
| RPA mixed | 249191 | the navigation and system glyphs |
| Future technology | 295984 | the sharing surface |

Only icons actually in use are checked in — the rest of each purchased set is
not vendored. To add one, drop the SVG here and regenerate `../index.tsx`.

## How they are used

`../index.tsx` wraps each SVG as a component with `fill="currentColor"`, so a
glyph takes its colour from the token layer like everything else. Attributes
are the React DOM spellings (`fillRule`, not `fill-rule`) — React warns on the
SVG ones and drops them, which silently changes how a path fills.

- Process glyphs are wired in `../processIcons.tsx`, keyed by taxonomy id. A
  unit test fails if any process in `src/config/taxonomy/processes.yaml` has no
  glyph.
- Navigation glyphs are wired in `components/layout/nav.ts`. These render at
  20px, which is the constraint that matters: the future-technology
  illustrations carry 200–3000 units of path data drawn for 100pt and collapse
  at that size. They belong at 40px+ (`components/ui/illustrations.tsx`). The
  line-art sets hold.
- `/icons` renders every glyph and every process mapping, for picking one.

Do not import a raw SVG at a call site, and do not add a `fill` to the paths.
