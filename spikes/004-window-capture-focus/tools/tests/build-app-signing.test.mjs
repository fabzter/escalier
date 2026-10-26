import test from "node:test";
import assert from "node:assert/strict";
import {
  chmodSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync
} from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const PROJECT_ROOT = path.resolve(fileURLToPath(new URL("../..", import.meta.url)));
const BUILD_SCRIPT = path.join(PROJECT_ROOT, "tools", "build-app.sh");

function runWithFakeCodesign(stubBody) {
  const tempRoot = mkdtempSync(path.join(tmpdir(), "escalier-004-signing-test-"));
  const stubDirectory = path.join(tempRoot, "bin");
  const scratch = path.join(tempRoot, "scratch");
  mkdirSync(stubDirectory, { recursive: true });
  const stub = path.join(stubDirectory, "codesign");
  writeFileSync(stub, `#!/bin/sh\n${stubBody}\n`, { mode: 0o755 });
  chmodSync(stub, 0o755);

  const result = spawnSync("bash", [BUILD_SCRIPT], {
    cwd: PROJECT_ROOT,
    encoding: "utf8",
    env: {
      ...process.env,
      PATH: `${stubDirectory}:${process.env.PATH}`,
      SCRATCH_PATH: scratch
    }
  });
  return { result, tempRoot };
}

test("build script pins ad-hoc signing and strict verification commands", () => {
  const script = readFileSync(BUILD_SCRIPT, "utf8");
  assert.match(script, /codesign --force --sign - --timestamp=none "\$APP"/);
  assert.match(script, /codesign --verify --strict --verbose=2 "\$APP"/);
  assert.doesNotMatch(script, /--deep/);
});

test("signing failure propagates as a nonzero build result", () => {
  const { result, tempRoot } = runWithFakeCodesign(
    'echo "fake codesign sign failure" >&2\nexit 42'
  );
  try {
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /fake codesign sign failure/);
  } finally {
    rmSync(tempRoot, { recursive: true, force: true });
  }
});

test("verification failure propagates as a nonzero build result", () => {
  const { result, tempRoot } = runWithFakeCodesign(
    'if [ "$1" = "--verify" ]; then echo "fake codesign verify failure" >&2; exit 43; fi\nexit 0'
  );
  try {
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /fake codesign verify failure/);
  } finally {
    rmSync(tempRoot, { recursive: true, force: true });
  }
});
