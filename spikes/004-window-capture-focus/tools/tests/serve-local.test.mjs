import test from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  DEFAULT_PORT,
  HOST,
  contentTypeFor,
  createFixtureServer,
  parseArgs,
  resolveRequestPath
} from "../serve-local.mjs";

const WEB_ROOT = path.resolve(
  fileURLToPath(new URL("../../web", import.meta.url))
);

test("fixture server binds loopback only", () => {
  assert.equal(HOST, "127.0.0.1");
  assert.equal(DEFAULT_PORT, 8642);
});

test("parseArgs defaults to a manual loopback port and never opens a browser", () => {
  assert.deepEqual(parseArgs([]), { port: DEFAULT_PORT, help: false });
  assert.deepEqual(parseArgs(["--port", "9000"]), { port: 9000, help: false });
  assert.deepEqual(parseArgs(["--help"]), { port: DEFAULT_PORT, help: true });
  assert.throws(() => parseArgs(["--port", "0"]), /port/);
  assert.throws(() => parseArgs(["--port", "abc"]), /port/);
  assert.throws(() => parseArgs(["--open"]), /unknown/);
});

test("non-loopback host construction is refused before listen", () => {
  assert.throws(() => createFixtureServer({ host: "0.0.0.0" }), /127\.0\.0\.1/);
  assert.throws(() => createFixtureServer({ host: "::1" }), /127\.0\.0\.1/);
});

test("resolves root, files and query strings inside the web root", () => {
  assert.equal(resolveRequestPath(WEB_ROOT, "/"), path.join(WEB_ROOT, "index.html"));
  assert.equal(
    resolveRequestPath(WEB_ROOT, "/sender.html?x=1"),
    path.join(WEB_ROOT, "sender.html")
  );
  assert.equal(
    resolveRequestPath(WEB_ROOT, "/sender.html#section"),
    path.join(WEB_ROOT, "sender.html")
  );
});

test("rejects traversal, encoded traversal, null bytes and dotfiles", () => {
  for (const requestUrl of [
    "/%2e%2e/%2e%2e/etc/passwd",
    "/..%2f..%2fetc%2fpasswd",
    "/%00/index.html",
    "/.hidden",
    "/.git/config"
  ]) {
    assert.equal(resolveRequestPath(WEB_ROOT, requestUrl), null, requestUrl);
  }
});

test("rejects malformed percent encoding and unsupported file types", () => {
  assert.equal(resolveRequestPath(WEB_ROOT, "/%E0%A4%A"), null);
  assert.equal(resolveRequestPath(WEB_ROOT, "/secret.exe"), null);
  assert.equal(resolveRequestPath(WEB_ROOT, "/data.json"), null);
});

test("serves only the expected local MIME types", () => {
  assert.equal(contentTypeFor("index.html"), "text/html; charset=utf-8");
  assert.equal(contentTypeFor("sender.mjs"), "text/javascript; charset=utf-8");
  assert.equal(contentTypeFor("app.css"), "text/css; charset=utf-8");
  assert.equal(contentTypeFor("notes.txt"), "text/plain; charset=utf-8");
  assert.equal(contentTypeFor("image.svg"), "image/svg+xml");
  assert.equal(contentTypeFor("unknown.bin"), null);
});
