import test from "node:test";
import assert from "node:assert/strict";

import { attachFocusLog, createFocusLog } from "../focus-log.mjs";

test("records focus snapshots in deterministic order with bounded memory", () => {
  const log = createFocusLog({ limit: 2, now: () => "T" });
  const first = log.record("focus", {
    visibilityState: "visible",
    hasFocus: true,
    activeElement: "BUTTON"
  });
  assert.deepEqual(first, {
    name: "focus",
    at: "T",
    visibilityState: "visible",
    hasFocus: true,
    activeElement: "BUTTON"
  });
  log.record("blur", { visibilityState: "visible", hasFocus: false, activeElement: "BODY" });
  log.record("visibilitychange", { visibilityState: "hidden", hasFocus: false, activeElement: null });
  assert.deepEqual(
    log.entries().map((entry) => entry.name),
    ["blur", "visibilitychange"]
  );
  assert.equal(log.entries().length, 2);
  assert.equal(log.entries()[1].visibilityState, "hidden");
  log.clear();
  assert.deepEqual(log.toJSON(), []);
});

test("snapshot normalizes missing values without inventing focus", () => {
  const log = createFocusLog({ now: () => "T" });
  const snapshot = log.snapshot({});
  assert.deepEqual(snapshot, {
    at: "T",
    visibilityState: "unknown",
    hasFocus: false,
    activeElement: null
  });
});

test("returned entries are defensive copies", () => {
  const log = createFocusLog({ now: () => "T" });
  log.record("focus", { visibilityState: "visible", hasFocus: true, activeElement: "BUTTON" });
  const entries = log.entries();
  entries[0].name = "mutated";
  assert.equal(log.entries()[0].name, "focus");
});

test("attachFocusLog requires DOM-like arguments", () => {
  assert.throws(() => attachFocusLog({}), /win, doc and log/);
});

test("attachFocusLog subscribes to focus, blur, visibility and lifecycle events", () => {
  const listeners = new Map();
  const fakeWindow = {
    addEventListener(type, callback) {
      listeners.set(`win:${type}`, callback);
    }
  };
  const fakeDocument = {
    visibilityState: "visible",
    hasFocus: () => true,
    activeElement: { tagName: "BUTTON" },
    addEventListener(type, callback) {
      listeners.set(`doc:${type}`, callback);
    }
  };
  const log = createFocusLog({ now: () => "T" });
  const handle = attachFocusLog({ win: fakeWindow, doc: fakeDocument, log });
  assert.equal(log.entries()[0].name, "initial");
  listeners.get("win:focus")();
  listeners.get("win:blur")();
  listeners.get("doc:visibilitychange")();
  listeners.get("win:pageshow")();
  listeners.get("win:pagehide")();
  assert.deepEqual(
    log.entries().map((entry) => entry.name),
    ["initial", "focus", "blur", "visibilitychange", "pageshow", "pagehide"]
  );
  const snapshot = handle.snapshotNow();
  assert.equal(snapshot.hasFocus, true);
  assert.equal(log.entries().at(-1).name, "manual-snapshot");
  handle.detach();
  assert.equal(listeners.size, 5);
});
