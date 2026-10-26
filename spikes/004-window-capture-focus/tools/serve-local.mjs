import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

export const HOST = "127.0.0.1";
export const DEFAULT_PORT = 8642;

export const CSP_POLICY =
  "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; media-src 'self' blob: mediastream:; connect-src 'none'; font-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'";

export const PERMISSIONS_POLICY =
  "camera=(), microphone=(), geolocation=(), display-capture=(self)";

const SECURITY_HEADERS = Object.freeze({
  "Content-Security-Policy": CSP_POLICY,
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "no-referrer",
  "Permissions-Policy": PERMISSIONS_POLICY,
  "X-Frame-Options": "DENY",
  "Cross-Origin-Opener-Policy": "same-origin",
  "Cross-Origin-Resource-Policy": "same-origin",
  "Cache-Control": "no-store"
});

const MIME_TYPES = new Map([
  [".html", "text/html; charset=utf-8"],
  [".mjs", "text/javascript; charset=utf-8"],
  [".js", "text/javascript; charset=utf-8"],
  [".css", "text/css; charset=utf-8"],
  [".txt", "text/plain; charset=utf-8"],
  [".svg", "image/svg+xml"],
  [".png", "image/png"],
  [".ico", "image/x-icon"]
]);

const WEB_ROOT = fileURLToPath(new URL("../web", import.meta.url));

export function contentTypeFor(filePath) {
  return MIME_TYPES.get(path.extname(filePath).toLowerCase()) ?? null;
}

export function resolveRequestPath(root, requestUrl) {
  let pathname;
  try {
    pathname = decodeURIComponent(new URL(requestUrl, "http://127.0.0.1").pathname);
  } catch {
    return null;
  }
  if (pathname.includes("\0")) return null;
  if (pathname.endsWith("/")) pathname += "index.html";

  const candidate = path.resolve(root, `.${pathname}`);
  const relative = path.relative(root, candidate);
  if (
    relative.length === 0 ||
    relative.startsWith("..") ||
    path.isAbsolute(relative)
  ) {
    return null;
  }

  const segments = relative.split(path.sep);
  if (segments.some((segment) => segment.length === 0 || segment.startsWith("."))) {
    return null;
  }
  if (contentTypeFor(candidate) === null) {
    return null;
  }
  return candidate;
}

function sendPlain(res, statusCode, message, extraHeaders = {}) {
  const body = `${message}\n`;
  res.writeHead(statusCode, {
    ...SECURITY_HEADERS,
    ...extraHeaders,
    "Content-Type": "text/plain; charset=utf-8",
    "Content-Length": Buffer.byteLength(body)
  });
  res.end(body);
}

export function createFixtureServer({
  root = WEB_ROOT,
  host = HOST,
  port = DEFAULT_PORT
} = {}) {
  if (host !== HOST) {
    throw new Error("fixture server only binds to 127.0.0.1");
  }
  if (!Number.isInteger(port) || port < 1 || port > 65_535) {
    throw new Error("fixture server port must be an integer 1-65535");
  }

  return createServer(async (request, response) => {
    if (request.method !== "GET" && request.method !== "HEAD") {
      sendPlain(response, 405, "Method not allowed", { Allow: "GET, HEAD" });
      return;
    }

    const filePath = resolveRequestPath(root, request.url ?? "/");
    if (filePath === null) {
      sendPlain(response, 404, "Not found");
      return;
    }

    try {
      const fileStat = await stat(filePath);
      if (fileStat.isDirectory() || !fileStat.isFile()) {
        sendPlain(response, 404, "Not found");
        return;
      }
      const body = await readFile(filePath);
      const contentType = contentTypeFor(filePath);
      if (contentType === null) {
        sendPlain(response, 404, "Not found");
        return;
      }
      response.writeHead(200, {
        ...SECURITY_HEADERS,
        "Content-Type": contentType,
        "Content-Length": body.byteLength
      });
      if (request.method === "HEAD") {
        response.end();
      } else {
        response.end(body);
      }
    } catch {
      sendPlain(response, 404, "Not found");
    }
  });
}

export function parseArgs(argv) {
  let port = DEFAULT_PORT;
  let help = false;

  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === "--help" || argument === "-h") {
      help = true;
      continue;
    }
    if (argument === "--port") {
      const raw = argv[index + 1];
      index += 1;
      const parsed = Number(raw);
      if (!Number.isInteger(parsed) || parsed < 1 || parsed > 65_535) {
        throw new Error("--port must be an integer between 1 and 65535");
      }
      port = parsed;
      continue;
    }
    throw new Error(`unknown argument: ${argument}`);
  }

  return { port, help };
}

const USAGE = [
  "Escalier 004 local synthetic fixture server",
  "",
  "Usage:",
  "  node tools/serve-local.mjs [--port 8642]",
  "",
  "The server binds to 127.0.0.1 only, serves web/ and never opens a browser.",
  "Manual start only. Ctrl+C stops it."
].join("\n");

async function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    console.log(USAGE);
    return;
  }
  const server = createFixtureServer({ port: options.port });
  server.on("error", (error) => {
    console.error(`fixture server error: ${error.message}`);
  });
  server.listen(options.port, HOST, () => {
    console.log(`Serving web/ at http://${HOST}:${options.port}/`);
    console.log("Manual start only. Open the URL yourself; no browser was launched.");
  });
}

const isDirectRun = (() => {
  if (!process.argv[1]) return false;
  try {
    return pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url;
  } catch {
    return false;
  }
})();

if (isDirectRun) {
  await main();
}
