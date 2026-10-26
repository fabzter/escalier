import { attachFocusLog, createFocusLog } from "./focus-log.mjs";
import {
  SIGNALING_CHANNEL,
  createCandidateQueue,
  createEventLog,
  validateSignalMessage
} from "./transport-core.mjs";
import {
  buildReceiverEvidence,
  computeRoiStats,
  extractInboundVideoStats
} from "./receiver-core.mjs";

const receiverVideo = document.getElementById("receiver-video");
const receiverStatus = document.getElementById("receiver-status");
const statsOutput = document.getElementById("receiver-stats");
const evidenceStatus = document.getElementById("evidence-status");
const evidenceSummary = document.getElementById("evidence-summary");
const roiStatsOutput = document.getElementById("roi-stats");
const roiLogOutput = document.getElementById("roi-log");
const transportLogOutput = document.getElementById("receiver-transport-log");
const roiCanvas = document.getElementById("roi-canvas");
const focusOutput = document.getElementById("focus-log");

const focusLog = createFocusLog({ limit: 400 });
const focusHandle = attachFocusLog({ win: window, doc: document, log: focusLog });
const transportLog = createEventLog({ limit: 400 });
const candidates = createCandidateQueue();

let peerConnection = null;
let channel = null;
let receivedStream = null;
let lastInbound = null;
let roiSamples = [];
let frameCallbackId = null;
let frameCounter = 0;
let statsInFlight = false;

function setStatus(message, kind = "") {
  receiverStatus.textContent = message;
  receiverStatus.className = kind.length > 0 ? `status ${kind}` : "status";
}

function renderFocus() {
  focusOutput.textContent = JSON.stringify(focusLog.toJSON(), null, 2);
}

function renderTransport() {
  roiLogOutput.textContent = JSON.stringify(roiSamples, null, 2);
  transportLogOutput.textContent = JSON.stringify(transportLog.toJSON(), null, 2);
}

function renderStats() {
  if (lastInbound === null) {
    statsOutput.textContent = "No inbound video statistics have been observed.";
    return;
  }
  statsOutput.textContent = [
    `framesDecoded=${lastInbound.framesDecoded ?? "null"}`,
    `framesReceived=${lastInbound.framesReceived ?? "null"}`,
    `bytesReceived=${lastInbound.bytesReceived ?? "null"}`,
    `packetsReceived=${lastInbound.packetsReceived ?? "null"}`,
    `frameWidth=${lastInbound.frameWidth ?? "null"}`,
    `frameHeight=${lastInbound.frameHeight ?? "null"}`,
    `framesPerSecond=${lastInbound.framesPerSecond ?? "null"}`,
    `timestamp=${lastInbound.timestamp ?? "null"}`
  ].join("  ");
}

function renderEvidence() {
  const positiveControl = roiSamples.some(
    (sample) =>
      sample.label === "control-sharing-readOnly" && sample.nearMarkerFraction > 0
  );
  const evidence = buildReceiverEvidence({
    inbound: lastInbound,
    video: {
      width: receiverVideo.videoWidth,
      height: receiverVideo.videoHeight,
      currentTime: receiverVideo.currentTime,
      readyState: receiverVideo.readyState
    },
    roiSamples,
    focusLog: focusLog.toJSON(),
    positiveControl,
    senderPreviewUsed: false
  });
  evidenceStatus.textContent = evidence.status;
  evidenceStatus.className =
    evidence.status === "RECEIVER TRANSPORT OBSERVED" && evidence.positiveControl
      ? "status ok"
      : "status warn";
  evidenceSummary.textContent = JSON.stringify(evidence, null, 2);
  return evidence;
}

async function refreshStats() {
  if (peerConnection === null || statsInFlight) return;
  statsInFlight = true;
  try {
    const report = await peerConnection.getStats();
    const inbound = extractInboundVideoStats(report);
    lastInbound = inbound;
    if (inbound !== null) {
      transportLog.record("inbound-stats", { id: inbound.id });
    }
    renderStats();
    renderEvidence();
    renderTransport();
  } catch (error) {
    transportLog.record("stats-error", {
      message: error instanceof Error ? error.message : String(error)
    });
    setStatus("Could not read receiver statistics. No evidence is inferred.", "warn");
  } finally {
    statsInFlight = false;
  }
}

function scheduleFrameCounter() {
  if (typeof receiverVideo.requestVideoFrameCallback !== "function") return;
  frameCallbackId = receiverVideo.requestVideoFrameCallback(() => {
    frameCounter += 1;
    if (frameCounter % 30 === 0) {
      void refreshStats();
    }
    scheduleFrameCounter();
  });
}

