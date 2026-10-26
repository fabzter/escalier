import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";

const TEXT_EXTENSIONS = new Set([".html", ".mjs", ".js", ".css", ".txt", ".svg"]);
const REQUIRED_CSP_TOKENS = [
  "default-src 'none'",
  "script-src 'self'",
  "connect-src 'none'",
  "form-action 'none'",
  "base-uri 'none'",
  "media-src 'self'"
];

function walk(directory) {
  if (!existsSync(directory)) return [];
  const results = [];
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    if (entry.name === "tests") continue;
    const absolute = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      results.push(...walk(absolute));
    } else {
      results.push(absolute);
    }
  }
  return results;
}

function normalizeSpace(value) {
  return value.replace(/\s+/g, " ").trim();
}

function relativeDisplay(projectRoot, absolute) {
  return path.relative(projectRoot, absolute).split(path.sep).join("/");
}

function hasId(source, id) {
  return source.includes(`id="${id}"`);
}

export function auditWebProject(projectRoot) {
  const errors = [];
  const scanned = [];
  const webRoot = path.join(projectRoot, "web");
  const serverPath = path.join(projectRoot, "tools", "serve-local.mjs");

  function record(code, file, detail) {
    errors.push({
      code,
      file: relativeDisplay(projectRoot, file),
      detail
    });
  }

  const webFiles = walk(webRoot).filter((file) =>
    TEXT_EXTENSIONS.has(path.extname(file).toLowerCase())
  );
  const fileContents = new Map();
  for (const file of webFiles) {
    scanned.push(file);
    fileContents.set(file, readFileSync(file, "utf8"));
  }

  if (!existsSync(serverPath)) {
    record("SERVER_MISSING", serverPath, "tools/serve-local.mjs is missing");
  } else {
    scanned.push(serverPath);
    fileContents.set(serverPath, readFileSync(serverPath, "utf8"));
  }

  const serverText = fileContents.get(serverPath) ?? "";
  const serverCspMatch = serverText.match(/export const CSP_POLICY\s*=\s*"([^"]+)";/);
  const serverCsp = serverCspMatch ? normalizeSpace(serverCspMatch[1]) : null;

  // Shared web-content rules. The server tool is audited separately below.
  for (const file of webFiles) {
    const source = fileContents.get(file);
    if (/(?:https?|wss?|ftp|file):\/\//i.test(source)) {
      record("EXTERNAL_URL", file, "external URL scheme is not allowed");
    }
    if (/\b(?:stun|turn):/i.test(source)) {
      record("STUN_TURN", file, "STUN/TURN URL is not allowed");
    }
    if (/\b(?:protected|unprotected)\b/i.test(source)) {
      record("PROTECTION_WORD", file, "use sharing-none/sharing-readOnly labels");
    }
  }

  // HTML rules.
  for (const file of webFiles.filter((candidate) => path.extname(candidate) === ".html")) {
    const source = fileContents.get(file);
    const name = path.basename(file);

    if (!/<!doctype html>/i.test(source)) {
      record("HTML_DOCTYPE", file, "missing doctype");
    }

    const cspMatches = [
      ...source.matchAll(
        /<meta\s+http-equiv="Content-Security-Policy"\s+content="([^"]*)"\s*\/?>/gi
      )
    ];
    if (cspMatches.length === 0) {
      record("MISSING_CSP", file, "Content-Security-Policy meta tag is required");
    } else if (cspMatches.length > 1) {
      record("DUPLICATE_CSP", file, "only one CSP meta tag is allowed");
    } else {
      const htmlCsp = normalizeSpace(cspMatches[0][1]);
      if (serverCsp === null) {
        record("SERVER_CSP_MISSING", serverPath, "server CSP constant is missing");
      } else if (htmlCsp !== serverCsp) {
        record("CSP_MISMATCH", file, "HTML CSP differs from the server header policy");
      }
      for (const token of REQUIRED_CSP_TOKENS) {
        if (!htmlCsp.includes(token)) {
          record("CSP_WEAK", file, `CSP is missing ${token}`);
        }
      }
      if (/script-src[^;]*(?:'unsafe-inline'|'unsafe-eval')/i.test(htmlCsp)) {
        record("CSP_WEAK", file, "script-src must not allow unsafe code");
      }
    }

    const scriptPattern = /<script\b([^>]*)>([\s\S]*?)<\/script>/gi;
    for (const match of source.matchAll(scriptPattern)) {
      const attributes = match[1];
      const body = match[2];
      if (!/\bsrc\s*=/.test(attributes)) {
        record("INLINE_SCRIPT", file, "inline script tags are not allowed");
      }
      if (body.trim().length > 0) {
        record("INLINE_SCRIPT", file, "script body must be empty");
      }
      if (!/\btype="module"/.test(attributes)) {
        record("SCRIPT_NOT_MODULE", file, "scripts must be type=module");
      }
      const srcMatch = attributes.match(/\bsrc="([^"]+)"/);
      if (srcMatch) {
        const src = srcMatch[1];
        if (!src.startsWith("./")) {
          record("SCRIPT_SRC", file, `script src must be relative: ${src}`);
        } else {
          const resolved = path.resolve(webRoot, src.slice(2));
          if (!existsSync(resolved)) {
            record("SCRIPT_NOT_FOUND", file, `script target is missing: ${src}`);
          }
        }
      }
    }

    if (/\s+on[a-zA-Z]+\s*=/.test(source)) {
      record("INLINE_EVENT_HANDLER", file, "inline event handlers are not allowed");
    }
    if (/<style\b/i.test(source) || /\s+style\s*=/.test(source)) {
      record("INLINE_STYLE", file, "inline styles are not allowed");
    }
    if (/<audio\b/i.test(source)) {
      record("AUDIO_REQUEST", file, "audio elements are not allowed");
    }
    if (/<form\b/i.test(source)) {
      record("FORM_ACTION", file, "forms are not allowed");
    }
    if (/<base\b/i.test(source)) {
      record("BASE_TAG", file, "base tags are not allowed");
    }
    if (/<iframe\b/i.test(source)) {
      record("IFRAME", file, "iframes are not allowed");
    }
    if (/<object\b|<embed\b/i.test(source)) {
      record("EMBED", file, "embedded content is not allowed");
    }
    if (/<meta\s+http-equiv="refresh"/i.test(source)) {
      record("META_REFRESH", file, "meta refresh is not allowed");
    }
    if (/\s+href="\/\//i.test(source) || /\s+src="\/\//i.test(source)) {
      record("EXTERNAL_URL", file, "protocol-relative URLs are not allowed");
    }

    for (const match of source.matchAll(/<video\b([^>]*)>/gi)) {
      const attributes = match[1];
      if (/\bautoplay\b/i.test(attributes)) {
        record("NO_AUTOPLAY", file, "receiver/sender video must not autoplay");
      }
      if (!/\bmuted\b/.test(attributes) || !/\bplaysinline\b/.test(attributes)) {
        record("VIDEO_ATTRIBUTES", file, "video needs muted and playsinline");
      }
    }

    if (name === "index.html") {
      for (const id of [
        "focus-log",
        "snapshot-focus",
        "clear-focus-log",
        "underlay-button",
        "underlay-count"
      ]) {
        if (!hasId(source, id)) record("MISSING_INDEX_CONTROLS", file, `missing id="${id}"`);
      }
      if (hasId(source, "receiver-video") || hasId(source, "sender-preview")) {
        record("INDEX_PREVIEW_CONFUSION", file, "index must not embed capture previews");
      }
    }

    if (name === "sender.html") {
      for (const id of [
        "start-capture",
        "stop-capture",
        "sender-preview",
        "sender-status",
        "focus-log",
        "snapshot-focus"
      ]) {
        if (!hasId(source, id)) record("MISSING_SENDER_CONTROLS", file, `missing id="${id}"`);
      }
      if (hasId(source, "receiver-video")) {
        record("RECEIVER_PREVIEW_CONFUSION", file, "sender page must not contain the receiver video");
      }
    }

    if (name === "receiver.html") {
      for (const id of [
        "receiver-video",
        "receiver-status",
        "receiver-stats",
        "receiver-transport-log",
        "refresh-stats",
        "evidence-status",
        "evidence-summary",
        "roi-x",
        "roi-y",
        "roi-w",
        "roi-h",
        "sample-roi",
        "roi-label",
        "roi-stats",
        "roi-log",
        "roi-canvas",
        "focus-log",
        "snapshot-focus",
        "reset-receiver",
        "request-offer"
      ]) {
        if (!hasId(source, id)) record("MISSING_RECEIVER_CONTROLS", file, `missing id="${id}"`);
      }
      if (hasId(source, "sender-preview") || hasId(source, "start-capture")) {
        record("RECEIVER_PREVIEW_CONFUSION", file, "receiver page contains sender capture/preview UI");
      }
    }
  }

  // JavaScript rules.
  const jsFiles = webFiles.filter((file) => path.extname(file) === ".mjs");
  let displayCaptureCount = 0;
  for (const file of jsFiles) {
    const source = fileContents.get(file);
    const name = path.basename(file);
    const count = (source.match(/getDisplayMedia\s*\(/g) ?? []).length;
    displayCaptureCount += count;

    if (/getUserMedia\s*\(/.test(source)) {
      record("GET_USER_MEDIA", file, "getUserMedia is not allowed");
    }
    if (/\baudio\s*:\s*true\b/.test(source)) {
      record("AUDIO_REQUEST", file, "audio:true is not allowed");
    }
    if (/\bnew\s+Audio\b|\bAudioContext\b/.test(source)) {
      record("AUDIO_REQUEST", file, "audio playback/processing is not allowed");
    }
    if (/\bMediaRecorder\b|\bcaptureStream\s*\(/.test(source)) {
      record("MEDIA_RECORDER", file, "recording APIs are not allowed");
    }
    if (
      /\bfetch\s*\(|\bXMLHttpRequest\b|\bWebSocket\b|\bEventSource\b|\bsendBeacon\s*\(|\bnavigator\.serviceWorker\b|\bimportScripts\s*\(/i.test(
        source
      )
    ) {
      record("NETWORK_API", file, "network APIs are not allowed");
    }
    if (
      /\blocalStorage\b|\bsessionStorage\b|\bindexedDB\b|\bdocument\.cookie\b|\btoDataURL\s*\(|\btoBlob\s*\(|\bcreateObjectURL\s*\(|\bFileReader\b|\bshowSaveFilePicker\b|\bshowOpenFilePicker\b|\bdownload\s*=/i.test(
        source
      )
    ) {
      record("PERSISTENCE_API", file, "persistence/export APIs are not allowed");
    }
    if (/\bsetTimeout\s*\(|\bsetInterval\s*\(/.test(source)) {
      record("AUTOSTART_TIMER", file, "timers are not allowed in the capture fixture");
    }
    for (const match of source.matchAll(/iceServers\s*:\s*\[([^\]]*)\]/g)) {
      if (match[1].trim().length > 0) {
        record("ICE_SERVERS", file, "iceServers must be empty");
      }
    }
    if (/(?:https?|wss?|ftp|file):\/\//i.test(source)) {
      record("EXTERNAL_URL", file, "external URL scheme is not allowed");
    }
    if (/\b(?:stun|turn):/i.test(source)) {
      record("STUN_TURN", file, "STUN/TURN URL is not allowed");
    }
    if (
      !/\bnew RTCPeerConnection\(\s*\{\s*iceServers:\s*\[\s*\]\s*\}\s*\)/.test(source) &&
      (name === "sender.mjs" || name === "receiver.mjs")
    ) {
      record("ICE_SERVERS", file, "RTCPeerConnection must use an empty iceServers list");
    }

    if (name === "sender.mjs") {
      if (count !== 1) {
        record("DISPLAY_CAPTURE_OUTSIDE_GESTURE", file, "exactly one getDisplayMedia call is required");
      }
      if (
        !/export async function startUserChosenCapture\(\)\s*\{[\s\S]*?getDisplayMedia\(\s*\{\s*video:\s*true,\s*audio:\s*false\s*\}\s*\)[\s\S]*?\n\}/.test(
          source
        )
      ) {
        record(
          "DISPLAY_CAPTURE_OUTSIDE_GESTURE",
          file,
          "getDisplayMedia must be inside the click-triggered startUserChosenCapture function"
        );
      }
      if (!/isSecureContext/.test(source)) {
        record("MISSING_SECURE_CONTEXT", file, "secure context check is required");
      }
      if (!/navigator\.userActivation\??\.isActive/.test(source)) {
        record("MISSING_USER_ACTIVATION", file, "transient user activation check is required");
      }
      if (!/\bguardCaptureRequest\s*\(/.test(source)) {
        record("MISSING_CAPTURE_GUARD", file, "capture preflight guard is required");
      }
      if (!/\binspectVideoOnlyStream\s*\(/.test(source)) {
        record("MISSING_VIDEO_ONLY_CHECK", file, "video-only stream check is required");
      }
      if (!/getElementById\("start-capture"\)[\s\S]{0,240}addEventListener\("click"/.test(source)) {
        record("MISSING_CLICK_HANDLER", file, "start capture must be a click handler");
      }
      if (!/getElementById\("sender-preview"\)/.test(source) || !/srcObject\s*=/.test(source)) {
        record("MISSING_SENDER_PREVIEW", file, "labeled sender preview element is required");
      }
      if (!/addEventListener\(\s*"ended"/.test(source)) {
        record("MISSING_TRACK_ENDED", file, "local track ended handler is required");
      }
      if (!/\baddTrack\s*\(/.test(source)) {
        record("MISSING_ADD_TRACK", file, "peer connection addTrack call is required");
      }
      if (!/\battachFocusLog\s*\(/.test(source)) {
        record("MISSING_FOCUS_LOG", file, "focus log attachment is required");
      }
      if (/receiver-video/.test(source)) {
        record("RECEIVER_PREVIEW_CONFUSION", file, "sender must not reference receiver-video");
      }
    }

    if (name === "receiver.mjs") {
      if (count !== 0) {
        record("DISPLAY_CAPTURE_WRONG_FILE", file, "receiver must not call getDisplayMedia");
      }
      if (!/\bontrack\s*=/.test(source)) {
        record("MISSING_ONTRACK", file, "receiver video must come from pc.ontrack");
      }
      if (!/\bnew MediaStream\s*\(/.test(source) || !/srcObject\s*=/.test(source)) {
        record("MISSING_RECEIVER_STREAM", file, "receiver stream must be built from the received track");
      }
      if (!/\bgetStats\s*\(/.test(source)) {
        record("MISSING_GETSTATS", file, "receiver getStats call is required");
      }
      if (!/\bextractInboundVideoStats\s*\(/.test(source)) {
        record("MISSING_INBOUND_STATS", file, "inbound video stats extraction is required");
      }
      if (
        !/framesDecoded/.test(source) ||
        !/bytesReceived/.test(source) ||
        !/timestamp/.test(source)
      ) {
        record(
          "MISSING_TRANSPORT_FIELDS",
          file,
          "framesDecoded/bytesReceived/timestamp must be recorded"
        );
      }
      if (!/\bgetImageData\s*\(/.test(source) || !/\bdrawImage\s*\(/.test(source)) {
        record("MISSING_ROI_SAMPLING", file, "receiver ROI sampling is required");
      }
      if (!/\battachFocusLog\s*\(/.test(source)) {
        record("MISSING_FOCUS_LOG", file, "focus log attachment is required");
      }
      if (!/getElementById\("receiver-video"\)/.test(source)) {
        record("MISSING_RECEIVER_ELEMENT", file, "receiver video element lookup is required");
      }
      if (/sender-preview|getDisplayMedia|getUserMedia/.test(source)) {
        record("RECEIVER_PREVIEW_CONFUSION", file, "receiver must not reference sender capture");
      }
    }

    if (name === "app.mjs") {
      if (!/\battachFocusLog\s*\(/.test(source)) {
        record("MISSING_FOCUS_LOG", file, "focus log attachment is required");
      }
      if (!/underlay-button/.test(source) || !/underlay-count/.test(source)) {
        record("MISSING_INDEX_CONTROLS", file, "inert underlay button/counter is required");
      }
      if (/getDisplayMedia|getUserMedia|RTCPeerConnection/.test(source)) {
        record("INDEX_CAPTURE_CODE", file, "index page must not contain capture code");
      }
    }
  }

  if (displayCaptureCount !== 1) {
    record(
      "DISPLAY_CAPTURE_OUTSIDE_GESTURE",
      serverPath,
      `expected exactly one getDisplayMedia call across the web fixture, found ${displayCaptureCount}`
    );
  }

  const captureGuardPath = path.join(webRoot, "capture-guard.mjs");
  const captureGuardSource = fileContents.get(captureGuardPath) ?? "";
  if (!/getAudioTracks\s*\(/.test(captureGuardSource) || !/getVideoTracks\s*\(/.test(captureGuardSource)) {
    record("MISSING_TRACK_CHECK", captureGuardPath, "video-only track inspection is required");
  }

  // Server rules.
  if (serverText.length > 0) {
    if (!/export const HOST = "127\.0\.0\.1";/.test(serverText)) {
      record("SERVER_BIND", serverPath, "server must export HOST = 127.0.0.1");
    }
    if (/\b0\.0\.0\.0\b|"::"|'::'/.test(serverText)) {
      record("SERVER_BIND", serverPath, "wildcard bind address is not allowed");
    }
    if (!/server\.listen\([^)]*HOST/.test(serverText)) {
      record("SERVER_LISTEN", serverPath, "server.listen must pass the loopback HOST");
    }
    if (/node:child_process|\bexecSync\s*\(|\bexecFile\s*\(|\bspawnSync\s*\(|\bspawn\s*\(/.test(serverText)) {
      record("SERVER_CHILD_PROCESS", serverPath, "child processes are not allowed");
    }
    if (/\bfetch\s*\(|\bXMLHttpRequest\b|\bWebSocket\b|\bEventSource\b|\bnode:https\b|\bhttps\.request\b|\bhttp\.request\b/.test(serverText)) {
      record("SERVER_NETWORK", serverPath, "server may not make network requests");
    }
    if (
      !/const isDirectRun/.test(serverText) ||
      !/if \(isDirectRun\)/.test(serverText) ||
      /^main\(\);/m.test(serverText) ||
      /^await main\(\);/m.test(serverText)
    ) {
      record("SERVER_AUTOSTART", serverPath, "server must only start from an explicit direct-run guard");
    }
    for (const header of [
      "X-Content-Type-Options",
      "Referrer-Policy",
      "Permissions-Policy",
      "X-Frame-Options"
    ]) {
      if (!serverText.includes(header)) {
        record("SERVER_MISSING_HEADER", serverPath, `missing security header ${header}`);
      }
    }
    if (
      !serverText.includes("camera=()") ||
      !serverText.includes("microphone=()") ||
      !serverText.includes("display-capture=(self)")
    ) {
      record("SERVER_PERMISSIONS_POLICY", serverPath, "Permissions-Policy must deny camera/mic and allow self display-capture");
    }
    if (serverText.includes("Access-Control-Allow-Origin")) {
      record("SERVER_CORS", serverPath, "CORS headers are not allowed");
    }
    if (!serverText.includes("Cache-Control") || !serverText.includes("no-store")) {
      record("SERVER_CACHE", serverPath, "no-store caching is required");
    }
    if (!serverText.includes("isDirectory")) {
      record("SERVER_DIRECTORY_GUARD", serverPath, "directory requests must be rejected explicitly");
    }
    if (!serverText.includes("path.relative") || !serverText.includes('startsWith("..")')) {
      record("SERVER_PATH_GUARD", serverPath, "path traversal guard is required");
    }
    if (!serverText.includes("GET") || !serverText.includes("HEAD")) {
      record("SERVER_METHOD_GUARD", serverPath, "only GET/HEAD may be served");
    }
    if (!serverText.includes("contentTypeFor")) {
      record("SERVER_CONTENT_TYPE", serverPath, "content type allowlist is required");
    }
    if (!/Content-Security-Policy[^\n]*CSP_POLICY/.test(serverText)) {
      record("SERVER_CSP_HEADER", serverPath, "CSP header must use the shared CSP_POLICY constant");
    }
    if (/\bsetTimeout\s*\(|\bsetInterval\s*\(/.test(serverText)) {
      record("SERVER_AUTOSTART_TIMER", serverPath, "timers are not allowed in the server tool");
    }
    if (serverCsp === null) {
      record("SERVER_CSP_MISSING", serverPath, "CSP_POLICY constant is missing");
    } else {
      for (const token of REQUIRED_CSP_TOKENS) {
        if (!serverCsp.includes(token)) {
          record("CSP_WEAK", serverPath, `server CSP is missing ${token}`);
        }
      }
    }
  }

  return {
    ok: errors.length === 0,
    errors,
    scanned: scanned.map((file) => relativeDisplay(projectRoot, file))
  };
}
