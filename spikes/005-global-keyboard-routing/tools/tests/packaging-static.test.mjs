import test from "node:test";
import assert from "node:assert/strict";
import { cpSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { auditPackaging } from "../packaging-audit.mjs";

const projectRoot = fileURLToPath(new URL("../../", import.meta.url));

function withTamperedScript(mutate) {
  const tempRoot = mkdtempSync(path.join(os.tmpdir(), "escalier-005-packaging-"));
  mkdirSync(path.join(tempRoot, "tools"), { recursive: true });
  const scriptPath = path.join(tempRoot, "tools", "package-app.sh");
  cpSync(path.join(projectRoot, "tools", "package-app.sh"), scriptPath);
  const source = readFileSync(scriptPath, "utf8");
  writeFileSync(scriptPath, mutate(source));
  const result = auditPackaging(tempRoot);
  rmSync(tempRoot, { recursive: true, force: true });
  return result;
}

test("committed packager passes the ad-hoc signing guard", () => {
  assert.deepEqual(auditPackaging(projectRoot).errors, []);
});

test("removing strict verification is rejected", () => {
  const result = withTamperedScript((source) =>
    source.replace('codesign --verify --strict --verbose=2 "$APP"', "codesign --verify \"$APP\"")
  );
  assert.ok(result.errors.some((error) => error.code === "PACKAGER_REQUIRED"));
});

test("adding --deep is rejected", () => {
  const result = withTamperedScript((source) =>
    source.replace('codesign --force --sign - --timestamp=none "$APP"', 'codesign --force --deep --sign - --timestamp=none "$APP"')
  );
  assert.ok(result.errors.some((error) => error.detail === "--deep"));
});

test("adding Gatekeeper assessment is rejected", () => {
  const result = withTamperedScript((source) => `${source}\nspctl --assess "$APP"\n`);
  assert.ok(result.errors.some((error) => error.detail === "spctl"));
});

test("removing the ad-hoc signature assertion is rejected", () => {
  const result = withTamperedScript((source) =>
    source.replace("if ! printf '%s\\n' \"$SIGNATURE_REPORT\" | grep -F 'Signature=adhoc' >/dev/null; then", "if false; then")
  );
  assert.ok(result.errors.some((error) => error.code === "PACKAGER_ADHOC_CHECK"));
});

test("removing failure propagation is rejected", () => {
  const result = withTamperedScript((source) =>
    source.replace("if ! printf '%s\\n' \"$SIGNATURE_REPORT\" | grep -F 'Signature=adhoc' >/dev/null; then", "printf '%s\\n' \"$SIGNATURE_REPORT\" | grep -F 'Signature=adhoc' || true\nif false; then")
  );
  assert.ok(
    result.errors.some(
      (error) => error.code === "PACKAGER_ADHOC_CHECK" || error.code === "PACKAGER_FAILURE_PROPAGATION"
    )
  );
});
