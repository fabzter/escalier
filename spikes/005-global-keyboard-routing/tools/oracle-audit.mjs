import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";

const TEXT_EXTENSIONS = new Set([".html", ".mjs", ".js", ".css"]);

const FORBIDDEN_TOKENS = [
  "preventDefault",
  "stopPropagation",
  "stopImmediatePropagation",
  "returnValue",
  "fetch(",
  "XMLHttpRequest",
  "WebSocket",
  "sendBeacon",
  "localStorage",
  "sessionStorage",
  "indexedDB",
  "console.",
  "http://",
  "https://",
  "eval(",
  "new Function",
  "document.cookie",
  "clipboard.",
  "navigator.sendBeacon"
];

const REQUIRED_COUNTER_IDS = [
  "keydown-total",
  "keyup-total",
  "selected-down-K",
  "selected-up-K",
  "selected-down-Escape",
  "selected-up-Escape",
  "selected-down-A",
  "selected-up-A",
  "selected-down-Backspace",
  "selected-up-Backspace",
  "selected-down-Enter",
  "selected-up-Enter",
  "selected-down-Tab",
  "selected-up-Tab",
  "selected-down-other",
  "selected-up-other",
  "modifier-down",
  "modifier-up",
  "beforeinput-total",
  "input-total",
  "compositionstart-total",
  "compositionend-total",
  "focus-total",
  "blur-total",
  "visible-total",
  "hidden-total",
  "scroll-total"
];

const REQUIRED_PHRASES = [
  "positive control",
  "same chord",
  "same profile",
  "same page",
  "OFF",
  "focused visible field",
  "INVALID",
  "Reset counters"
];

function walk(directory) {
  if (!existsSync(directory)) return [];
  const results = [];
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const full = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      results.push(...walk(full));
    } else if (entry.isFile() && TEXT_EXTENSIONS.has(path.extname(entry.name).toLowerCase())) {
      results.push(full);
    }
  }
  return results;
}

