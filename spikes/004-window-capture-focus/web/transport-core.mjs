export const SIGNALING_CHANNEL = "escalier-004-signaling-v1";
export const ALLOWED_SIGNAL_TYPES = Object.freeze([
  "receiver-ready",
  "offer",
  "answer",
  "candidate",
  "bye"
]);

const MAX_SDP_LENGTH = 200_000;
const MAX_CANDIDATE_LENGTH = 4_096;
const URL_MARKERS = [
  "stun" + ":",
  "turn" + ":",
  "http" + "://",
  "https" + "://",
  "ws" + "://",
  "wss" + "://"
];

function isPlainObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function containsUrlMarker(value) {
  const lowercased = value.toLowerCase();
  return URL_MARKERS.some((marker) => lowercased.includes(marker));
}

function allowedKeysFor(type) {
  switch (type) {
    case "offer":
    case "answer":
      return ["sdp", "type"];
    case "candidate":
      return ["candidate", "sdpMLineIndex", "sdpMid", "type"];
    case "receiver-ready":
    case "bye":
      return ["type"];
    default:
      return null;
  }
}

/**
 * Validates the only permitted same-origin signaling payloads. No external
 * URLs, STUN/TURN servers, arbitrary blobs or extra fields are accepted.
 */
export function validateSignalMessage(value) {
  if (!isPlainObject(value)) {
    return Object.freeze({ ok: false, reason: "message-not-object" });
  }
  if (!ALLOWED_SIGNAL_TYPES.includes(value.type)) {
    return Object.freeze({ ok: false, reason: "message-type-not-allowed" });
  }

  const allowed = allowedKeysFor(value.type);
  for (const key of Object.keys(value)) {
    if (!allowed.includes(key)) {
      return Object.freeze({ ok: false, reason: "unexpected-field" });
    }
  }

  if (value.type === "offer" || value.type === "answer") {
    if (typeof value.sdp !== "string" || value.sdp.length === 0) {
      return Object.freeze({ ok: false, reason: "sdp-missing" });
    }
    if (value.sdp.length > MAX_SDP_LENGTH) {
      return Object.freeze({ ok: false, reason: "sdp-too-long" });
    }
    if (containsUrlMarker(value.sdp)) {
      return Object.freeze({ ok: false, reason: "sdp-contains-external-url" });
    }
    return Object.freeze({
      ok: true,
      message: Object.freeze({ type: value.type, sdp: value.sdp })
    });
  }

  if (value.type === "candidate") {
    if (typeof value.candidate !== "string" || value.candidate.length === 0) {
      return Object.freeze({ ok: false, reason: "candidate-missing" });
    }
    if (value.candidate.length > MAX_CANDIDATE_LENGTH) {
      return Object.freeze({ ok: false, reason: "candidate-too-long" });
    }
    if (containsUrlMarker(value.candidate)) {
      return Object.freeze({ ok: false, reason: "candidate-contains-external-url" });
    }
    if (
      value.sdpMid !== undefined &&
      value.sdpMid !== null &&
      typeof value.sdpMid !== "string"
    ) {
      return Object.freeze({ ok: false, reason: "sdp-mid-invalid" });
    }
    if (
      value.sdpMLineIndex !== undefined &&
      value.sdpMLineIndex !== null &&
      (!Number.isInteger(value.sdpMLineIndex) || value.sdpMLineIndex < 0)
    ) {
      return Object.freeze({ ok: false, reason: "sdp-mline-index-invalid" });
    }
    const message = { type: "candidate", candidate: value.candidate };
    if (value.sdpMid !== undefined) message.sdpMid = value.sdpMid;
    if (value.sdpMLineIndex !== undefined) message.sdpMLineIndex = value.sdpMLineIndex;
    return Object.freeze({ ok: true, message: Object.freeze(message) });
  }

  return Object.freeze({ ok: true, message: Object.freeze({ type: value.type }) });
}

/**
 * Buffers ICE candidates that arrive before the remote description.
 * Ordering is preserved exactly; add() is deterministic.
 */
export function createCandidateQueue() {
  let pending = [];
  let remoteDescriptionReady = false;

  return {
    add(candidate) {
      if (remoteDescriptionReady) {
        return { queued: false, flush: [candidate] };
      }
      pending.push(candidate);
      return { queued: true, flush: [] };
    },
    markRemoteDescriptionSet() {
      remoteDescriptionReady = true;
      const flush = pending.slice();
      pending = [];
      return flush;
    },
    pending() {
      return pending.slice();
    },
    get pendingCount() {
      return pending.length;
    },
    reset() {
      pending = [];
      remoteDescriptionReady = false;
    }
  };
}

/**
 * Cleanup order is fixed and idempotent. A failing step never prevents later
 * steps from running; the outcome names the failed step without throwing.
 */
export function createCleanupLedger({
  stopTracks = () => {},
  closePeer = () => {},
  closeChannel = () => {},
  log = () => {}
} = {}) {
  const steps = [
    { name: "stop-local-tracks", run: stopTracks },
    { name: "close-peer", run: closePeer },
    { name: "close-channel", run: closeChannel }
  ];
  let cleaned = false;
  let lastOutcome = null;

  return {
    run(reason) {
      if (cleaned) {
        return {
          alreadyCleaned: true,
          actions: lastOutcome ? lastOutcome.slice() : []
        };
      }
      cleaned = true;
      const actions = steps.map((step) => {
        try {
          step.run();
          return { name: step.name, ok: true, error: null };
        } catch (error) {
          return {
            name: step.name,
            ok: false,
            error: error instanceof Error ? error.message : String(error)
          };
        }
      });
      lastOutcome = actions.slice();
      try {
        log({
          event: "cleanup",
          reason,
          actions: actions.map(({ name, ok }) => ({ name, ok }))
        });
      } catch {
        // Logging must not change cleanup ordering or throw into the page.
      }
      return { alreadyCleaned: false, actions: actions.slice() };
    },
    get cleaned() {
      return cleaned;
    }
  };
}

export function createEventLog({ limit = 500, now = () => new Date().toISOString() } = {}) {
  if (!Number.isInteger(limit) || limit < 1) {
    throw new RangeError("event log limit must be a positive integer");
  }
  let entries = [];

  return {
    record(event, detail = null) {
      const entry = {
        at: now(),
        event: String(event),
        detail
      };
      entries.push(entry);
      if (entries.length > limit) {
        entries.splice(0, entries.length - limit);
      }
      return { ...entry };
    },
    toJSON() {
      return entries.map((entry) => ({
        at: entry.at,
        event: entry.event,
        detail:
          entry.detail !== null && typeof entry.detail === "object"
            ? { ...entry.detail }
            : entry.detail
      }));
    },
    clear() {
      entries = [];
    }
  };
}
