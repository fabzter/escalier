export const MARKER_RGB = Object.freeze({ r: 255, g: 0, b: 170 });

function numberOrNull(value) {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

/**
 * Extracts only inbound video RTP statistics from an RTCPeerConnection stats
 * report. Returns null unless inbound video is present. A sender preview,
 * outbound stats or connection state cannot substitute for this evidence.
 */
export function extractInboundVideoStats(statsReport) {
  if (!statsReport || typeof statsReport.forEach !== "function") {
    return null;
  }

  let selected = null;
  let selectedBytes = -1;
  statsReport.forEach((report) => {
    if (report.type !== "inbound-rtp") return;
    if (report.kind !== "video" && report.mediaType !== "video") return;
    const bytes = numberOrNull(report.bytesReceived) ?? 0;
    if (selected === null || bytes > selectedBytes) {
      selected = report;
      selectedBytes = bytes;
    }
  });

  if (selected === null) return null;

  return {
    id: typeof selected.id === "string" ? selected.id : null,
    framesDecoded: numberOrNull(selected.framesDecoded),
    framesReceived: numberOrNull(selected.framesReceived),
    bytesReceived: numberOrNull(selected.bytesReceived),
    packetsReceived: numberOrNull(selected.packetsReceived),
    packetsLost: numberOrNull(selected.packetsLost),
    jitter: numberOrNull(selected.jitter),
    frameWidth: numberOrNull(selected.frameWidth),
    frameHeight: numberOrNull(selected.frameHeight),
    framesPerSecond: numberOrNull(selected.framesPerSecond),
    timestamp: numberOrNull(selected.timestamp)
  };
}

/**
 * Computes marker-color coverage for a cropped receiver ROI. The caller passes
 * only RGBA bytes for that ROI; this function never receives or returns a
 * full-frame image and never persists pixels.
 */
export function computeRoiStats(rgba, width, height, { tolerance = 28 } = {}) {
  if (!Number.isInteger(width) || width <= 0) {
    throw new RangeError("ROI width must be a positive integer");
  }
  if (!Number.isInteger(height) || height <= 0) {
    throw new RangeError("ROI height must be a positive integer");
  }
  if (!Number.isInteger(tolerance) || tolerance < 0) {
    throw new RangeError("tolerance must be a non-negative integer");
  }
  const expectedLength = width * height * 4;
  if (!rgba || rgba.length !== expectedLength) {
    throw new RangeError(
      `ROI buffer length must be ${expectedLength} RGBA bytes`
    );
  }

  let nearMarkerPixels = 0;
  let redTotal = 0;
  let greenTotal = 0;
  let blueTotal = 0;
  const pixelCount = width * height;

  for (let offset = 0; offset < rgba.length; offset += 4) {
    const red = rgba[offset];
    const green = rgba[offset + 1];
    const blue = rgba[offset + 2];
    redTotal += red;
    greenTotal += green;
    blueTotal += blue;
    if (
      Math.abs(red - MARKER_RGB.r) <= tolerance &&
      Math.abs(green - MARKER_RGB.g) <= tolerance &&
      Math.abs(blue - MARKER_RGB.b) <= tolerance
    ) {
      nearMarkerPixels += 1;
    }
  }

  return {
    width,
    height,
    pixelCount,
    nearMarkerPixels,
    nearMarkerFraction: nearMarkerPixels / pixelCount,
    meanRed: redTotal / pixelCount,
    meanGreen: greenTotal / pixelCount,
    meanBlue: blueTotal / pixelCount
  };
}

/**
 * Builds a receiver-evidence summary from inbound RTP stats, the receiver
 * video element's intrinsic dimensions, manual ROI samples and the focus log.
 * It never accepts sender-preview pixels as receiver evidence.
 */
export function buildReceiverEvidence({
  inbound = null,
  video = null,
  roiSamples = [],
  focusLog = [],
  positiveControl = null,
  senderPreviewUsed = false
} = {}) {
  const reasons = [];
  const videoWidth = numberOrNull(video?.width);
  const videoHeight = numberOrNull(video?.height);
  const hasBytesReceived =
    inbound !== null && (numberOrNull(inbound.bytesReceived) ?? 0) > 0;
  const hasTimestamp =
    inbound !== null && (numberOrNull(inbound.timestamp) ?? 0) > 0;
  const hasDecodedFrames =
    inbound !== null &&
    typeof inbound.framesDecoded === "number" &&
    inbound.framesDecoded > 0;
  const hasFrameDimensions =
    inbound !== null &&
    typeof inbound.frameWidth === "number" &&
    inbound.frameWidth > 0 &&
    typeof inbound.frameHeight === "number" &&
    inbound.frameHeight > 0;
  const hasVideoDimensions =
    videoWidth !== null && videoWidth > 0 && videoHeight !== null && videoHeight > 0;
  const markerObserved =
    roiSamples.length === 0
      ? null
      : roiSamples.some((sample) => sample.nearMarkerFraction > 0);

  let status = "NO RECEIVER EVIDENCE";
  let transport = null;

  if (senderPreviewUsed) {
    reasons.push("Only a sender preview is available; a sender preview is not receiver evidence.");
  } else if (inbound === null) {
    reasons.push("No receiver transport statistics (inbound RTP video) are available.");
  } else if (!hasBytesReceived || !hasTimestamp) {
    transport = inbound;
    reasons.push(
      "Inbound RTP bytesReceived and timestamp are required and must be positive; missing, zero, negative, or non-finite fields are not receiver evidence."
    );
  } else if (!hasDecodedFrames) {
    transport = inbound;
    reasons.push("Inbound RTP exists but framesDecoded is zero or missing.");
  } else if (!hasFrameDimensions) {
    transport = inbound;
    reasons.push("Inbound RTP frame dimensions are missing or zero.");
  } else if (!hasVideoDimensions) {
    transport = inbound;
    reasons.push("Receiver video dimensions are missing or zero.");
  } else {
    status = "RECEIVER TRANSPORT OBSERVED";
    transport = inbound;
    reasons.push(
      "Inbound RTP decoded frames, bytes, timestamp, and receiver video dimensions are present."
    );
  }

  let interpretation;
  if (status !== "RECEIVER TRANSPORT OBSERVED") {
    interpretation =
      "No receiver transport evidence is claimed. Do not interpret marker absence from this cell.";
  } else if (positiveControl === true) {
    interpretation =
      "Receiver transport observed with a positive control. Marker presence or absence remains a local observation with no stealth or privacy guarantee.";
  } else {
    interpretation =
      "Receiver transport observed, but no positive control is visible. Do not interpret marker absence from this cell.";
  }

  return {
    status,
    reasons,
    transport,
    receiverVideoWidth: videoWidth,
    receiverVideoHeight: videoHeight,
    videoReadyState: numberOrNull(video?.readyState),
    videoCurrentTime: numberOrNull(video?.currentTime),
    roiSamples,
    roiSampleCount: roiSamples.length,
    markerObserved,
    positiveControl: positiveControl === true,
    focusLogEntries: focusLog.length,
    senderPreviewUsed: senderPreviewUsed === true,
    interpretation
  };
}
