// Static file server for the candidate UI with a same-origin /api/v1 proxy.
//
// Usage: node checks/serve.mjs [port]
// The browser always talks to http://127.0.0.1:<port>/api/v1 so CORS never
// forces the UI to know the control-plane origin.  Override the upstream with
// NAA_API_UPSTREAM (default http://127.0.0.1:8000).

import { createServer } from "node:http";
import { createReadStream, existsSync, statSync } from "node:fs";
import { extname, join, normalize, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(fileURLToPath(new URL("..", import.meta.url)));
const port = Number(process.argv[2] || process.env.PORT || 8100);
const upstream = (process.env.NAA_API_UPSTREAM || "http://127.0.0.1:8000").replace(/\/+$/, "");

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".woff2": "font/woff2",
  ".ico": "image/x-icon"
};

function sendJson(response, status, body) {
  const text = JSON.stringify(body);
  response.writeHead(status, {
    "content-type": "application/json; charset=utf-8",
    "cache-control": "no-store",
    "content-length": Buffer.byteLength(text)
  });
  response.end(text);
}

async function proxy(request, response, url) {
  const chunks = [];
  for await (const chunk of request) chunks.push(chunk);
  const body = chunks.length ? Buffer.concat(chunks) : undefined;
  const headers = { ...request.headers, host: new URL(upstream).host };
  delete headers.connection;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 15000);
  try {
    const upstreamResponse = await fetch(`${upstream}${url.pathname}${url.search}`, {
      method: request.method,
      headers,
      body: request.method === "GET" || request.method === "HEAD" ? undefined : body,
      signal: controller.signal
    });
    const bytes = Buffer.from(await upstreamResponse.arrayBuffer());
    const out = {};
    for (const [key, value] of upstreamResponse.headers.entries()) {
      if (["content-encoding", "transfer-encoding", "connection"].includes(key)) continue;
      out[key] = value;
    }
    response.writeHead(upstreamResponse.status, { ...out, "cache-control": "no-store" });
    response.end(bytes);
  } catch (error) {
    const aborted = error && error.name === "AbortError";
    sendJson(response, aborted ? 504 : 502, {
      error: {
        code: aborted ? "UPSTREAM_TIMEOUT" : "UPSTREAM_UNREACHABLE",
        message: aborted ? "Control plane timed out" : "Control plane is unreachable",
        retryable: true
      }
    });
  } finally {
    clearTimeout(timer);
  }
}

function serveStatic(request, response, url) {
  let pathname = decodeURIComponent(url.pathname);
  if (pathname === "/") pathname = "/index.html";
  const relative = normalize(pathname).replace(/^(\.\.[/\\])+/, "");
  let file = resolve(join(root, relative));
  if (!file.startsWith(`${root}/`) && file !== root) {
    response.writeHead(403);
    response.end("forbidden");
    return;
  }
  if (existsSync(file) && statSync(file).isDirectory()) file = join(file, "index.html");
  if (!existsSync(file) || !statSync(file).isFile()) {
    response.writeHead(404, { "content-type": "text/plain; charset=utf-8" });
    response.end("not found");
    return;
  }
  const type = MIME[extname(file)] || "application/octet-stream";
  response.writeHead(200, { "content-type": type, "cache-control": "no-store" });
  if (request.method === "HEAD") {
    response.end();
    return;
  }
  createReadStream(file).pipe(response);
}

createServer((request, response) => {
  const url = new URL(request.url || "/", `http://127.0.0.1:${port}`);
  if (url.pathname.startsWith("/api/v1/")) {
    void proxy(request, response, url);
    return;
  }
  serveStatic(request, response, url);
}).listen(port, "127.0.0.1", () => {
  console.log(`candidate UI on http://127.0.0.1:${port}/ (proxy /api/v1 -> ${upstream})`);
});
