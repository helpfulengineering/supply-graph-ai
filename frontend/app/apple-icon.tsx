/* eslint-disable react-refresh/only-export-components -- Next's
   image file convention: the route exports its size and content type
   alongside the component that draws it. */
import { ImageResponse } from "next/og";
import { renderMarkSvg } from "@/components/layout/mark";
import { BRAND_GROUND_DARK, BRAND_NAME, BRAND_RAMP_DARK } from "./brand";

/**
 * The home-screen icon, rasterized from the same mark as the favicon.
 *
 * iOS ignores SVG apple-touch-icons, so this one has to be a PNG — which is
 * why it is generated rather than checked in: a hand-exported bitmap is
 * exactly the asset that silently falls a redesign behind. Drawn with a square
 * ground because iOS applies its own corner mask, and rounding it twice leaves
 * a dark rim inside the platform's radius.
 */
export const size = { width: 180, height: 180 };
export const contentType = "image/png";

export default function AppleIcon() {
  const svg = renderMarkSvg({
    ramp: BRAND_RAMP_DARK,
    ground: BRAND_GROUND_DARK,
    groundRadius: 0,
    inset: 0.74,
    label: BRAND_NAME,
  });

  return new ImageResponse(
    (
      <div style={{ display: "flex", width: "100%", height: "100%" }}>
        {/* A plain <img> on purpose: satori is the renderer here, and
            next/image has no meaning inside an ImageResponse. */}
        <img
          src={`data:image/svg+xml;base64,${Buffer.from(svg).toString("base64")}`}
          alt=""
          width={size.width}
          height={size.height}
        />
      </div>
    ),
    { ...size },
  );
}
