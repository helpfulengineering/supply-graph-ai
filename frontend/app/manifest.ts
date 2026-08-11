import type { MetadataRoute } from "next";
import {
  BRAND_DESCRIPTION,
  BRAND_GROUND_DARK,
  BRAND_NAME,
  BRAND_SHORT,
} from "./brand";

/**
 * The web app manifest — what a browser reads when someone installs OHM to a
 * home screen or launches it as a standalone window.
 *
 * Without one, an installed instance shows the page title truncated to
 * whatever fits and a screenshot of the tab in place of the mark. The mark is
 * the same SVG the favicon serves; `purpose: "any"` because it already carries
 * its own ground and would look wrong re-cropped as a maskable icon.
 */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: BRAND_NAME,
    short_name: BRAND_SHORT,
    description: BRAND_DESCRIPTION,
    start_url: "/",
    display: "standalone",
    background_color: BRAND_GROUND_DARK,
    theme_color: BRAND_GROUND_DARK,
    icons: [
      {
        src: "/icon.svg",
        type: "image/svg+xml",
        sizes: "any",
        purpose: "any",
      },
    ],
  };
}
