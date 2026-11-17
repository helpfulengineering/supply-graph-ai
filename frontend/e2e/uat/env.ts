import path from "node:path";

/**
 * Where the UAT runs, and the refusal that keeps it off production.
 *
 * The suite creates accounts, mints keys, publishes designs and deletes
 * accounts. A maintainer's checkout usually has a `.env` that names a real
 * storage container, and the API reads it, so "the server on localhost:8001"
 * is not evidence that the node is disposable. The suite therefore starts only
 * when the caller says in so many words that this node is a throwaway one.
 * The workflow sets it after building a node with local storage and nothing
 * else; a person sets it only against a node they started that way.
 *
 * This is a function and not a constant so that listing the specs
 * (`playwright test --list`) does not need the variable.
 */
export interface UatEnv {
  /** Base URL of the API under test. The CLI talks to this directly. */
  apiUrl: string;
  /** The bootstrap key (`API_KEYS`). Used once, to mint the operator. */
  bootstrapKey: string;
  /** The `ohm` binary. */
  ohmBin: string;
}

/**
 * The names the node is started with (`OHM_FEDERATION_NODE_NAME`,
 * `OHM_NODE_OPERATOR`). The registration page says them aloud, and part 1
 * checks that it does. The workflow starts the node with these values.
 */
export const NODE_NAME = process.env.UAT_NODE_NAME ?? "Field node";
export const OPERATOR_NAME = process.env.UAT_OPERATOR_NAME ?? "Ada's workshop";

export function uatEnv(): UatEnv {
  if (process.env.UAT_THROWAWAY_NODE !== "1") {
    throw new Error(
      "Refusing to run the UAT. It creates and deletes accounts, and the node " +
        "it points at may be backed by real storage. Set UAT_THROWAWAY_NODE=1 " +
        "only for a node you started with STORAGE_PROVIDER=local and no cloud " +
        "credentials. The weekly workflow does.",
    );
  }
  const bootstrapKey = (process.env.API_KEYS ?? "").split(",")[0]?.trim() ?? "";
  if (!bootstrapKey) {
    throw new Error(
      "API_KEYS is empty. The UAT mints the operator with the bootstrap key, " +
        "so it must be in this process's environment (the value the node was " +
        "started with).",
    );
  }
  return {
    apiUrl: (process.env.UAT_API_URL ?? "http://localhost:8001").replace(
      /\/+$/,
      "",
    ),
    bootstrapKey,
    ohmBin:
      process.env.UAT_OHM_BIN ??
      path.resolve(process.cwd(), "../.venv/bin/ohm"),
  };
}
