import { attachFocusLog, createFocusLog } from "./focus-log.mjs";

const focusLog = createFocusLog({ limit: 500 });
const focusOutput = document.getElementById("focus-log");
const focusHandle = attachFocusLog({ win: window, doc: document, log: focusLog });

let underlayHits = 0;
const underlayCount = document.getElementById("underlay-count");

function renderFocusLog() {
  focusOutput.textContent = JSON.stringify(focusLog.toJSON(), null, 2);
}

function renderUnderlayCount() {
  underlayCount.textContent = String(underlayHits);
}

document.getElementById("snapshot-focus").addEventListener("click", () => {
  focusHandle.snapshotNow();
  renderFocusLog();
});

document.getElementById("clear-focus-log").addEventListener("click", () => {
  focusLog.clear();
  renderFocusLog();
});

document.getElementById("underlay-button").addEventListener("click", () => {
  underlayHits += 1;
  renderUnderlayCount();
});

window.addEventListener("focus", renderFocusLog);
window.addEventListener("blur", renderFocusLog);
document.addEventListener("visibilitychange", renderFocusLog);

renderFocusLog();
renderUnderlayCount();
