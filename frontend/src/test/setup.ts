import "@testing-library/jest-dom/vitest";
import { afterAll, afterEach, beforeAll, vi } from "vitest";
import { server } from "./msw/server";

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
});