export function auditOracle(projectRoot) {
  const errors = [];
  const webRoot = path.join(projectRoot, "web");
  const files = walk(webRoot);

  function fail(code, file, detail) {
    errors.push({ code, file: path.relative(projectRoot, file), detail });
  }

  const htmlPath = path.join(webRoot, "index.html");
  const jsPath = path.join(webRoot, "oracle.mjs");
  if (!existsSync(htmlPath)) {
    fail("MISSING_HTML", htmlPath, "web/index.html is required");
  }
  if (!existsSync(jsPath)) {
    fail("MISSING_JS", jsPath, "web/oracle.mjs is required");
  }
  if (files.length === 0) {
    fail("NO_WEB_FILES", webRoot, "no web files found");
  }

  const contents = new Map();
  for (const file of files) {
    contents.set(file, readFileSync(file, "utf8"));
  }
  const combined = [...contents.values()].join("\n");

  for (const token of FORBIDDEN_TOKENS) {
    if (combined.includes(token)) {
      fail("FORBIDDEN_TOKEN", webRoot, `found ${token}`);
    }
  }

  for (const id of REQUIRED_COUNTER_IDS) {
    if (!combined.includes(`id="${id}"`)) {
      fail("MISSING_COUNTER", htmlPath, `missing id="${id}"`);
    }
  }

  for (const phrase of REQUIRED_PHRASES) {
    if (!combined.includes(phrase)) {
      fail("MISSING_CONTROL_PHRASE", htmlPath, `missing phrase: ${phrase}`);
    }
  }

  const html = contents.get(htmlPath) ?? "";
  const js = contents.get(jsPath) ?? "";

  if (!/<textarea[^>]*id="test-field"/.test(html) && !/<input[^>]*id="test-field"/.test(html)) {
    fail("MISSING_EDITABLE_FIELD", htmlPath, "test-field must be editable");
  }
  if (/<textarea[^>]*\b(disabled|readonly)\b/i.test(html) || /<input[^>]*\b(disabled|readonly)\b/i.test(html)) {
    fail("FIELD_NOT_EDITABLE", htmlPath, "test field carries a disabling attribute");
  }
  if (/\son[a-z]+\s*=/i.test(html)) {
    fail("INLINE_HANDLER", htmlPath, "inline event handler found");
  }

  const scriptTags = [...html.matchAll(/<script\b[^>]*>/gi)].map((match) => match[0]);
  if (scriptTags.length !== 1 || !/src="oracle\.mjs"/.test(scriptTags[0])) {
    fail("SCRIPT_SHAPE", htmlPath, "exactly one module script, src=oracle.mjs, is required");
  }
  if (!/type="module"/.test(scriptTags[0] ?? "")) {
    fail("SCRIPT_NOT_MODULE", htmlPath, "oracle script must be a module");
  }
  if (!html.includes("default-src 'none'") || !html.includes("connect-src 'none'")) {
    fail("CSP_MISSING", htmlPath, "restrictive content security policy missing");
  }

  if (!combined.includes("{ capture: true, passive: true }")) {
    fail("LISTENER_OPTIONS", jsPath, "literal capture+passive listener options are required");
  }

  const jsLines = js.split("\n");
  jsLines.forEach((line, index) => {
    if (line.includes("addEventListener(") && !line.includes("LISTENER_OPTIONS")) {
      fail("UNPINNED_LISTENER", jsPath, `line ${index + 1} does not use LISTENER_OPTIONS`);
    }
  });
  if (!js.includes("LISTENER_OPTIONS")) {
    fail("MISSING_LISTENER_HELPER", jsPath, "listener options constant is missing");
  }

  if (!/SELECTED_KEYS/.test(js) || !/MODIFIER_KEYS/.test(js)) {
    fail("COUNTER_SEPARATION", jsPath, "selected keys and modifiers must be counted separately");
  }
  if (!/selected-down-\$\{selectedLabel\(event\)\}/.test(js)) {
    fail("SELECTED_KEY_COUNTER", jsPath, "selected non-modifier key counters are not wired");
  }
  if (!/modifier-down/.test(js) || !/modifier-up/.test(js)) {
    fail("MODIFIER_COUNTER", jsPath, "modifier counters are not wired");
  }

  if (!/document\.hasFocus\(\)/.test(js) || !/document\.visibilityState/.test(js) || !/document\.activeElement === field/.test(js)) {
    fail("PRECONDITIONS", jsPath, "focus, visibility and active-element preconditions are required");
  }

  if (!/keydown/.test(js) || !/keyup/.test(js) || !/beforeinput/.test(js) || !/input/.test(js)) {
    fail("MISSING_KEY_COUNTERS", jsPath, "key and input counters are required");
  }
  if (!/compositionstart/.test(js) || !/compositionend/.test(js)) {
    fail("MISSING_COMPOSITION", jsPath, "composition counters are required");
  }
  if (!/visibilitychange/.test(js) || !/scroll/.test(js)) {
    fail("MISSING_VISIBILITY_SCROLL", jsPath, "visibility and scroll counters are required");
  }

  return { errors, files: files.map((file) => path.relative(projectRoot, file)) };
}

export function auditServer(projectRoot) {
  const errors = [];
  const serverPath = path.join(projectRoot, "tools", "serve-local.mjs");
  if (!existsSync(serverPath)) {
    return { errors: [{ code: "MISSING_SERVER", file: "tools/serve-local.mjs", detail: "missing" }] };
  }
  const source = readFileSync(serverPath, "utf8");
  for (const token of ["child_process", "exec(", "spawn(", "https://", "http://"]) {
    if (source.includes(token)) {
      errors.push({ code: "SERVER_FORBIDDEN", file: "tools/serve-local.mjs", detail: token });
    }
  }
  if (!source.includes("127.0.0.1")) {
    errors.push({ code: "SERVER_BIND", file: "tools/serve-local.mjs", detail: "must bind loopback" });
  }
  if (!source.includes("Content-Security-Policy")) {
    errors.push({ code: "SERVER_CSP", file: "tools/serve-local.mjs", detail: "CSP header missing" });
  }
  return { errors };
}
