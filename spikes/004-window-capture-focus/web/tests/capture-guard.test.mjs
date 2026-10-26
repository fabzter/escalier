import test from "node:test";
import assert from "node:assert/strict";

import {
  CAPTURE_ERROR,
  guardCaptureRequest,
  inspectVideoOnlyStream
} from "../capture-guard.mjs";

test("accepts a secure, active user gesture with audio explicitly disabled", () => {
  const result = guardCaptureRequest({
    isSecureContext: true,
    userActivationActive: true,
    audioRequested: false,
    mediaDevicesAvailable: true
  });
  assert.deepEqual(result, { ok: true, reason: null });
});

test("rejects an insecure context", () => {
  const result = guardCaptureRequest({
    isSecureContext: false,
    userActivationActive: true,
    audioRequested: false,
    mediaDevicesAvailable: true
  });
  assert.equal(result.ok, false);
  assert.equal(result.reason, CAPTURE_ERROR.INSECURE_CONTEXT);
});

test("rejects a request without transient user activation", () => {
  const result = guardCaptureRequest({
    isSecureContext: true,
    userActivationActive: false,
    audioRequested: false,
    mediaDevicesAvailable: true
  });
  assert.equal(result.ok, false);
  assert.equal(result.reason, CAPTURE_ERROR.NO_USER_ACTIVATION);
});

test("rejects any audio request", () => {
  const result = guardCaptureRequest({
    isSecureContext: true,
    userActivationActive: true,
    audioRequested: true,
    mediaDevicesAvailable: true
  });
  assert.equal(result.ok, false);
  assert.equal(result.reason, CAPTURE_ERROR.AUDIO_REQUESTED);
});

test("rejects unavailable display media devices", () => {
  const result = guardCaptureRequest({
    isSecureContext: true,
    userActivationActive: true,
    audioRequested: false,
    mediaDevicesAvailable: false
  });
  assert.equal(result.ok, false);
  assert.equal(result.reason, CAPTURE_ERROR.MEDIA_DEVICES_UNAVAILABLE);
});

test("missing fields fail closed", () => {
  const result = guardCaptureRequest({});
  assert.equal(result.ok, false);
  assert.equal(result.reason, CAPTURE_ERROR.INSECURE_CONTEXT);
});

test("accepts exactly one video track and zero audio tracks", () => {
  const videoTrack = { kind: "video" };
  const stream = {
    getVideoTracks: () => [videoTrack],
    getAudioTracks: () => []
  };
  const result = inspectVideoOnlyStream(stream);
  assert.equal(result.ok, true);
  assert.equal(result.videoTrack, videoTrack);
  assert.equal(result.videoCount, 1);
  assert.equal(result.audioCount, 0);
});

test("rejects a stream that contains an audio track", () => {
  const stream = {
    getVideoTracks: () => [{ kind: "video" }],
    getAudioTracks: () => [{ kind: "audio" }]
  };
  const result = inspectVideoOnlyStream(stream);
  assert.equal(result.ok, false);
  assert.equal(result.reason, "audio-track-present");
  assert.equal(result.audioCount, 1);
});

test("rejects zero or multiple video tracks", () => {
  const zero = inspectVideoOnlyStream({ getVideoTracks: () => [], getAudioTracks: () => [] });
  assert.equal(zero.ok, false);
  assert.equal(zero.reason, "expected-exactly-one-video-track");
  const multiple = inspectVideoOnlyStream({
    getVideoTracks: () => [{}, {}],
    getAudioTracks: () => []
  });
  assert.equal(multiple.ok, false);
  assert.equal(multiple.reason, "expected-exactly-one-video-track");
});

test("rejects an unavailable stream object", () => {
  const result = inspectVideoOnlyStream(null);
  assert.equal(result.ok, false);
  assert.equal(result.reason, "stream-unavailable");
});
