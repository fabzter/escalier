import test from "node:test";
import assert from "node:assert/strict";

import {
  MARKER_RGB,
  buildReceiverEvidence,
  computeRoiStats,
  extractInboundVideoStats
} from "../receiver-core.mjs";

function statsReport(entries) {
  return {
    forEach(callback) {
      for (const entry of entries) callback(entry);
    }
  };
}

test("marker color is the documented synthetic magenta", () => {
  assert.deepEqual(MARKER_RGB, { r: 255, g: 0, b: 170 });
});

test("extracts inbound video statistics and ignores outbound/audio entries", () => {
  const inbound = extractInboundVideoStats(
    statsReport([
      { id: "out", type: "outbound-rtp", kind: "video", framesEncoded: 99 },
      {
        id: "in",
        type: "inbound-rtp",
        kind: "video",
        framesDecoded: 90,
        framesReceived: 92,
        bytesReceived: 400_000,
        packetsReceived: 500,
        packetsLost: 2,
        jitter: 0.004,
        frameWidth: 1920,
        frameHeight: 1080,
        framesPerSecond: 29.97,
        timestamp: 1234
      },
      { id: "audio", type: "inbound-rtp", kind: "audio", bytesReceived: 9999 }
    ])
  );
  assert.deepEqual(inbound, {
    id: "in",
    framesDecoded: 90,
    framesReceived: 92,
    bytesReceived: 400_000,
    packetsReceived: 500,
    packetsLost: 2,
    jitter: 0.004,
    frameWidth: 1920,
    frameHeight: 1080,
    framesPerSecond: 29.97,
    timestamp: 1234
  });
});

test("selects the inbound video entry with the most received bytes deterministically", () => {
  const inbound = extractInboundVideoStats(
    statsReport([
      { id: "small", type: "inbound-rtp", kind: "video", bytesReceived: 1, framesDecoded: 1 },
      { id: "large", type: "inbound-rtp", kind: "video", bytesReceived: 2, framesDecoded: 2 }
    ])
  );
  assert.equal(inbound.id, "large");
});

test("accepts the mediaType fallback used by some browser stats reports", () => {
  const inbound = extractInboundVideoStats(
    statsReport([
      {
        id: "media-type",
        type: "inbound-rtp",
        mediaType: "video",
        framesDecoded: 12,
        bytesReceived: 500,
        frameWidth: 1280,
        frameHeight: 720
      }
    ])
  );
  assert.equal(inbound.id, "media-type");
  assert.equal(inbound.framesDecoded, 12);
});

test("returns null when inbound video statistics are missing", () => {
  assert.equal(extractInboundVideoStats(statsReport([])), null);
  assert.equal(
    extractInboundVideoStats(
      statsReport([{ id: "audio", type: "inbound-rtp", kind: "audio", bytesReceived: 10 }])
    ),
    null
  );
});

test("computes marker coverage from one RGBA ROI only", () => {
  const marker = Uint8ClampedArray.from([
    MARKER_RGB.r, MARKER_RGB.g, MARKER_RGB.b, 255,
    MARKER_RGB.r, MARKER_RGB.g, MARKER_RGB.b, 255
  ]);
  assert.equal(computeRoiStats(marker, 2, 1).nearMarkerFraction, 1);

  const black = Uint8ClampedArray.from([0, 0, 0, 255, 0, 0, 0, 255]);
  assert.equal(computeRoiStats(black, 2, 1).nearMarkerFraction, 0);

  const half = Uint8ClampedArray.from([
    MARKER_RGB.r, MARKER_RGB.g, MARKER_RGB.b, 255,
    0, 0, 0, 255
  ]);
  const stats = computeRoiStats(half, 2, 1);
  assert.equal(stats.nearMarkerFraction, 0.5);
  assert.equal(stats.nearMarkerPixels, 1);
  assert.equal(stats.pixelCount, 2);
});

test("marker tolerance is per channel and does not retain pixels", () => {
  const near = Uint8ClampedArray.from([255, 30, 170, 255]);
  assert.equal(computeRoiStats(near, 1, 1, { tolerance: 28 }).nearMarkerFraction, 0);
  assert.equal(computeRoiStats(near, 1, 1, { tolerance: 40 }).nearMarkerFraction, 1);
  const stats = computeRoiStats(near, 1, 1, { tolerance: 40 });
  assert.deepEqual(Object.keys(stats).sort(), [
    "height",
    "meanBlue",
    "meanGreen",
    "meanRed",
    "nearMarkerFraction",
    "nearMarkerPixels",
    "pixelCount",
    "width"
  ]);
});

test("invalid ROI buffers throw instead of fabricating a measurement", () => {
  assert.throws(() => computeRoiStats(new Uint8ClampedArray(3), 1, 1), /length/);
  assert.throws(() => computeRoiStats(new Uint8ClampedArray(4), 0, 1), /width/);
});

