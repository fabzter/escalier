import path from "node:path";
import { fileURLToPath } from "node:url";

import { auditNativeProject } from "./native-audit.mjs";
import { auditWebProject } from "./web-audit.mjs";

const PROJECT_ROOT = path.resolve(fileURLToPath(new URL("..", import.meta.url)));

function printAudit(label, result) {
  console.log(`${label}: ${result.ok ? "PASS" : "FAIL"} (${result.scanned.length} files scanned)`);
  for (const error of result.errors) {
    console.log(`  ${error.code} ${error.file}: ${error.detail}`);
  }
}

const web = auditWebProject(PROJECT_ROOT);
const native = auditNativeProject(PROJECT_ROOT);

printAudit("WEB AUDIT", web);
printAudit("NATIVE AUDIT", native);

if (!web.ok || !native.ok) {
  process.exitCode = 1;
} else {
  console.log("STATIC VALIDATION PASS — no app/browser/server was launched and no capture was started.");
}
