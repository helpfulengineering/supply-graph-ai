import fs from "node:fs";
import path from "node:path";
import { field, ohm } from "./ohm";

/**
 * Everything one pass of the UAT has made: the CI form of `notes/uat/state.env`.
 *
 * It lives in a file, not in module state. Playwright starts a fresh worker
 * after a failed test, and a later part running in that worker would otherwise
 * find an empty world and fail on something unrelated to what actually broke.
 * Reading the file instead means a part either finds what it needs or says
 * which part to run first.
 *
 * It holds tokens. It sits under `artifacts/` beside, not inside, the evidence
 * folders the workflow uploads, and the node it describes is destroyed when the
 * run ends.
 */
export interface Person {
  name: string;
  accountId: string;
  did: string;
  token: string;
}

export interface World {
  operator?: Person;
  /** The people downstream parts use. Keys are the cast: ada, bo, chi. */
  people?: Record<string, Person>;
  spaceDid?: string;
  /** Design ids this pass created, keyed by a short name. */
  designs?: Record<string, string>;
  hashes?: Record<string, string>;
  listId?: string;
}

const FILE = path.resolve(process.cwd(), "artifacts/uat-world/world.json");

export function loadWorld(): World {
  try {
    return JSON.parse(fs.readFileSync(FILE, "utf-8")) as World;
  } catch {
    return {};
  }
}

export function saveWorld(patch: Partial<World>): World {
  const next = { ...loadWorld(), ...patch };
  fs.mkdirSync(path.dirname(FILE), { recursive: true });
  fs.writeFileSync(FILE, JSON.stringify(next, null, 2), { mode: 0o600 });
  return next;
}

export function resetWorld(): void {
  fs.rmSync(FILE, { force: true });
}

/**
 * The operator, proven to still work.
 *
 * Each part opens with this so that a failure names the precondition
 * ("the operator from part 0 is not accepted") rather than surfacing three
 * steps later as a puzzling 401.
 */
export async function requireOperator(): Promise<Person> {
  const operator = loadWorld().operator;
  if (!operator) {
    throw new Error("No operator in the world. Run part 0 first.");
  }
  const who = await ohm(operator.token, ["identity", "whoami"]);
  if (who.subject_did !== operator.did) {
    throw new Error(
      "The operator from part 0 is not accepted by this node. Was the node " +
        "restarted with different storage?",
    );
  }
  return operator;
}

/**
 * Mint a person account with a DID and a read/write token, as the operator.
 * Idempotent on the cast key: a second call returns the stored person.
 */
export async function mintPerson(
  operator: Person,
  cast: string,
  displayName: string,
): Promise<Person> {
  const existing = loadWorld().people?.[cast];
  if (existing) {
    return existing;
  }
  const account = await ohm(operator.token, [
    "identity",
    "accounts",
    "create",
    "--name",
    displayName,
  ]);
  const accountId = field(account, "id");
  const identity = await ohm(operator.token, [
    "identity",
    "identities",
    "create",
    "--account-id",
    accountId,
    "--kind",
    "person",
    "--name",
    displayName,
  ]);
  const key = await ohm(operator.token, [
    "identity",
    "keys",
    "create",
    "--name",
    displayName,
    "--permission",
    "read",
    "--permission",
    "write",
    "--account-id",
    accountId,
  ]);
  const person: Person = {
    name: displayName,
    accountId,
    did: field(identity, "did"),
    token: field(key, "token"),
  };
  const people = { ...(loadWorld().people ?? {}), [cast]: person };
  saveWorld({ people });
  return person;
}

export async function requirePerson(cast: string): Promise<Person> {
  const person = loadWorld().people?.[cast];
  if (!person) {
    throw new Error(`No ${cast} in the world. Run the part that mints them.`);
  }
  const who = await ohm(person.token, ["identity", "whoami"]);
  if (who.subject_did !== person.did) {
    throw new Error(
      `${cast} from an earlier part is not accepted by this node.`,
    );
  }
  return person;
}