function ensurePeerConnection() {
  if (peerConnection !== null) return peerConnection;

  peerConnection = new RTCPeerConnection({ iceServers: [] });
  peerConnection.ontrack = (event) => {
    if (event.track.kind !== "video") {
      event.track.stop();
      transportLog.record("non-video-track-rejected", { kind: event.track.kind });
      setStatus("A non-video track was rejected. Video only is required.", "warn");
      return;
    }

    receivedStream = new MediaStream([event.track]);
    receiverVideo.srcObject = receivedStream;
    void receiverVideo.play().catch((error) => {
      transportLog.record("receiver-play-failed", {
        message: error instanceof Error ? error.message : String(error)
      });
    });
    event.track.addEventListener("ended", () => {
      transportLog.record("received-track-ended", {});
      lastInbound = null;
      renderStats();
      setStatus("The received video track ended. Live receiver evidence is cleared; record stats before stopping.", "warn");
      renderEvidence();
    });
    transportLog.record("receiver-track", { kind: event.track.kind });
    setStatus("Received video track. Waiting for inbound RTP statistics...");
    scheduleFrameCounter();
    void refreshStats();
  };

  peerConnection.onicecandidate = (event) => {
    if (event.candidate === null || channel === null) return;
    channel.postMessage({
      type: "candidate",
      candidate: event.candidate.candidate,
      sdpMid: event.candidate.sdpMid,
      sdpMLineIndex: event.candidate.sdpMLineIndex
    });
  };

  peerConnection.onconnectionstatechange = () => {
    if (peerConnection === null) return;
    transportLog.record("receiver-connection", {
      state: peerConnection.connectionState
    });
    setStatus(`Receiver peer state: ${peerConnection.connectionState}`);
    renderTransport();
  };

  return peerConnection;
}

async function handleSignal(rawMessage) {
  const parsed = validateSignalMessage(rawMessage);
  if (!parsed.ok) {
    transportLog.record("signal-rejected", { reason: parsed.reason });
    renderTransport();
    return;
  }
  const message = parsed.message;

  if (message.type === "offer") {
    if (
      peerConnection !== null &&
      peerConnection.remoteDescription?.sdp === message.sdp &&
      peerConnection.localDescription !== null
    ) {
      transportLog.record("duplicate-offer-ignored", {});
      renderTransport();
      return;
    }
    const peer = ensurePeerConnection();
    await peer.setRemoteDescription({ type: "offer", sdp: message.sdp });
    for (const candidate of candidates.markRemoteDescriptionSet()) {
      await peer.addIceCandidate(candidate);
    }
    const answer = await peer.createAnswer();
    await peer.setLocalDescription(answer);
    channel.postMessage({
      type: "answer",
      sdp: peer.localDescription.sdp
    });
    transportLog.record("offer-applied", {});
    setStatus("Offer received and answer sent. Waiting for inbound video frames.");
    await refreshStats();
  } else if (message.type === "candidate") {
    const candidate = {
      candidate: message.candidate,
      sdpMid: message.sdpMid ?? null,
      sdpMLineIndex: message.sdpMLineIndex ?? null
    };
    if (peerConnection !== null && peerConnection.remoteDescription !== null) {
      await peerConnection.addIceCandidate(candidate);
    } else {
      candidates.add(candidate);
    }
    transportLog.record("sender-candidate", {
      queued: peerConnection === null || peerConnection.remoteDescription === null
    });
  } else if (message.type === "bye") {
    transportLog.record("sender-bye", {});
    lastInbound = null;
    renderStats();
    renderEvidence();
    setStatus("The sender closed the local peer. Live receiver evidence is cleared; record stats before stopping.", "warn");
  }
  renderTransport();
}

function connectChannel() {
  if (channel !== null) {
    channel.close();
  }
  channel = new BroadcastChannel(SIGNALING_CHANNEL);
  channel.addEventListener("message", (event) => {
    handleSignal(event.data).catch((error) => {
      transportLog.record("signal-error", {
        message: error instanceof Error ? error.message : String(error)
      });
      setStatus("A local receiver signalling error occurred; no evidence is claimed.", "warn");
      renderTransport();
    });
  });
  channel.postMessage({ type: "receiver-ready" });
  transportLog.record("receiver-ready-sent", {});
}

function cleanupReceiver(reason) {
  if (frameCallbackId !== null && typeof receiverVideo.cancelVideoFrameCallback === "function") {
    receiverVideo.cancelVideoFrameCallback(frameCallbackId);
  }
  frameCallbackId = null;
  frameCounter = 0;

  if (receivedStream !== null) {
    receivedStream.getTracks().forEach((track) => track.stop());
  }
  if (peerConnection !== null) {
    peerConnection.close();
  }
  if (channel !== null) {
    channel.close();
  }
  peerConnection = null;
  channel = null;
  receivedStream = null;
  receiverVideo.srcObject = null;
  lastInbound = null;
  candidates.reset();
  transportLog.record("receiver-cleanup", { reason });
}

function resetReceiver() {
  cleanupReceiver("manual-reset");
  roiSamples = [];
  renderStats();
  renderEvidence();
  renderTransport();
  connectChannel();
  setStatus("Receiver reset. Request an offer from the sender tab when ready.");
}

