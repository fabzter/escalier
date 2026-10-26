import test from "node:test";
import assert from "node:assert/strict";
import {
  appendFileSync,
  cpSync,
  mkdtempSync,
  readdirSync,
  readFileSync,
  rmSync,
  statSync,
  writeFileSync
} from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { auditNativeProject } from "../native-audit.mjs";

const PROJECT_ROOT = path.resolve(fileURLToPath(new URL("../..", import.meta.url)));

function sourceFiles(root) {
  const files = [];
  const walk = (directory) => {
    for (const name of readdirSync(directory)) {
      const absolute = path.join(directory, name);
      if (statSync(absolute).isDirectory()) {
        walk(absolute);
      } else if (name.endsWith(".swift")) {
        files.push(absolute);
      }
    }
  };
  walk(path.join(root, "Sources"));
  return files;
}

function copyProject() {
  const tempRoot = mkdtempSync(path.join(tmpdir(), "escalier-004-native-audit-"));
  cpSync(path.join(PROJECT_ROOT, "Sources"), path.join(tempRoot, "Sources"), {
    recursive: true
  });
  cpSync(path.join(PROJECT_ROOT, "Resources"), path.join(tempRoot, "Resources"), {
    recursive: true
  });
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

function hasError(result, code) {
  return result.errors.some((error) => error.code === code);
}

test("the checked-in native fixture passes the public-API audit", () => {
  const result = auditNativeProject(PROJECT_ROOT);
  assert.equal(result.ok, true, JSON.stringify(result.errors, null, 2));
  assert.ok(result.scanned.some((file) => file.endsWith("AppMain.swift")));
  assert.ok(result.scanned.some((file) => file.endsWith("Resources/Info.plist")));
});

test("tampered global event tap is rejected", () => {
  const result = withTamperedCopy(
    (tempRoot) => appendFileSync(sourceFiles(tempRoot)[0], "\n// CGEventTapCreate\n"),
    (tempRoot) => auditNativeProject(tempRoot)
  );
  assert.ok(hasError(result, "NATIVE_BANNED_API"));
});

test("tampered NSTask use is rejected", () => {
  const result = withTamperedCopy(
    (tempRoot) => appendFileSync(sourceFiles(tempRoot)[0], "\n// NSTask\n"),
    (tempRoot) => auditNativeProject(tempRoot)
  );
  assert.ok(hasError(result, "NATIVE_BANNED_API"));
});

test("tampered missing sharingType readback is rejected", () => {
  const result = withTamperedCopy(
    (tempRoot) => {
      for (const file of sourceFiles(tempRoot)) {
        const source = readFileSync(file, "utf8");
        writeFileSync(file, source.replaceAll("sharingType", "sharingKind"));
      }
    },
    (tempRoot) => auditNativeProject(tempRoot)
  );
  assert.ok(hasError(result, "NATIVE_MISSING_READBACK"));
});

test("tampered microphone usage description is rejected", () => {
  const result = withTamperedCopy(
    (tempRoot) => {
      const plist = path.join(tempRoot, "Resources", "Info.plist");
      writeFileSync(
        plist,
        readFileSync(plist, "utf8").replace(
          "</dict>",
          "<key>NSMicrophoneUsageDescription</key><string>test</string></dict>"
        )
      );
    },
    (tempRoot) => auditNativeProject(tempRoot)
  );
  assert.ok(hasError(result, "INFO_PLIST_BANNED_USAGE"));
});

test("tampered bundle identifier is rejected", () => {
  const result = withTamperedCopy(
    (tempRoot) => {
      const plist = path.join(tempRoot, "Resources", "Info.plist");
      writeFileSync(
        plist,
        readFileSync(plist, "utf8").replace(
          "test.escalier.spike004.fixture",
          "com.example.not-escalier"
        )
      );
    },
    (tempRoot) => auditNativeProject(tempRoot)
  );
  assert.ok(hasError(result, "INFO_PLIST_IDENTITY"));
});

test("protection wording in native source is rejected", () => {
  const result = withTamperedCopy(
    (tempRoot) => appendFileSync(sourceFiles(tempRoot)[0], "\n// protected marker\n"),
    (tempRoot) => auditNativeProject(tempRoot)
  );
  assert.ok(hasError(result, "NATIVE_PROTECTION_WORD"));
});

test("external URL in native source is rejected", () => {
  const result = withTamperedCopy(
    (tempRoot) => appendFileSync(sourceFiles(tempRoot)[0], "\n// https://example.invalid\n"),
    (tempRoot) => auditNativeProject(tempRoot)
  );
  assert.ok(hasError(result, "NATIVE_EXTERNAL_URL"));
});
