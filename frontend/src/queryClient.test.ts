import { describe, it, expect, vi } from "vitest";
import { QueryClient } from "@tanstack/react-query";
import {
  queryClient,
  LOW_VOLATILITY_QUERY_KEYS,
  refreshLowVolatilityData,
} from "./queryClient";

const ONE_HOUR = 60 * 60 * 1000;

describe("queryClient defaults", () => {
  it("caches aggressively with auto-refetch disabled", () => {
    const defaults = queryClient.getDefaultOptions().queries!;
    expect(defaults.staleTime).toBe(ONE_HOUR);
    expect(defaults.gcTime).toBe(2 * ONE_HOUR);
    expect(defaults.refetchOnWindowFocus).toBe(false);
    expect(defaults.refetchOnReconnect).toBe(false);
  });
});

describe("refreshLowVolatilityData", () => {
  it("invalidates each low-volatility query key exactly once", async () => {
    const client = new QueryClient();
    const spy = vi
      .spyOn(client, "invalidateQueries")
      .mockResolvedValue(undefined);

    await refreshLowVolatilityData(client);

    expect(spy).toHaveBeenCalledTimes(LOW_VOLATILITY_QUERY_KEYS.length);
    for (const key of LOW_VOLATILITY_QUERY_KEYS) {
      expect(spy).toHaveBeenCalledWith({ queryKey: [...key] });
    }
  });

  it("invalidates a matching cached query via prefix match", async () => {
    const client = new QueryClient();
    // Both the shared baseline and a filtered variant fall under ["network"].
    client.setQueryData(["network", "baseline"], { spaces: [] });
    client.setQueryData(["network", { country: "US" }], { spaces: [] });

    await refreshLowVolatilityData(client);

    expect(client.getQueryState(["network", "baseline"])?.isInvalidated).toBe(
      true,
    );
    expect(
      client.getQueryState(["network", { country: "US" }])?.isInvalidated,
    ).toBe(true);
  });
});
