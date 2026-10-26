import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";

const BANNED_SOURCE_PATTERNS = [
  ["CGEventTapCreate", "global event tap"],
  ["CGEvent(", "synthetic event injection"],
  ["NSEvent.addGlobalMonitor", "global event monitor"],
  ["addGlobalMonitorForEvents", "global event monitor"],
  ["AXUIElement", "accessibility automation"],
  ["AXIsProcessTrusted", "accessibility permission check"],
  ["CGPreflightScreenCaptureAccess", "screen-capture permission API"],
  ["CGRequestScreenCaptureAccess", "screen-capture permission API"],
  ["ScreenCaptureKit", "screen capture API"],
  ["SCShareableContent", "screen capture API"],
  ["SCStream", "screen capture API"],
  ["CGWindowListCreateImage", "screen capture API"],
  ["CGDisplayStream", "screen capture API"],
  ["CGDisplayCreateImage", "screen capture API"],
  ["NSAppleScript", "script automation"],
  ["NSTask", "child process"],
  ["Process(", "child process"],
  ["dlopen", "dynamic loading"],
  ["dlsym", "dynamic loading"],
  ["objc_msgSend", "Objective-C runtime bypass"],
  ["URLSession", "network API"],
  ["NWConnection", "network API"],
  ["CFStream", "network API"],
  ["NSPasteboard", "clipboard access"]
];

const REQUIRED_SOURCE_PATTERNS = [
  ["NSWindow.SharingType.none", "sharing-none AppKit mapping"],
  ["NSWindow.SharingType.readOnly", "sharing-readOnly AppKit mapping"],
  ["sharingType", "sharing readback"],
  ["NSPanel", "panel surface"],
  ["nonactivatingPanel", "nonactivating panel configuration"],
  ["ignoresMouseEvents", "click-through configuration"],
  ["activationPolicy", "activation policy switch/readback"],
  ["occlusionState", "occlusion readback"],
  ["frontmostApplication", "frontmost app readback"],
  ["isKeyWindow", "key-window readback"],
  ["isMainWindow", "main-window readback"],
  ["auxiliary-panel", "auxiliary panel role"],
  ["click-through-panel", "click-through panel role"],
  ["NOT RUN IN WORKER", "runtime status label"],
  ["sharing-readOnly", "sharing-readOnly label"]
];

const BANNED_PLIST_KEYS = [
  "NSMicrophoneUsageDescription",
  "NSCameraUsageDescription",
  "NSAppleEventsUsageDescription",
  "NSScreenCaptureUsageDescription"
];

function walk(directory) {
  if (!existsSync(directory)) return [];
  const results = [];
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const absolute = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      results.push(...walk(absolute));
    } else if (entry.name.endsWith(".swift")) {
      results.push(absolute);
    }
  }
  return results;
}

function relativeDisplay(projectRoot, absolute) {
  return path.relative(projectRoot, absolute).split(path.sep).join("/");
}

export function auditNativeProject(projectRoot) {
  const errors = [];
  const scanned = [];
  const sourcesRoot = path.join(projectRoot, "Sources");
  const infoPlistPath = path.join(projectRoot, "Resources", "Info.plist");

  function record(code, file, detail) {
    errors.push({
      code,
      file: relativeDisplay(projectRoot, file),
      detail
    });
  }

  const swiftFiles = walk(sourcesRoot);
  if (swiftFiles.length === 0) {
    record("NATIVE_SOURCE_MISSING", sourcesRoot, "no Swift sources were found");
  }

  let combinedSource = "";
  for (const file of swiftFiles) {
    scanned.push(file);
    const source = readFileSync(file, "utf8");
    combinedSource += `\n${source}`;

    for (const [pattern, detail] of BANNED_SOURCE_PATTERNS) {
      if (source.includes(pattern)) {
        record("NATIVE_BANNED_API", file, `banned ${detail}: ${pattern}`);
      }
    }
    if (/\b(?:protected|unprotected)\b/i.test(source)) {
      record("NATIVE_PROTECTION_WORD", file, "use sharing-none/sharing-readOnly labels");
    }
    if (/(?:https?|wss?|ftp|file):\/\//i.test(source)) {
      record("NATIVE_EXTERNAL_URL", file, "external URL scheme is not allowed");
    }
  }

  for (const [pattern, detail] of REQUIRED_SOURCE_PATTERNS) {
    if (!combinedSource.includes(pattern)) {
      record(
        "NATIVE_MISSING_READBACK",
        sourcesRoot,
        `missing required ${detail}: ${pattern}`
      );
    }
  }

  if (!existsSync(infoPlistPath)) {
    record("INFO_PLIST_MISSING", infoPlistPath, "Info.plist is missing");
  } else {
    scanned.push(infoPlistPath);
    const plist = readFileSync(infoPlistPath, "utf8");

    if (
      !/<key>CFBundleIdentifier<\/key>\s*<string>test\.escalier\.spike004\.fixture<\/string>/.test(
        plist
      )
    ) {
      record("INFO_PLIST_IDENTITY", infoPlistPath, "unexpected CFBundleIdentifier");
    }
    if (!/<key>CFBundleExecutable<\/key>\s*<string>EscalierCaptureFixture<\/string>/.test(plist)) {
      record("INFO_PLIST_IDENTITY", infoPlistPath, "unexpected CFBundleExecutable");
    }
    const nameMatch = plist.match(/<key>CFBundleName<\/key>\s*<string>([^<]*)<\/string>/);
    if (!nameMatch) {
      record("INFO_PLIST_IDENTITY", infoPlistPath, "CFBundleName is missing");
    } else {
      const name = nameMatch[1].toLowerCase();
      if (!name.includes("escalier") || !name.includes("synthetic")) {
        record("INFO_PLIST_IDENTITY", infoPlistPath, "CFBundleName must be clearly Escalier synthetic");
      }
    }
    if (!plist.includes("LSMinimumSystemVersion")) {
      record("INFO_PLIST_IDENTITY", infoPlistPath, "LSMinimumSystemVersion is missing");
    }
    for (const key of BANNED_PLIST_KEYS) {
      if (plist.includes(key)) {
        record("INFO_PLIST_BANNED_USAGE", infoPlistPath, `unexpected usage key ${key}`);
      }
    }
    if (plist.includes("com.apple.security")) {
      record("INFO_PLIST_BANNED_USAGE", infoPlistPath, "security entitlements are out of scope");
    }
  }

  return {
    ok: errors.length === 0,
    errors,
    scanned: scanned.map((file) => relativeDisplay(projectRoot, file))
  };
}
