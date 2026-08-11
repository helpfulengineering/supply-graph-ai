/**
 * Regenerate the checked-in brand assets from their source modules.
 *
 *   npm run gen:brand
 *
 * Right now that is app/icon.svg, emitted from the shared mark geometry
 * (src/components/layout/mark.ts) coloured by the baked brand ramp
 * (app/brand.ts). The favicon is a build input rather than a build output on
 * purpose: it is checked in so it survives static export, CDN caching, and any
 * host that serves the app without running Next's image pipeline.
 *
 * Run under Node's type stripping (no ts-node, no extra dependency); the two
 * modules it imports are deliberately free of runtime imports of their own.
 */
import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { renderMarkSvg } from "../src/components/layout/mark.ts";
import { BRAND_GROUND_DARK, BRAND_NAME, BRAND_RAMP_DARK } from "../app/brand.ts";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const target = join(root, "app", "icon.svg");

writeFileSync(
  target,
  renderMarkSvg({
    ramp: BRAND_RAMP_DARK,
    ground: BRAND_GROUND_DARK,
    label: BRAND_NAME,
  }),
  "utf8",
);

console.log(`wrote ${target}`);
