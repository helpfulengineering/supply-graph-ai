/**
 * Failures, said in the user's language.
 *
 * The app had one of these already — `generationErrorMessage` in
 * GenerateView — written because "429" tells a non-technical person nothing.
 * That reasoning was never specific to generation, but the module was, so
 * every other surface fell back to printing `err.message`: a raw
 * `TypeError: Failed to fetch` for a dropped connection, a bare "Not Found"
 * for a record that was deleted, and the same flat "Something went wrong"
 * heading over all of it.
 *
 * This is that mapping, generalized, with the shape a message actually needs:
 * a title naming what failed, a body saying what it means and what to do, and
 * `retryable` — whether pressing the same button again could plausibly work.
 * A retry control offered on a 403 is worse than no control, because it asks a
 * person to keep trying something that cannot succeed.
 *
 * Pure and framework-free so the copy can be asserted directly, and so
 * `app/error.tsx`, `ErrorMessage`, and any future surface read one source
 * rather than each inventing its own wording for the same status.
 *
 * Domain-specific mappings still belong to their domain: `generationErrorMessage`
 * knows a 404 there means a repository URL, which is not what a 404 means
 * anywhere else in the app.
 */
import { ApiError } from "../api/ohm/client";

export interface UserFacingError {
  /** One line naming what failed. Sentence case, no terminal period. */
  title: string;
  /** What it means and what to do next. One or two sentences. */
  body: string;
  /** Whether the identical request could plausibly succeed on a second try. */
  retryable: boolean;
  /** Correlation id to quote to an operator, when the API sent one. */
  requestId?: string;
}

/** The last resort, and the wording every surface used to hardcode. */
const UNKNOWN: UserFacingError = {
  title: "Something went wrong",
  body: "The app hit a problem it could not identify. Reloading the page usually clears it.",
  retryable: true,
};

/**
 * True when the browser itself says there is no connection.
 *
 * Worth distinguishing because it is the one failure the user can fix and the
 * app cannot: no amount of retrying reaches a server that is unreachable, and
 * "the request failed" sends someone looking for a bug on our side.
 */
function isOffline(): boolean {
  return typeof navigator !== "undefined" && navigator.onLine === false;
}

/**
 * A fetch that never reached a server.
 *
 * `fetch` rejects with a bare `TypeError` for DNS failure, a refused
 * connection, a CORS rejection, and an offline device alike — the message text
 * differs per browser and carries nothing a user could act on, so it is
 * replaced rather than shown.
 */
function isNetworkFailure(err: unknown): boolean {
  return err instanceof TypeError && /fetch|network/i.test(err.message);
}

/** An in-flight request the app itself cancelled — a navigation, a new query. */
function isAbort(err: unknown): boolean {
  return err instanceof Error && err.name === "AbortError";
}

function fromStatus(err: ApiError): UserFacingError {
  const base = { requestId: err.requestId };
  switch (err.status) {
    case 401:
      return {
        ...base,
        title: "Not signed in",
        body: "This action needs an API key. Add one under Settings, then try again.",
        retryable: false,
      };
    case 403:
      return {
        ...base,
        title: "Not allowed",
        body: "Your API key does not carry permission for this. An instance administrator can grant it.",
        retryable: false,
      };
    case 404:
      return {
        ...base,
        title: "Not found",
        body: "That record is not on this instance. It may have been removed, or it may live on a peer this instance does not federate with.",
        retryable: false,
      };
    case 408:
    case 504:
      return {
        ...base,
        title: "The request timed out",
        body: "The server took too long to answer. Trying again often works; a large request may need to be narrowed.",
        retryable: true,
      };
    case 409:
      return {
        ...base,
        title: "That conflicts with something already saved",
        body:
          err.message ||
          "The record changed since this page loaded. Reload to see the current version before saving again.",
        retryable: false,
      };
    case 413:
      return {
        ...base,
        title: "That upload is too large",
        body: "This instance caps the size of an upload. Try a smaller file, or link to it instead of attaching it.",
        retryable: false,
      };
    case 422:
      // The API's own validation text is the useful part here: it names the
      // field. Wrapping it in our own sentence would bury the one detail that
      // tells the user what to change.
      return {
        ...base,
        title: "That request was rejected",
        body: err.message || "Some of the values sent were not valid.",
        retryable: false,
      };
    case 429:
      return {
        ...base,
        title: "Too many requests",
        body: "This instance is rate-limiting requests. Wait a little while, then try again.",
        retryable: true,
      };
    case 503:
      return {
        ...base,
        title: "That service is not available",
        body: "This instance is not running the service behind this page, or it is restarting. Try again shortly.",
        retryable: true,
      };
    default:
      if (err.status >= 500) {
        return {
          ...base,
          title: "The server hit a problem",
          body: "This is a fault on the instance, not with what you sent. Trying again is worth a shot; if it persists, an operator will need the request id.",
          retryable: true,
        };
      }
      return {
        ...base,
        title: "That request could not be completed",
        body: err.message || UNKNOWN.body,
        retryable: false,
      };
  }
}

export interface UserFacingErrorOptions {
  /**
   * Whether a plain `Error`'s own message is fit to show.
   *
   * True where the throw site is known and writes prose — `new Error("Package
   * not found")`, an API wrapper's fallback text — which is most of this app.
   *
   * False at a boundary that catches whatever happened to be thrown, where the
   * message is as likely to be "Cannot read properties of undefined (reading
   * 'map')". Recognized failures (an ApiError, a dead connection) are still
   * described exactly; only the unrecognizable ones fall back to generic copy,
   * and the raw text belongs in a technical detail block rather than in the
   * sentence a visitor reads first.
   */
  trustErrorMessage?: boolean;
}

/**
 * Turn anything thrown into something a person can read and act on.
 *
 * Accepts `unknown` because that is what a catch block and a react-query
 * `error` actually hand you — narrowing is this function's job, not every
 * caller's.
 */
export function userFacingError(
  err: unknown,
  { trustErrorMessage = true }: UserFacingErrorOptions = {},
): UserFacingError {
  if (isOffline()) {
    return {
      title: "You are offline",
      body: "This device has no network connection. The page will work again once it is back.",
      retryable: true,
    };
  }
  if (err instanceof ApiError) return fromStatus(err);
  if (isNetworkFailure(err)) {
    return {
      title: "Could not reach the server",
      body: "The request never arrived. The instance may be down, or something between here and it is blocking the connection.",
      retryable: true,
    };
  }
  if (isAbort(err)) {
    return {
      title: "That request was cancelled",
      body: "The app stopped the request before it finished — usually because the page moved on. Try again if you still need it.",
      retryable: true,
    };
  }
  if (trustErrorMessage && err instanceof Error && err.message.trim()) {
    return { ...UNKNOWN, body: err.message };
  }
  return UNKNOWN;
}
