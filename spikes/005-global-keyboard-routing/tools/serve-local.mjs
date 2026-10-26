import { createServer } from "node:http";
import { readFileSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const projectRoot = fileURLToPath(new URL("../", import.meta.url));
const webRoot = path.join(projectRoot, "web");

export const CSP_POLICY =
  "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'none'; form-action 'none'; base-uri 'none'; img-src 'self'; font-src 'none'";

const MIME_TYPES = new Map([
  [".html", "text/html; charset=utf-8"],
  [".mjs", "text/javascript; charset=utf-8"],
  [".js", "text/javascript; charset=utf-8"],
  [".css", "text/css; charset=utf-8"]
]);

function resolveRequestPath(requestURL) {
  const rawPath = (requestURL ?? "/").split("?")[0];
  const decoded = decodeURIComponent(rawPath);
  const relative = decoded === "/" ? "index.html" : decoded.replace(/^\/+/, "");
  const resolved = path.resolve(webRoot, relative);
  const webPrefix = webRoot + path.sep;
  if (resolved !== webRoot && !resolved.startsWith(webPrefix)) {
    return null;
  }
  return resolved;
}

export function createLocalServer() {
  return createServer((request, response) => {
    if (request.method !== "GET" && request.method !== "HEAD") {
      response.writeHead(405, { "Content-Type": "text/plain; charset=utf-8" });
      response.end("method not allowed\n");
      return;
    }

    const filePath = resolveRequestPath(request.url);
    if (!filePath) {
      response.writeHead(400, { "Content-Type": "text/plain; charset=utf-8" });
      response.end("bad path\n");
      return;
    }

    let body;
    try {
      if (!statSync(filePath).isFile()) {
        throw new Error("not a file");
      }
      body = readFileSync(filePath);
    } catch {
      response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
      response.end("not found\n");
      return;
    }

    const mime = MIME_TYPES.get(path.extname(filePath).toLowerCase()) ?? "application/octet-stream";
    response.writeHead(200, {
      "Content-Type": mime,
      "Content-Security-Policy": CSP_POLICY,
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff"
    });
    if (request.method === "HEAD") {
      response.end();
      return;
    }
    response.end(body);
  });
}

async function main() {
  const port = Number.parseInt(process.argv[2] ?? "8765", 10);
  if (!Number.isInteger(port) || port < 0 || port > 65535) {
    throw new Error("port must be an integer between 0 and 65535");
  }
  const server = createLocalServer();
  server.listen(port, "127.0.0.1", () => {
    process.stdout.write(`Manual oracle server: 127.0.0.1:${server.address().port}/\n`);
  });
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((error) => {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  });
}
