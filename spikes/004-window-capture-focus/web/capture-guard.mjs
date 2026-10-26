export const CAPTURE_ERROR = Object.freeze({
  INSECURE_CONTEXT: "insecure-context",
  NO_USER_ACTIVATION: "no-transient-user-activation",
  AUDIO_REQUESTED: "audio-requested",
  MEDIA_DEVICES_UNAVAILABLE: "media-devices-unavailable",
  STREAM_UNAVAILABLE: "stream-unavailable",
  AUDIO_TRACK_PRESENT: "audio-track-present",
  WRONG_VIDEO_TRACK_COUNT: "expected-exactly-one-video-track"
});

/**
 * Fail-closed preflight for a user-chosen display capture. This function does
 * not request media; callers must invoke it synchronously inside a click
 * handler, then call getDisplayMedia with audio:false.
 */
export function guardCaptureRequest({
  isSecureContext,
  userActivationActive,
  audioRequested,
  mediaDevicesAvailable
} = {}) {
  if (isSecureContext !== true) {
    return Object.freeze({ ok: false, reason: CAPTURE_ERROR.INSECURE_CONTEXT });
  }
  if (userActivationActive !== true) {
    return Object.freeze({ ok: false, reason: CAPTURE_ERROR.NO_USER_ACTIVATION });
  }
  if (audioRequested !== false) {
    return Object.freeze({ ok: false, reason: CAPTURE_ERROR.AUDIO_REQUESTED });
  }
  if (mediaDevicesAvailable !== true) {
    return Object.freeze({ ok: false, reason: CAPTURE_ERROR.MEDIA_DEVICES_UNAVAILABLE });
  }
  return Object.freeze({ ok: true, reason: null });
}

/**
 * Receives only a browser MediaStream. Rejects any audio track and requires
 * exactly one video track. A sender preview alone is never receiver evidence.
 */
export function inspectVideoOnlyStream(stream) {
  if (
    stream === null ||
    typeof stream !== "object" ||
    typeof stream.getVideoTracks !== "function" ||
    typeof stream.getAudioTracks !== "function"
  ) {
    return Object.freeze({
      ok: false,
      reason: CAPTURE_ERROR.STREAM_UNAVAILABLE,
      videoCount: 0,
      audioCount: 0
    });
  }

  const videoTracks = stream.getVideoTracks();
  const audioTracks = stream.getAudioTracks();

  if (audioTracks.length !== 0) {
    return Object.freeze({
      ok: false,
      reason: CAPTURE_ERROR.AUDIO_TRACK_PRESENT,
      videoCount: videoTracks.length,
      audioCount: audioTracks.length
    });
  }

  if (videoTracks.length !== 1) {
    return Object.freeze({
      ok: false,
      reason: CAPTURE_ERROR.WRONG_VIDEO_TRACK_COUNT,
      videoCount: videoTracks.length,
      audioCount: audioTracks.length
    });
  }

  return Object.freeze({
    ok: true,
    reason: null,
    videoTrack: videoTracks[0],
    videoCount: 1,
    audioCount: 0
  });
}
