import test from "node:test";
import assert from "node:assert/strict";
import {
  appendFileSync,
  cpSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync
} from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { auditWebProject } from "../web-audit.mjs";

const PROJECT_ROOT = path.resolve(fileURLToPath(new URL("../..", import.meta.url)));

function copyProject() {
  const tempRoot = mkdtempSync(path.join(tmpdir(), "escalier-004-web-audit-"));
  for (const entry of ["web", "Sources", "Resources"]) {
    cpSync(path.join(PROJECT_ROOT, entry), path.join(tempRoot, entry), {
      recursive: true
    });
  }
  mkdirSync(path.join(tempRoot, "tools"), { recursive: true });
  cpSync(
    path.join(PROJECT_ROOT, "tools", "serve-local.mjs"),
    path.join(tempRoot, "tools", "serve-local.mjs")
  );
  return tempRoot;
}

function withTamperedCopy(mutator, callback) {
  const tempRoot = copyProject();
  try {
    mutator(tempRoot);
    return callback(tempRoot);
  } finally {
    rmSync(tempRoot, { recursive: true, force: true });
  }
}

function overwrite(tempRoot, relativePath, transform) {
  const absolute = path.join(tempRoot, relativePath);
  writeFileSync(absolute, transform(readFileSync(absolute, "utf8")));
}

function append(tempRoot, relativePath, text) {
  appendFileSync(path.join(tempRoot, relativePath), text);
}

function hasError(result, code) {
  return result.errors.some((error) => error.code === code);
}

test("the checked-in browser fixture passes the static audit", () => {
  const result = auditWebProject(PROJECT_ROOT);
  assert.equal(result.ok, true, JSON.stringify(result.errors, null, 2));
  assert.ok(result.scanned.some((file) => file.endsWith("web/index.html")));
  assert.ok(result.scanned.some((file) => file.endsWith("web/sender.html")));
  assert.ok(result.scanned.some((file) => file.endsWith("web/receiver.html")));
  assert.ok(result.scanned.some((file) => file.endsWith("tools/serve-local.mjs")));
});

test("tampered external URL is rejected", () => {
  const result = withTamperedCopy(
    (tempRoot) => append(tempRoot, "web/index.html", '\n<img src="https://example.invalid/x.png">\n'),
    (tempRoot) => auditWebProject(tempRoot)
  );
  assert.equal(result.ok, false);
  assert.ok(hasError(result, "EXTERNAL_URL"));
});

test("tampered getUserMedia request is rejected", () => {
  const result = withTamperedCopy(
    (tempRoot) => append(tempRoot, "web/sender.mjs", "\nnavigator.mediaDevices.getUserMedia({ audio: true });\n"),
    (tempRoot) => auditWebProject(tempRoot)
  );
  assert.ok(hasError(result, "GET_USER_MEDIA"));
});

test("tampered audio request is rejected", () => {
  const result = withTamperedCopy(
    (tempRoot) => append(tempRoot, "web/sender.mjs", "\nconst forbidden = { audio: true };\n"),
    (tempRoot) => auditWebProject(tempRoot)
  );
  assert.ok(hasError(result, "AUDIO_REQUEST"));
});

test("tampered STUN/TURN configuration is rejected", () => {
  const result = withTamperedCopy(
    (tempRoot) =>
      overwrite(tempRoot, "web/receiver.mjs", (source) =>
        source.replace(
          "iceServers: []",
          'iceServers: [{ urls: "stun:example.invalid" }]'
        )
      ),
    (tempRoot) => auditWebProject(tempRoot)
  );
  assert.ok(hasError(result, "STUN_TURN"));
  assert.ok(hasError(result, "ICE_SERVERS"));
});

test("tampered top-level getDisplayMedia call is rejected as autostart/outside gesture", () => {
  const result = withTamperedCopy(
    (tempRoot) =>
      append(
        tempRoot,
        "web/sender.mjs",
        "\nnavigator.mediaDevices.getDisplayMedia({ video: true, audio: false });\n"
      ),
    (tempRoot) => auditWebProject(tempRoot)
  );
  assert.ok(hasError(result, "DISPLAY_CAPTURE_OUTSIDE_GESTURE"));
});

test("tampered missing user-activation check is rejected", () => {
  const result = withTamperedCopy(
    (tempRoot) =>
      overwrite(tempRoot, "web/sender.mjs", (source) =>
        source.replaceAll("userActivation", "removedActivation")
      ),
    (tempRoot) => auditWebProject(tempRoot)
  );
  assert.ok(hasError(result, "MISSING_USER_ACTIVATION"));
});

