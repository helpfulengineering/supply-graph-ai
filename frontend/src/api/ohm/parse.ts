import { ZodType } from "zod";
import { ApiError } from "./client";

/**
 * Parse a response payload at the client boundary.
 *
 * Generated types close the *authoring* gap: with a response model declared,
 * the compiler knows the shape at build time. They do nothing about the
 * *deployment* gap — a server that changes after this bundle was built still
 * hands it a payload the types promise cannot happen.
 *
 * That gap is what produced #369. A drift arrived as React error #31 thrown
 * deep inside a render, with a minified component name and no mention of the
 * endpoint or the field. This turns the same drift into a message that names
 * both, at the seam it entered through.
 *
 * Reserved for routes whose shape the compiler cannot vouch for. Parsing every
 * response would mean a hand-maintained schema beside every generated type —
 * two sources of truth for ninety endpoints, which is its own drift risk.
 */
export function parsePayload<T>(
  endpoint: string,
  schema: ZodType<T>,
  payload: unknown,
): T {
  const result = schema.safeParse(payload);
  if (result.success) return result.data;

  const [issue] = result.error.issues;
  const field = issue.path.join(".") || "(root)";
  // Status 200 because that is what the server actually sent: the request
  // succeeded, its body is wrong. It also keeps userMessage on the branch that
  // shows this message and marks it non-retryable, which is right — repeating
  // the request cannot change a shape mismatch. A 5xx here would replace the
  // endpoint and field with generic "the server hit a problem" copy.
  throw new ApiError(
    200,
    `${endpoint} returned an unexpected shape: ${field} — ${issue.message}`,
  );
}