test("missing transport stats means no receiver evidence", () => {
  const evidence = buildReceiverEvidence({
    inbound: null,
    video: { width: 1920, height: 1080 },
    roiSamples: []
  });
  assert.equal(evidence.status, "NO RECEIVER EVIDENCE");
  assert.equal(evidence.transport, null);
  assert.ok(evidence.reasons.some((reason) => reason.includes("transport")));
});

test("zero decoded frames means no receiver evidence", () => {
  const evidence = buildReceiverEvidence({
    inbound: {
      framesDecoded: 0,
      bytesReceived: 1000,
      frameWidth: 1920,
      frameHeight: 1080,
      timestamp: 1234
    },
    video: { width: 1920, height: 1080 }
  });
  assert.equal(evidence.status, "NO RECEIVER EVIDENCE");
});

test("missing, zero or negative bytesReceived means no receiver evidence", () => {
  for (const bytesReceived of [undefined, 0, -1]) {
    const evidence = buildReceiverEvidence({
      inbound: {
        framesDecoded: 90,
        bytesReceived,
        frameWidth: 1920,
        frameHeight: 1080,
        timestamp: 1234
      },
      video: { width: 1920, height: 1080 }
    });
    assert.equal(evidence.status, "NO RECEIVER EVIDENCE", String(bytesReceived));
    assert.ok(
      evidence.reasons.some((reason) => reason.includes("bytesReceived")),
      String(bytesReceived)
    );
  }
});

test("missing, zero, negative or non-finite timestamp means no receiver evidence", () => {
  for (const timestamp of [undefined, 0, -1, Number.NaN, Number.POSITIVE_INFINITY]) {
    const evidence = buildReceiverEvidence({
      inbound: {
        framesDecoded: 90,
        bytesReceived: 400_000,
        frameWidth: 1920,
        frameHeight: 1080,
        timestamp
      },
      video: { width: 1920, height: 1080 }
    });
    assert.equal(evidence.status, "NO RECEIVER EVIDENCE", String(timestamp));
    assert.ok(
      evidence.reasons.some((reason) => reason.includes("timestamp")),
      String(timestamp)
    );
  }
});

test("missing receiver video dimensions means no receiver evidence", () => {
  const evidence = buildReceiverEvidence({
    inbound: {
      framesDecoded: 10,
      bytesReceived: 1000,
      frameWidth: 1920,
      frameHeight: 1080,
      timestamp: 1234
    },
    video: { width: 0, height: 1080 }
  });
  assert.equal(evidence.status, "NO RECEIVER EVIDENCE");
});

test("sender preview only is rejected as receiver evidence", () => {
  const evidence = buildReceiverEvidence({
    inbound: {
      framesDecoded: 10,
      bytesReceived: 1000,
      frameWidth: 1920,
      frameHeight: 1080,
      timestamp: 1234
    },
    video: { width: 1920, height: 1080 },
    senderPreviewUsed: true
  });
  assert.equal(evidence.status, "NO RECEIVER EVIDENCE");
  assert.ok(evidence.reasons.some((reason) => reason.includes("sender preview")));
});

test("valid inbound frames and dimensions are observed as receiver transport", () => {
  const sample = {
    label: "control-readOnly",
    nearMarkerFraction: 0.97,
    sampledAt: "T",
    width: 32,
    height: 32
  };
  const evidence = buildReceiverEvidence({
    inbound: {
      framesDecoded: 90,
      bytesReceived: 400_000,
      frameWidth: 1920,
      frameHeight: 1080,
      timestamp: 1234
    },
    video: { width: 1920, height: 1080, currentTime: 12.5, readyState: 4 },
    roiSamples: [sample],
    positiveControl: true,
    focusLog: [{ name: "focus" }]
  });
  assert.equal(evidence.status, "RECEIVER TRANSPORT OBSERVED");
  assert.equal(evidence.transport.framesDecoded, 90);
  assert.equal(evidence.transport.bytesReceived, 400_000);
  assert.equal(evidence.receiverVideoWidth, 1920);
  assert.equal(evidence.receiverVideoHeight, 1080);
  assert.equal(evidence.positiveControl, true);
  assert.equal(evidence.markerObserved, true);
  assert.equal(evidence.roiSampleCount, 1);
  assert.equal(evidence.focusLogEntries, 1);
  const text = JSON.stringify(evidence).toLowerCase();
  assert.equal(text.includes("pixels"), false);
  assert.equal(text.includes("rgba"), false);
  assert.equal(text.includes("data:image"), false);
});

test("transport without a positive control is not interpreted as marker absence evidence", () => {
  const evidence = buildReceiverEvidence({
    inbound: {
      framesDecoded: 90,
      bytesReceived: 400_000,
      frameWidth: 1920,
      frameHeight: 1080,
      timestamp: 1234
    },
    video: { width: 1920, height: 1080 },
    roiSamples: [],
    positiveControl: false
  });
  assert.equal(evidence.status, "RECEIVER TRANSPORT OBSERVED");
  assert.equal(evidence.positiveControl, false);
  assert.match(evidence.interpretation.toLowerCase(), /positive control/);
});
