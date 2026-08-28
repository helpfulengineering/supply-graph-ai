/**
 * Format conversion, in and out of the OKH manifest.
 *
 * CLI-only until now, which is why the docs page claiming it works carried no
 * frontend evidence for the claim.
 *
 * Both importers return a manifest WITHOUT saving it. That is what makes them a
 * better fit for the guided create flow than /api/okh/upload, which validates
 * and stores in one step: a converted manifest can land in the editor for
 * review before anything is written.
 */
import {
  apiClient,
  ApiError,
  errorMessage,
  requestIdFromError,
} from "./client";
import type { OkhManifest } from "../../types/okh";
import type { components } from "../generated/schema";

type DatasheetBody = components["schemas"]["ConvertToDatasheetRequest"];

function fail(error: unknown, response: Response, fallback: string): never {
  throw new ApiError(
    response.status,
    errorMessage(error, `${fallback} (HTTP ${response.status})`),
    requestIdFromError(error, response),
  );
}

/**
 * Render a design as an MSF technical-specification datasheet (.docx).
 *
 * Returns the bytes rather than triggering the download, so the caller owns the
 * object URL and its revocation.
 */
export async function toDatasheet(manifest: OkhManifest): Promise<Blob> {
  const { data, error, response } = await apiClient.POST(
    "/api/convert/to-datasheet",
    {
      // The manifest IS the request body: its fields sit at the top level
      // alongside the shared request base, not nested under a `manifest` key.
      // Cast once, here, because OkhManifest is the app's view type and the
      // generated request type is the server's — they agree on the fields that
      // matter and disagree on optionality, and reconciling them field by field
      // would be a second manifest model to keep in step.
      body: {
        ...manifest,
        quality_level: null,
        strict_mode: null,
      } as unknown as DatasheetBody,
      // A .docx stream, not JSON. Without this openapi-fetch parses the body as
      // JSON and the download arrives corrupt.
      parseAs: "blob",
    },
  );
  if (error || !response.ok || !data) {
    fail(error, response, "Could not build the datasheet");
  }
  return data as unknown as Blob;
}

async function convertFile(
  path: "/api/convert/from-okh-losh" | "/api/convert/from-datasheet",
  field: string,
  file: File,
  fallback: string,
): Promise<OkhManifest> {
  const form = new FormData();
  form.append(field, file);
  const { data, error, response } = await apiClient.POST(path, {
    body: form as unknown as never,
    // Pass the FormData through untouched. The default serializer would JSON
    // it, and setting Content-Type by hand drops the multipart boundary the
    // browser generates.
    bodySerializer: (body: unknown) => body as BodyInit,
  });
  if (error || !response.ok || !data) fail(error, response, fallback);
  const manifest = (data as { manifest?: unknown }).manifest ?? data;
  return manifest as OkhManifest;
}

/** OKH-LOSH v2.4 TOML in, OKH manifest out. Nothing is stored. */
export function fromOkhLosh(file: File): Promise<OkhManifest> {
  return convertFile(
    "/api/convert/from-okh-losh",
    "toml_file",
    file,
    "Could not read that OKH-LOSH file",
  );
}

/** MSF datasheet (.docx) in, OKH manifest out. Nothing is stored. */
export function fromDatasheet(file: File): Promise<OkhManifest> {
  return convertFile(
    "/api/convert/from-datasheet",
    "datasheet_file",
    file,
    "Could not read that datasheet",
  );
}

/** What the create flow accepts, and what happens to each. */
export const IMPORT_FORMATS = [
  { label: ".yaml / .json", note: "An OKH manifest. Read in the browser." },
  { label: ".toml", note: "OKH-LOSH v2.4. Converted by this node." },
  { label: ".docx", note: "An MSF datasheet. Converted by this node." },
] as const;

export const IMPORT_ACCEPT = ".yaml,.yml,.json,.toml,.docx";

/** Which route a dropped file takes, by extension. */
export function importRouteFor(
  filename: string,
): "parse" | "okh-losh" | "datasheet" | null {
  const name = filename.toLowerCase();
  if (/\.(ya?ml|json)$/.test(name)) return "parse";
  if (name.endsWith(".toml")) return "okh-losh";
  if (name.endsWith(".docx")) return "datasheet";
  return null;
}
