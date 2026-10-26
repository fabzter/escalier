import {
  guardCaptureRequest,
  inspectVideoOnlyStream
} from "./capture-guard.mjs";
import { attachFocusLog, createFocusLog } from "./focus-log.mjs";
import {
  SIGNALING_CHANNEL,
  createCandidateQueue,
  createCleanupLedger,
  createEventLog,
  validateSignalMessage
} from "./transport-core.mjs";

const preview = document.getElementById("sender-preview");
const senderStatus = document.getElementById("sender-status");
const senderLog = document.getElementById("sender-log");
const focusOutput = document.getElementById("focus-log");

const focusLog = createFocusLog({ limit: 400 });
const focusHandle = attachFocusLog({ win: window, doc: document, log: focusLog });
const transportLog = createEventLog({ limit: 400 });
const remoteCandidates = createCandidateQueue();

let stream = null;
let peerConnection = null;
let channel = null;
let receiverReady = false;
let remoteDescriptionSet = false;
let offerInFlight = false;
let stopping = false;

function setStatus(message, kind = "") {
  senderStatus.textContent = message;
  senderStatus.className = kind.length > 0 ? `status ${kind}` : "status";
}

function render() {
  focusOutput.textContent = JSON.stringify(focusLog.toJSON(), null, 2);
  senderLog.textContent = JSON.stringify(
    { focus: focusLog.toJSON(), transport: transportLog.toJSON() },
    null,
    2
  );
}

function openChannel() {
  if (channel !== null) {
    channel.close();
  }
  channel = new BroadcastChannel(SIGNALING_CHANNEL);
  channel.addEventListener("message", (event) => {
    handleSignal(event.data).catch((error) => {
      transportLog.record("signal-error", {
        message: error instanceof Error ? error.message : String(error)
      });
      setStatus("A local signalling error occurred; no capture claim is made.", "warn");
      render();
    });
  });
  transportLog.record("channel-open", { channel: SIGNALING_CHANNEL });
}

async function announceOfferIfReady() {
  if (peerConnection === null || stream === null || channel === null || offerInFlight) {
    return;
  }
  offerInFlight = true;
  try {
    if (peerConnection.localDescription !== null) {
      channel.postMessage({
        type: "offer",
        sdp: peerConnection.localDescription.sdp
      });
    } else {
      const offer = await peerConnection.createOffer();
      await peerConnection.setLocalDescription(offer);
      channel.postMessage({
        type: "offer",
        sdp: peerConnection.localDescription.sdp
      });
    }
    transportLog.record("offer-sent", { receiverReady });
    setStatus("Offer sent over the local signal channel. Waiting for the receiver answer.");
  } catch (error) {
    transportLog.record("offer-error", {
      message: error instanceof Error ? error.message : String(error)
    });
    setStatus("Could not create or send the local offer. No capture claim is made.", "warn");
  } finally {
    offerInFlight = false;
    render();
  }
}

function setupPeerConnection() {
  peerConnection = new RTCPeerConnection({ iceServers: [] });
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
    transportLog.record("sender-connection", {
      state: peerConnection.connectionState
    });
    setStatus(`Sender peer state: ${peerConnection.connectionState}`);
    render();
  };

  const videoTrack = stream.getVideoTracks()[0];
  peerConnection.addTrack(videoTrack, stream);
  videoTrack.addEventListener("ended", () => {
    stopCapture("browser-ended-capture");
  });
}

async function handleSignal(rawMessage) {
  const parsed = validateSignalMessage(rawMessage);
  if (!parsed.ok) {
    transportLog.record("signal-rejected", { reason: parsed.reason });
    render();
    return;
  }
  const message = parsed.message;

  if (message.type === "receiver-ready") {
    receiverReady = true;
    transportLog.record("receiver-ready", {});
    await announceOfferIfReady();
  } else if (message.type === "answer") {
    if (peerConnection === null) {
      transportLog.record("answer-without-peer", {});
    } else {
      await peerConnection.setRemoteDescription({
        type: "answer",
        sdp: message.sdp
      });
      remoteDescriptionSet = true;
      for (const candidate of remoteCandidates.markRemoteDescriptionSet()) {
        await peerConnection.addIceCandidate(candidate);
      }
      transportLog.record("answer-applied", {});
    }
  } else if (message.type === "candidate") {
    const candidate = {
      candidate: message.candidate,
      sdpMid: message.sdpMid ?? null,
      sdpMLineIndex: message.sdpMLineIndex ?? null
    };
    if (peerConnection !== null && remoteDescriptionSet) {
      await peerConnection.addIceCandidate(candidate);
    } else {
      remoteCandidates.add(candidate);
    }
    transportLog.record("receiver-candidate", { queued: !remoteDescriptionSet });
  } else if (message.type === "bye") {
    transportLog.record("receiver-bye", {});
    setStatus("Receiver closed its peer; the local sender preview remains until you stop it.", "warn");
  }
  render();
}

