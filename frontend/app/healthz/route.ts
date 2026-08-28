// Load balancer / container health probe. Mirrors the nginx `location = /healthz`
// contract: 200 "ok\n", no logging dependence, no upstream involvement.
export function GET(): Response {
  return new Response("ok\n", {
    headers: { "content-type": "text/plain; charset=utf-8" },
  });
}

export const dynamic = "force-dynamic";
