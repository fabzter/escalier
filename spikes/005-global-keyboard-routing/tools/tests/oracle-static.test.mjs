import test from "node:test";
import assert from "node:assert/strict";
import { appendFileSync, cpSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { auditOracle, auditServer } from "../oracle-audit.mjs";

const projectRoot = fileURLToPath(new URL("../../", import.meta.url));

function withTamperedCopy(mutate) {
  const tempRoot = mkdtempSync(path.join(os.tmpdir(), "escalier-005-oracle-"));
  cpSync(path.join(projectRoot, "web"), path.join(tempRoot, "web"), { recursive: true });
  mkdirSync(path.join(tempRoot, "tools"), { recursive: true });
  cpSync(path.join(projectRoot, "tools", "serve-local.mjs"), path.join(tempRoot, "tools", "serve-local.mjs"));
  mutate(tempRoot);
  const result = auditOracle(tempRoot);
  rmSync(tempRoot, { recursive: true, force: true });
  return result;
}

test("committed oracle passes the static audit", () => {
  const result = auditOracle(projectRoot);
  assert.deepEqual(result.errors, []);
  assert.ok(result.files.some((file) => file.endsWith("index.html")));
  assert.ok(result.files.some((file) => file.endsWith("oracle.mjs")));
});

test("manual server is loopback-only with CSP and no process launch", () => {
  assert.deepEqual(auditServer(projectRoot).errors, []);
});

test("tampered event suppression is rejected", () => {
  const result = withTamperedCopy((root) => {
    appendFileSync(
      path.join(root, "web", "oracle.mjs"),
      "\ndocument.addEventListener('keydown', (event) => event.preventDefault());\n"
    );
  });
  assert.ok(result.errors.some((error) => error.detail.includes("preventDefault")));
});

test("tampered network readback is rejected", () => {
  const result = withTamperedCopy((root) => {
    appendFileSync(
      path.join(root, "web", "oracle.mjs"),
      "\nfetch('synthetic.invalid');\n"
    );
  });
  assert.ok(result.errors.some((error) => error.detail.includes("fetch(")));
});

test("tampered listener options are rejected", () => {
  const result = withTamperedCopy((root) => {
    const jsPath = path.join(root, "web", "oracle.mjs");
    const source = readFileSync(jsPath, "utf8");
    writeFileSync(jsPath, source.replace("{ capture: true, passive: true }", "{ capture: true }"));
  });
  assert.ok(result.errors.some((error) => error.code === "LISTENER_OPTIONS"));
});

test("tampered field identity is rejected", () => {
  const result = withTamperedCopy((root) => {
    const htmlPath = path.join(root, "web", "index.html");
    const source = readFileSync(htmlPath, "utf8");
    writeFileSync(htmlPath, source.replace('id="test-field"', 'id="other-field"'));
  });
  assert.ok(result.errors.some((error) => error.code === "MISSING_COUNTER" || error.code === "MISSING_EDITABLE_FIELD"));
});