export async function startUserChosenCapture() {
  if (stream !== null || stopping) return;

  const preflight = guardCaptureRequest({
    isSecureContext: window.isSecureContext,
    userActivationActive: navigator.userActivation?.isActive === true,
    audioRequested: false,
    mediaDevicesAvailable:
      typeof navigator.mediaDevices?.getDisplayMedia === "function"
  });
  if (!preflight.ok) {
    transportLog.record("capture-blocked", { reason: preflight.reason });
    setStatus(
      `Capture blocked by the local preflight: ${preflight.reason}. No media request was made.`,
      "warn"
    );
    render();
    return;
  }

  setStatus("Waiting for your manual source choice and any browser/OS permission...");
  let rawStream;
  try {
    rawStream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: false });
  } catch (error) {
    transportLog.record("capture-cancelled", {
      message: error instanceof Error ? error.message : String(error)
    });
    setStatus("Capture was cancelled or denied. Nothing was retained.", "warn");
    render();
    return;
  }

  const videoOnly = inspectVideoOnlyStream(rawStream);
  if (!videoOnly.ok) {
    rawStream.getTracks().forEach((track) => track.stop());
    transportLog.record("capture-rejected", { reason: videoOnly.reason });
    setStatus(
      `The chosen stream was rejected by the video-only check: ${videoOnly.reason}.`,
      "warn"
    );
    render();
    return;
  }

  stream = rawStream;
  preview.srcObject = stream;
  try {
    await preview.play();
  } catch (error) {
    transportLog.record("preview-play-failed", {
      message: error instanceof Error ? error.message : String(error)
    });
  }

  receiverReady = false;
  remoteDescriptionSet = false;
  remoteCandidates.reset();
  openChannel();
  setupPeerConnection();
  document.getElementById("start-capture").disabled = true;
  document.getElementById("stop-capture").disabled = false;
  setStatus("Video-only stream acquired. Local offer announced; receiver stats are separate.");
  render();
  await announceOfferIfReady();
}

function stopCapture(reason) {
  if (stopping) return;
  stopping = true;
  if (channel !== null) {
    try {
      channel.postMessage({ type: "bye" });
    } catch {
      // The channel may already be closed; cleanup below still runs.
    }
  }

  const ledger = createCleanupLedger({
    stopTracks: () => {
      if (stream !== null) {
        stream.getTracks().forEach((track) => track.stop());
      }
    },
    closePeer: () => {
      if (peerConnection !== null) {
        peerConnection.close();
      }
    },
    closeChannel: () => {
      if (channel !== null) {
        channel.close();
      }
    },
    log: (entry) => transportLog.record("cleanup", entry)
  });
  const outcome = ledger.run(reason);
  for (const action of outcome.actions) {
    if (!action.ok) {
      transportLog.record("cleanup-error", action);
    }
  }

  stream = null;
  peerConnection = null;
  channel = null;
  receiverReady = false;
  remoteDescriptionSet = false;
  remoteCandidates.reset();
  preview.srcObject = null;
  document.getElementById("start-capture").disabled = false;
  document.getElementById("stop-capture").disabled = true;
  setStatus(`Capture stopped (${reason}). No stream or frame is retained.`, "warn");
  render();
  stopping = false;
}

document.getElementById("start-capture").addEventListener("click", () => {
  void startUserChosenCapture();
});

document.getElementById("stop-capture").addEventListener("click", () => {
  stopCapture("user-stop");
});

document.getElementById("snapshot-focus").addEventListener("click", () => {
  focusHandle.snapshotNow();
  render();
});

window.addEventListener("focus", render);
window.addEventListener("blur", render);
document.addEventListener("visibilitychange", render);

openChannel();
render();
