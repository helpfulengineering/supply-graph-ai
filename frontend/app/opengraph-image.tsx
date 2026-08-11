/* eslint-disable react-refresh/only-export-components -- Next's
   image file convention: the route exports its size and content type
   alongside the component that draws it. */
import { ImageResponse } from "next/og";
import { renderMarkSvg } from "@/components/layout/mark";
import {
  BRAND_DESCRIPTION,
  BRAND_GROUND_DARK,
  BRAND_INK_DARK,
  BRAND_INK_MUTED_DARK,
  BRAND_NAME,
  BRAND_RAMP_DARK,
  BRAND_TAGLINE,
} from "./brand";

/**
 * The share card: what a link to this instance looks like in a chat client,
 * a feed, or a search result.
 *
 * Same mark, same Warm-dark ground, same iridescent rule that closes every
 * page hero — so a link previews as the app rather than as a grey rectangle
 * with a hostname in it. Composed rather than exported by hand, so it cannot
 * fall behind the mark it draws.
 *
 * The type is the one thing that is not on-brand: Geist ships from fontsource
 * as woff2 only, and satori reads ttf, otf, and woff. Rather than vendor a
 * second copy of the typeface to serve one image, the card uses the renderer's
 * default sans. If Geist ever ships an otf, pass it through `fonts` here.
 */
export const alt = `${BRAND_NAME} — ${BRAND_TAGLINE}`;
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpengraphImage() {
  const svg = renderMarkSvg({
    ramp: BRAND_RAMP_DARK,
    ground: BRAND_GROUND_DARK,
    groundRadius: 0,
    inset: 1,
    label: BRAND_NAME,
  });

  return new ImageResponse(
    (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          width: "100%",
          height: "100%",
          padding: "88px 96px",
          background: BRAND_GROUND_DARK,
          color: BRAND_INK_DARK,
        }}
      >
        {/* A plain <img> on purpose: satori is the renderer here, and
            next/image has no meaning inside an ImageResponse. */}
        <img
          src={`data:image/svg+xml;base64,${Buffer.from(svg).toString("base64")}`}
          alt=""
          width={132}
          height={132}
        />
        <div style={{ display: "flex", fontSize: 76, marginTop: 40 }}>
          {BRAND_NAME}
        </div>
        <div
          style={{
            display: "flex",
            width: 520,
            height: 6,
            marginTop: 28,
            borderRadius: 3,
            background: `linear-gradient(120deg, ${BRAND_RAMP_DARK.join(", ")})`,
          }}
        />
        <div
          style={{
            display: "flex",
            fontSize: 30,
            marginTop: 28,
            maxWidth: 900,
            color: BRAND_INK_MUTED_DARK,
          }}
        >
          {BRAND_DESCRIPTION}
        </div>
      </div>
    ),
    { ...size },
  );
}