test("tampered fetch call is rejected", () => {
  const result = withTamperedCopy(
    (tempRoot) => append(tempRoot, "web/receiver.mjs", '\nfetch("./local.json");\n'),
    (tempRoot) => auditWebProject(tempRoot)
  );
  assert.ok(hasError(result, "NETWORK_API"));
});

test("tampered canvas export is rejected", () => {
  const result = withTamperedCopy(
    (tempRoot) =>
      append(tempRoot, "web/receiver.mjs", '\ndocument.querySelector("canvas")?.toDataURL();\n'),
    (tempRoot) => auditWebProject(tempRoot)
  );
  assert.ok(hasError(result, "PERSISTENCE_API"));
});

test("tampered inline script is rejected", () => {
  const result = withTamperedCopy(
    (tempRoot) => append(tempRoot, "web/index.html", '<script>console.log("inline")</script>\n'),
    (tempRoot) => auditWebProject(tempRoot)
  );
  assert.ok(hasError(result, "INLINE_SCRIPT"));
});

test("tampered missing CSP is rejected", () => {
  const result = withTamperedCopy(
    (tempRoot) =>
      overwrite(tempRoot, "web/index.html", (source) =>
        source.replace(/<meta http-equiv="Content-Security-Policy"[^>]*>\s*/g, "")
      ),
    (tempRoot) => auditWebProject(tempRoot)
  );
  assert.ok(hasError(result, "MISSING_CSP"));
});

test("tampered autoplay attribute is rejected", () => {
  const result = withTamperedCopy(
    (tempRoot) =>
      overwrite(tempRoot, "web/receiver.html", (source) =>
        source.replace('<video id="receiver-video"', '<video autoplay id="receiver-video"')
      ),
    (tempRoot) => auditWebProject(tempRoot)
  );
  assert.ok(hasError(result, "NO_AUTOPLAY"));
});

test("a sender preview inserted into the receiver page is rejected", () => {
  const result = withTamperedCopy(
    (tempRoot) =>
      append(tempRoot, "web/receiver.html", '<video id="sender-preview"></video>\n'),
    (tempRoot) => auditWebProject(tempRoot)
  );
  assert.ok(hasError(result, "RECEIVER_PREVIEW_CONFUSION"));
});

test("tampered server bind address is rejected", () => {
  const result = withTamperedCopy(
    (tempRoot) =>
      overwrite(tempRoot, "tools/serve-local.mjs", (source) =>
        source.replace('export const HOST = "127.0.0.1";', 'export const HOST = "0.0.0.0";')
      ),
    (tempRoot) => auditWebProject(tempRoot)
  );
  assert.ok(hasError(result, "SERVER_BIND"));
});

test("tampered server autostart is rejected", () => {
  const result = withTamperedCopy(
    (tempRoot) => append(tempRoot, "tools/serve-local.mjs", "\nmain();\n"),
    (tempRoot) => auditWebProject(tempRoot)
  );
  assert.ok(hasError(result, "SERVER_AUTOSTART"));
});

test("tampered server child_process import is rejected", () => {
  const result = withTamperedCopy(
    (tempRoot) =>
      append(tempRoot, "tools/serve-local.mjs", '\nimport { exec } from "node:child_process";\n'),
    (tempRoot) => auditWebProject(tempRoot)
  );
  assert.ok(hasError(result, "SERVER_CHILD_PROCESS"));
});

test("tampered server CSP drift is rejected", () => {
  const result = withTamperedCopy(
    (tempRoot) =>
      overwrite(tempRoot, "tools/serve-local.mjs", (source) =>
        source.replace("default-src 'none';", "default-src 'self';")
      ),
    (tempRoot) => auditWebProject(tempRoot)
  );
  assert.ok(hasError(result, "CSP_MISMATCH"));
});

test("tampered missing receiver getStats is rejected", () => {
  const result = withTamperedCopy(
    (tempRoot) =>
      overwrite(tempRoot, "web/receiver.mjs", (source) =>
        source.replaceAll("getStats", "getStatistics")
      ),
    (tempRoot) => auditWebProject(tempRoot)
  );
  assert.ok(hasError(result, "MISSING_GETSTATS"));
});

test("tampered missing ontrack is rejected", () => {
  const result = withTamperedCopy(
    (tempRoot) =>
      overwrite(tempRoot, "web/receiver.mjs", (source) =>
        source.replace("ontrack", "onstream")
      ),
    (tempRoot) => auditWebProject(tempRoot)
  );
  assert.ok(hasError(result, "MISSING_ONTRACK"));
});
