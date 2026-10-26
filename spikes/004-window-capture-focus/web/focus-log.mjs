export function createFocusLog({
  limit = 500,
  now = () => new Date().toISOString()
} = {}) {
  if (!Number.isInteger(limit) || limit < 1) {
    throw new RangeError("focus log limit must be a positive integer");
  }
  let entries = [];

  function snapshot({ visibilityState, hasFocus, activeElement } = {}) {
    return {
      at: now(),
      visibilityState:
        typeof visibilityState === "string" && visibilityState.length > 0
          ? visibilityState
          : "unknown",
      hasFocus: hasFocus === true,
      activeElement:
        activeElement === null || activeElement === undefined
          ? null
          : String(activeElement)
    };
  }

  return {
    snapshot,
    record(name, input = {}) {
      const entry = { name: String(name), ...snapshot(input) };
      entries.push(entry);
      if (entries.length > limit) {
        entries.splice(0, entries.length - limit);
      }
      return { ...entry };
    },
    entries() {
      return entries.map((entry) => ({ ...entry }));
    },
    toJSON() {
      return entries.map((entry) => ({ ...entry }));
    },
    clear() {
      entries = [];
    }
  };
}

/**
 * Attaches focus, blur, visibility and page lifecycle listeners. It does not
 * listen to keys, pointer content, clipboard or any browser permission API.
 */
export function attachFocusLog({ win, doc, log }) {
  if (!win || !doc || !log) {
    throw new Error("attachFocusLog requires win, doc and log");
  }

  function currentSnapshot() {
    return log.snapshot({
      visibilityState: doc.visibilityState,
      hasFocus: typeof doc.hasFocus === "function" ? doc.hasFocus() : false,
      activeElement: doc.activeElement?.tagName ?? null
    });
  }

  log.record("initial", {
    visibilityState: doc.visibilityState,
    hasFocus: typeof doc.hasFocus === "function" ? doc.hasFocus() : false,
    activeElement: doc.activeElement?.tagName ?? null
  });

  const subscriptions = [
    [win, "focus", "focus"],
    [win, "blur", "blur"],
    [win, "pageshow", "pageshow"],
    [win, "pagehide", "pagehide"],
    [doc, "visibilitychange", "visibilitychange"]
  ].map(([target, type, name]) => {
    const handler = () => {
      log.record(name, currentSnapshot());
    };
    target.addEventListener(type, handler);
    return { target, type, handler };
  });

  return {
    snapshotNow() {
      return log.record("manual-snapshot", currentSnapshot());
    },
    detach() {
      for (const { target, type, handler } of subscriptions) {
        if (typeof target.removeEventListener === "function") {
          target.removeEventListener(type, handler);
        }
      }
    }
  };
}
