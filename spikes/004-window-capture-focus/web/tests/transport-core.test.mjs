import test from "node:test";
import assert from "node:assert/strict";

import {
  SIGNALING_CHANNEL,
  createCandidateQueue,
  createCleanupLedger,
  createEventLog,
  validateSignalMessage
} from "../transport-core.mjs";

test("uses a project-local BroadcastChannel name", () => {
  assert.equal(SIGNALING_CHANNEL, "escalier-004-signaling-v1");
});

test("accepts offer and answer messages with SDP only", () => {
  const offer = validateSignalMessage({ type: "offer", sdp: "v=0\r\nmock" });
  assert.equal(offer.ok, true);
  assert.deepEqual(offer.message, { type: "offer", sdp: "v=0\r\nmock" });
  const answer = validateSignalMessage({ type: "answer", sdp: "v=0\r\nmock" });
  assert.equal(answer.ok, true);
  assert.deepEqual(answer.message, { type: "answer", sdp: "v=0\r\nmock" });
});

test("accepts local ICE candidate messages only post-validation", () => {
  const result = validateSignalMessage({
    type: "candidate",
    candidate: "candidate:1 1 UDP 2122260223 127.0.0.1 50000 typ host",
    sdpMid: "0",
    sdpMLineIndex: 0
  });
  assert.equal(result.ok, true);
  assert.equal(result.message.type, "candidate");
  assert.equal(result.message.sdpMLineIndex, 0);
});

test("accepts only empty receiver-ready and bye lifecycle messages", () => {
  assert.deepEqual(validateSignalMessage({ type: "receiver-ready" }), {
    ok: true,
    message: { type: "receiver-ready" }
  });
  assert.deepEqual(validateSignalMessage({ type: "bye" }), {
    ok: true,
    message: { type: "bye" }
  });
});

test("rejects unknown, non-object, array and extra-field messages", () => {
  for (const value of [
    null,
    "offer",
    [],
    { type: "unknown" },
    { type: "receiver-ready", extra: true },
    { type: "offer", sdp: "v=0", extra: true }
  ]) {
    const result = validateSignalMessage(value);
    assert.equal(result.ok, false, JSON.stringify(value));
  }
});

test("rejects missing, empty, oversized or URL-bearing SDP", () => {
  for (const sdp of [
    undefined,
    "",
    "x".repeat(200_001),
    "v=0\r\nstun:example.invalid",
    "v=0\r\nturn:example.invalid",
    "v=0\r\nhttps://example.invalid"
  ]) {
    const result = validateSignalMessage({ type: "offer", sdp });
    assert.equal(result.ok, false, String(sdp).slice(0, 40));
  }
});

test("rejects candidate URL fields and STUN/TURN candidate strings", () => {
  const withUrl = validateSignalMessage({
    type: "candidate",
    candidate: "candidate:1 1 UDP 1 127.0.0.1 50000 typ host",
    sdpMid: "0",
    sdpMLineIndex: 0,
    url: "stun:example.invalid"
  });
  assert.equal(withUrl.ok, false);
  const withStun = validateSignalMessage({
    type: "candidate",
    candidate: "candidate:1 1 UDP 1 127.0.0.1 50000 typ host stun:example.invalid",
    sdpMid: "0",
    sdpMLineIndex: 0
  });
  assert.equal(withStun.ok, false);
});

test("queues ICE candidates until the remote description is ready", () => {
  const queue = createCandidateQueue();
  assert.equal(queue.pendingCount, 0);
  const first = { candidate: "candidate:a" };
  const second = { candidate: "candidate:b" };
  assert.deepEqual(queue.add(first), { queued: true, flush: [] });
  assert.deepEqual(queue.add(second), { queued: true, flush: [] });
  assert.equal(queue.pendingCount, 2);
  assert.deepEqual(queue.pending(), [first, second]);
  assert.deepEqual(queue.markRemoteDescriptionSet(), [first, second]);
  assert.equal(queue.pendingCount, 0);
  const third = { candidate: "candidate:c" };
  assert.deepEqual(queue.add(third), { queued: false, flush: [third] });
});

test("candidate queue reset drops pending candidates without reordering", () => {
  const queue = createCandidateQueue();
  queue.add({ candidate: "candidate:a" });
  queue.add({ candidate: "candidate:b" });
  queue.reset();
  assert.equal(queue.pendingCount, 0);
  assert.deepEqual(queue.markRemoteDescriptionSet(), []);
});

test("cleanup ledger runs stop, peer close and channel close once in order", () => {
  const calls = [];
  const ledger = createCleanupLedger({
    stopTracks: () => calls.push("stop-tracks"),
    closePeer: () => calls.push("close-peer"),
    closeChannel: () => calls.push("close-channel"),
    log: (entry) => calls.push(`log:${entry.event}`)
  });

  const first = ledger.run("user-stop");
  assert.equal(first.alreadyCleaned, false);
  assert.deepEqual(first.actions.map((action) => action.name), [
    "stop-local-tracks",
    "close-peer",
    "close-channel"
  ]);
  assert.deepEqual(calls, [
    "stop-tracks",
    "close-peer",
    "close-channel",
    "log:cleanup"
  ]);

  const second = ledger.run("again");
  assert.equal(second.alreadyCleaned, true);
  assert.equal(calls.length, 4);
});

test("cleanup continues after a failing step and reports it", () => {
  const calls = [];
  const ledger = createCleanupLedger({
    stopTracks: () => calls.push("stop-tracks"),
    closePeer: () => {
      calls.push("close-peer");
      throw new Error("mock peer close failure");
    },
    closeChannel: () => calls.push("close-channel")
  });
  const outcome = ledger.run("failure-test");
  assert.deepEqual(calls, ["stop-tracks", "close-peer", "close-channel"]);
  assert.equal(outcome.alreadyCleaned, false);
  const peer = outcome.actions.find((action) => action.name === "close-peer");
  assert.equal(peer.ok, false);
  assert.match(peer.error, /mock peer close failure/);
  assert.equal(outcome.actions.find((action) => action.name === "close-channel").ok, true);
});

test("event log preserves ordering, bounds memory and exposes no frame data", () => {
  const log = createEventLog({ limit: 2, now: () => "T" });
  log.record("first", { note: "a" });
  log.record("second", { note: "b" });
  log.record("third", { note: "c" });
  const entries = log.toJSON();
  assert.deepEqual(entries.map((entry) => entry.event), ["second", "third"]);
  assert.equal(entries[0].at, "T");
  assert.deepEqual(entries[0].detail, { note: "b" });
  log.clear();
  assert.deepEqual(log.toJSON(), []);
});
