// Cloudflare Pages front door for ThreatRAG: every request is passed to the Cloud Run web service
// (nginx + React), which proxies /api to the API. Responses stream through untouched, so SSE
// investigations still arrive live. Nothing is cached here: the API is per-user and dynamic.
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const target = new URL(url.pathname + url.search, env.ORIGIN);
    const headers = new Headers(request.headers);
    headers.delete("host");
    // The visitor's address, for per-visitor rate limits behind two proxies
    const ip = request.headers.get("cf-connecting-ip");
    if (ip) headers.set("x-forwarded-for", ip);
    headers.set("x-forwarded-host", url.host);
    headers.set("x-forwarded-proto", "https");
    return fetch(target, {
      method: request.method,
      headers,
      body: ["GET", "HEAD"].includes(request.method) ? undefined : request.body,
      redirect: "manual",
    });
  },
};
