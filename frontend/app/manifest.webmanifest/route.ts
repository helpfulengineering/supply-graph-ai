import {
  BRAND_DESCRIPTION,
  BRAND_GROUND_DARK,
  BRAND_NAME,
  BRAND_SHORT,
} from "../brand";

/**
 * The web app manifest — what a browser reads when someone installs OHM to a
 * home screen or launches it as a standalone window.
 *
 * Without one, an installed instance shows the page title truncated to
 * whatever fits and a screenshot of the tab in place of the mark. The mark is
 * the same SVG the favicon serves; `purpose: "any"` because it already carries
 * its own ground and would look wrong re-cropped as a maskable icon.
 *
 * A route handler rather than `app/manifest.ts`, which is the obvious way to
 * write this and the reason it broke. That file convention emits its own
 * `<link rel="manifest">` with no `crossorigin`, and a manifest is fetched as
 * a CORS request — so behind Vercel's deployment protection, where the request
 * is redirected to `vercel.com/sso-api`, the browser blocks the response and
 * the deployment installs with no name and no icon. The layout emits the tag
 * itself with `crossOrigin="use-credentials"`; serving the JSON from a plain
 * route is what makes that possible. Same URL, same body.
 */
export function GET(): Response {
  return Response.json(
    {
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
    },
    { headers: { "content-type": "application/manifest+json" } },
  );
}
