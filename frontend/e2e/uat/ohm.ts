import { execFile } from "node:child_process";
import { uatEnv } from "./env";

/**
 * Run one `ohm` command as one credential and return its JSON.
 *
 * The key travels in `OHM_API_KEY` for this single child process, never in the
 * argument list, so it is not in a process listing or in an error message.
 *
 * Empty output is a failure. The identity commands exit 0 and print nothing when
 * the node answers 401, so a wrong or revoked key looks exactly like a command
 * that had nothing to say. Treating that as success is how a flow can "pass"
 * on a credential that never worked; `ohm-helper.spec.ts` pins it.
 */
export class OhmError extends Error {}

export function ohm<T = Record<string, unknown>>(
  token: string,
  args: string[],
  serverUrl?: string,
): Promise<T> {
  const env = uatEnv();
  const url = serverUrl ?? env.apiUrl;
  const argv = ["--server-url", url, ...args, "--json"];
  const label = `ohm ${args.join(" ")}`;
  return new Promise((resolve, reject) => {
    execFile(
      env.ohmBin,
      argv,
      {
        env: { ...process.env, OHM_API_KEY: token },
        maxBuffer: 16 * 1024 * 1024,
        timeout: 60_000,
      },
      (error, stdout, stderr) => {
        if (error) {
          // The CLI reports its own failure on stdout and writes unrelated
          // configuration warnings to stderr, so the cause is in both. A failed
          // command prints no token; a successful one is not reported here.
          const said = [stdout.trim(), stderr.trim()]
            .filter(Boolean)
            .join("\n")
            .slice(-1200);
          reject(new OhmError(`${label} failed: ${said || error.message}`));
          return;
        }
        const text = stdout.trim();
        if (!text) {
          reject(
            new OhmError(
              `${label} returned no JSON. The key was refused: the identity ` +
                "CLI exits 0 and prints nothing on a 401.",
            ),
          );
          return;
        }
        try {
          resolve(JSON.parse(text) as T);
        } catch {
          reject(new OhmError(`${label} printed something that is not JSON.`));
        }
      },
    );
  });
}

/** `ohm` as the bootstrap key. Only the first minting uses this. */
export function ohmAsBootstrap<T = Record<string, unknown>>(
  args: string[],
): Promise<T> {
  return ohm<T>(uatEnv().bootstrapKey, args);
}

/** A field that must be present, as a string. */
export function field(data: Record<string, unknown>, name: string): string {
  const value = data[name];
  if (value === undefined || value === null || value === "") {
    throw new OhmError(`expected "${name}" in the response`);
  }
  return String(value);
}
