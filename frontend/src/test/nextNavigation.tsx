import { vi } from "vitest";
import {
  useSyncExternalStore,
  type AnchorHTMLAttributes,
  type ReactNode,
} from "react";

/**
 * Shared next/navigation double for component tests. setup.ts registers the
 * module mocks; tests seed location state through `setMockNavigation` (the
 * replacement for MemoryRouter's `initialEntries`) and assert navigation
 * through `mockRouter`.
 *
 * The double is reactive: `router.push`/`replace` update the mock location and
 * notify subscribed hooks, so components that rewrite their own query string
 * (e.g. dismissing the `?created=1` banner) re-render exactly as they do under
 * the real router. Cross-page navigation stays an assertion on the spy — there
 * is no route tree in jsdom to render.
 */

interface MockNavigationState {
  pathname: string;
  params: Record<string, string | string[]>;
  searchParams: URLSearchParams;
}

const state: MockNavigationState = {
  pathname: "/",
  params: {},
  searchParams: new URLSearchParams(),
};

let version = 0;
const listeners = new Set<() => void>();

function notify(): void {
  version += 1;
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function useMockLocationVersion(): number {
  return useSyncExternalStore(
    subscribe,
    () => version,
    () => version,
  );
}

function applyUrl(url: string): void {
  const [pathname, search = ""] = url.split("?");
  state.pathname = pathname;
  state.searchParams = new URLSearchParams(search);
  notify();
}

export const mockRouter = {
  push: vi.fn((url: string) => applyUrl(url)),
  replace: vi.fn((url: string) => applyUrl(url)),
  back: vi.fn(),
  forward: vi.fn(),
  refresh: vi.fn(),
  prefetch: vi.fn(),
};

export function setMockNavigation(
  next: Partial<{
    pathname: string;
    params: Record<string, string | string[]>;
    search: string;
  }>,
): void {
  if (next.pathname !== undefined) state.pathname = next.pathname;
  if (next.params !== undefined) state.params = next.params;
  if (next.search !== undefined)
    state.searchParams = new URLSearchParams(next.search);
  notify();
}

export function resetMockNavigation(): void {
  state.pathname = "/";
  state.params = {};
  state.searchParams = new URLSearchParams();
  mockRouter.push.mockClear();
  mockRouter.replace.mockClear();
  mockRouter.back.mockClear();
  mockRouter.forward.mockClear();
  mockRouter.refresh.mockClear();
  mockRouter.prefetch.mockClear();
  notify();
}

export function useMockPathname(): string {
  useMockLocationVersion();
  return state.pathname;
}

export function useMockParams(): Record<string, string | string[]> {
  useMockLocationVersion();
  return state.params;
}

export function useMockSearchParams(): URLSearchParams {
  useMockLocationVersion();
  return state.searchParams;
}

type MockLinkProps = AnchorHTMLAttributes<HTMLAnchorElement> & {
  href: string;
  children?: ReactNode;
  prefetch?: boolean;
  replace?: boolean;
  scroll?: boolean;
};

/** Plain-anchor stand-in for next/link; navigation itself is asserted via mockRouter. */
export function MockLink({
  href,
  children,
  prefetch: _p,
  replace: _r,
  scroll: _s,
  ...rest
}: MockLinkProps) {
  return (
    <a href={href} {...rest}>
      {children}
    </a>
  );
}
