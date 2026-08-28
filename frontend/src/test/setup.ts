import "@testing-library/jest-dom/vitest";
import { afterAll, afterEach, beforeAll, vi } from "vitest";
import { server } from "./msw/server";

/**
 * Web Storage, which this environment does not supply.
 *
 * Node 26 defines `localStorage` as a native global that is inert without
 * `--localstorage-file`, and it shadows the one jsdom would otherwise install
 * (`window === globalThis` here, so there is no second object to fall back
 * to). The result is `localStorage === undefined` inside jsdom, which is not
 * a shape any browser presents.
 *
 * Installed once, for every suite, rather than stubbed per test: the per-test
 * stub was already being written by hand in useDomainPreference.test.ts, and
 * the site-layer suite assumed a real one and got a TypeError. Both storages
 * are cleared between tests below, so seeding one is a normal thing to do.
 */
function installStorage(name: "localStorage" | "sessionStorage"): void {
  if (typeof (globalThis as Record<string, unknown>)[name] !== "undefined") {
    return;
  }
  const entries = new Map<string, string>();
  const storage: Storage = {
    get length() {
      return entries.size;
    },
    key: (i) => [...entries.keys()][i] ?? null,
    getItem: (k) => entries.get(String(k)) ?? null,
    setItem: (k, v) => void entries.set(String(k), String(v)),
    removeItem: (k) => void entries.delete(String(k)),
    clear: () => entries.clear(),
  };
  // defineProperty, not vi.stubGlobal: several suites call
  // vi.unstubAllGlobals() in their own afterEach, which would take this with
  // them and leave every later suite without storage again.
  Object.defineProperty(globalThis, name, {
    value: storage,
    configurable: true,
    writable: true,
  });
}
installStorage("localStorage");
installStorage("sessionStorage");

// Components read routing through next/navigation, which needs a mounted App
// Router. jsdom has none, so every test runs against this double; tests seed
// location state via setMockNavigation and assert through mockRouter.
vi.mock("next/navigation", async () => {
  const mock = await import("./nextNavigation");
  return {
    useRouter: () => mock.mockRouter,
    usePathname: () => mock.useMockPathname(),
    useSearchParams: () => mock.useMockSearchParams(),
    useParams: () => mock.useMockParams(),
    redirect: vi.fn(),
    notFound: vi.fn(),
  };
});

vi.mock("next/link", async () => {
  const mock = await import("./nextNavigation");
  return { default: mock.MockLink };
});

// Start the MSW mock API for all unit/component tests. Fixtures are shared with
// the Playwright mocked E2E lane so mock data has a single source of truth.
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

afterEach(async () => {
  const { resetMockNavigation } = await import("./nextNavigation");
  resetMockNavigation();
  // Storage outlives a test otherwise, and navState stashes RFQ payloads in
  // sessionStorage — one test's hand-off would be readable by the next.
  localStorage?.clear();
  sessionStorage?.clear();
});
