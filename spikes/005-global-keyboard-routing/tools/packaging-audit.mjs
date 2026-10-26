import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

const FORBIDDEN_TOKENS = [
  "--deep",
  "spctl",
  "xattr",
  "tccutil",
  "security ",
  "security-import",
  "notarytool",
  "--options runtime",
  "launchctl",
  "osascript",
  "open ",
  "killall",
  "sudo ",
  "Keychain",
  "trust-settings",
  "quarantine"
];

const REQUIRED_TOKENS = [
  "set -euo pipefail",
  "swift build -c debug --product RoutingFixture",
  "plutil -lint",
  'codesign --force --sign - --timestamp=none "$APP"',
  'codesign --verify --strict --verbose=2 "$APP"',
  "Signature=adhoc",
  "TeamIdentifier",
  "not launched"
];

export function auditPackaging(projectRoot) {
  const errors = [];
  const scriptPath = path.join(projectRoot, "tools", "package-app.sh");
  if (!existsSync(scriptPath)) {
    return {
      errors: [{ code: "MISSING_PACKAGER", file: "tools/package-app.sh", detail: "missing" }]
    };
  }

  const source = readFileSync(scriptPath, "utf8");

  for (const token of FORBIDDEN_TOKENS) {
    if (source.includes(token)) {
      errors.push({
        code: "PACKAGER_FORBIDDEN",
        file: "tools/package-app.sh",
        detail: token.trim()
      });
    }
  }

  for (const token of REQUIRED_TOKENS) {
    if (!source.includes(token)) {
      errors.push({
        code: "PACKAGER_REQUIRED",
        file: "tools/package-app.sh",
        detail: token
      });
    }
  }

  if (!/SIGNATURE_REPORT=.*codesign --display --verbose=4/.test(source)) {
    errors.push({
      code: "PACKAGER_SIGNATURE_INSPECTION",
      file: "tools/package-app.sh",
      detail: "signature inspection is not captured"
    });
  }
  if (!/grep -F 'Signature=adhoc'/.test(source)) {
    errors.push({
      code: "PACKAGER_ADHOC_CHECK",
      file: "tools/package-app.sh",
      detail: "ad-hoc signature check missing"
    });
  }
  if (!/if ! printf .*grep -F 'Signature=adhoc'/.test(source)) {
    errors.push({
      code: "PACKAGER_FAILURE_PROPAGATION",
      file: "tools/package-app.sh",
      detail: "ad-hoc check must fail the script"
    });
  }

  return { errors };
}
