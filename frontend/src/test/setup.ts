import "@testing-library/jest-dom/vitest";
import { afterAll, afterEach, beforeAll } from "vitest";
import { server } from "./msw/server";

// Start the MSW mock API for all unit/component tests. Fixtures are shared with
// the Playwright mocked E2E lane so mock data has a single source of truth.
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