function readRoiInputs() {
  const x = Number(document.getElementById("roi-x").value);
  const y = Number(document.getElementById("roi-y").value);
  const width = Number(document.getElementById("roi-w").value);
  const height = Number(document.getElementById("roi-h").value);
  if (
    !Number.isInteger(x) ||
    !Number.isInteger(y) ||
    !Number.isInteger(width) ||
    !Number.isInteger(height) ||
    x < 0 ||
    y < 0 ||
    width < 1 ||
    height < 1
  ) {
    throw new Error("ROI requires non-negative integers and positive dimensions");
  }
  return { x, y, width, height };
}

function sampleRoiNow() {
  if (lastInbound === null || (lastInbound.framesDecoded ?? 0) <= 0) {
    setStatus("No inbound decoded frames are available; ROI sampling is not receiver evidence.", "warn");
    return;
  }
  if (receiverVideo.readyState < 2 || receiverVideo.videoWidth <= 0) {
    setStatus("The receiver video has no current frame to sample.", "warn");
    return;
  }

  try {
    const roi = readRoiInputs();
    if (
      roi.x + roi.width > receiverVideo.videoWidth ||
      roi.y + roi.height > receiverVideo.videoHeight
    ) {
      throw new Error("ROI lies outside the current receiver video dimensions");
    }

    const crop = document.createElement("canvas");
    crop.width = roi.width;
    crop.height = roi.height;
    const cropContext = crop.getContext("2d", { willReadFrequently: true });
    cropContext.drawImage(
      receiverVideo,
      roi.x,
      roi.y,
      roi.width,
      roi.height,
      0,
      0,
      roi.width,
      roi.height
    );
    const rgba = cropContext.getImageData(0, 0, roi.width, roi.height).data;
    const stats = computeRoiStats(rgba, roi.width, roi.height);

    roiSamples.push({
      label: document.getElementById("roi-label").value,
      nearMarkerFraction: stats.nearMarkerFraction,
      sampledAt: new Date().toISOString(),
      width: roi.width,
      height: roi.height
    });

    roiCanvas.width = roi.width;
    roiCanvas.height = roi.height;
    const previewContext = roiCanvas.getContext("2d");
    previewContext.drawImage(crop, 0, 0);

    roiStatsOutput.textContent =
      `nearMarkerFraction=${stats.nearMarkerFraction.toFixed(4)} ` +
      `nearMarkerPixels=${stats.nearMarkerPixels}/${stats.pixelCount}`;
    transportLog.record("roi-sample", {
      label: roiSamples.at(-1).label,
      nearMarkerFraction: roiSamples.at(-1).nearMarkerFraction
    });
    renderEvidence();
    renderTransport();
    setStatus("ROI sample recorded. Cropped marker ROI only; no full frame was retained.");
  } catch (error) {
    setStatus(
      error instanceof Error ? error.message : "ROI sampling failed without a measurement.",
      "warn"
    );
  }
}

receiverVideo.addEventListener("click", (event) => {
  if (receiverVideo.videoWidth <= 0 || receiverVideo.videoHeight <= 0) return;
  const rect = receiverVideo.getBoundingClientRect();
  if (rect.width <= 0 || rect.height <= 0) return;
  const width = 48;
  const height = 48;
  const sourceX = ((event.clientX - rect.left) / rect.width) * receiverVideo.videoWidth;
  const sourceY = ((event.clientY - rect.top) / rect.height) * receiverVideo.videoHeight;
  const x = Math.min(
    Math.max(Math.floor(sourceX - width / 2), 0),
    Math.max(receiverVideo.videoWidth - width, 0)
  );
  const y = Math.min(
    Math.max(Math.floor(sourceY - height / 2), 0),
    Math.max(receiverVideo.videoHeight - height, 0)
  );
  document.getElementById("roi-x").value = String(x);
  document.getElementById("roi-y").value = String(y);
  document.getElementById("roi-w").value = String(width);
  document.getElementById("roi-h").value = String(height);
  setStatus("ROI placed from the receiver video click. Sample it to record only the crop.");
});

document.getElementById("request-offer").addEventListener("click", () => {
  if (channel === null) {
    connectChannel();
  } else {
    channel.postMessage({ type: "receiver-ready" });
  }
  setStatus("Receiver ready message sent. Waiting for the sender offer.");
});

document.getElementById("refresh-stats").addEventListener("click", () => {
  void refreshStats();
});

document.getElementById("reset-receiver").addEventListener("click", resetReceiver);

document.getElementById("sample-roi").addEventListener("click", sampleRoiNow);

document.getElementById("snapshot-focus").addEventListener("click", () => {
  focusHandle.snapshotNow();
  renderFocus();
  renderEvidence();
});

window.addEventListener("focus", renderFocus);
window.addEventListener("blur", renderFocus);
document.addEventListener("visibilitychange", renderFocus);

renderFocus();
renderStats();
renderEvidence();
renderTransport();
connectChannel();
