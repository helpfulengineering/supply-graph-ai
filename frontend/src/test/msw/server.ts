import { setupServer } from "msw/node";
import { handlers } from "./handlers";

// Node MSW server for vitest. Started/stopped in src/test/setup.ts.
export const server = setupServer(...handlers);
