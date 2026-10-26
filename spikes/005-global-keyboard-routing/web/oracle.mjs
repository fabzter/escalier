const LISTENER_OPTIONS = { capture: true, passive: true };

const field = document.getElementById("test-field");
const counters = new Map();
let resetSeen = false;

const MODIFIER_KEYS = new Set(["Shift", "Control", "Alt", "Meta", "CapsLock", "Fn"]);

const SELECTED_KEYS = new Map([
  [75, "K"],
  [27, "Escape"],
  [65, "A"],
  [8, "Backspace"],
  [13, "Enter"],
  [9, "Tab"],
  [37, "ArrowLeft"],
  [38, "ArrowUp"],
  [39, "ArrowRight"],
  [40, "ArrowDown"],
  [36, "Home"],
  [35, "End"],
  [33, "PageUp"],
  [34, "PageDown"]
]);

function bump(id) {
  const next = (counters.get(id) ?? 0) + 1;
  counters.set(id, next);
  const node = document.getElementById(id);
  if (node) {
    node.textContent = String(next);
  }
}

function resetCounters() {
  for (const id of counters.keys()) {
    const node = document.getElementById(id);
    if (node) {
      node.textContent = "0";
    }
  }
  counters.clear();
}

function observe(type, handler) {
  window.addEventListener(type, handler, LISTENER_OPTIONS);
}

function selectedLabel(event) {
  return SELECTED_KEYS.get(event.keyCode) ?? "other";
}

function isModifierEvent(event) {
  return MODIFIER_KEYS.has(event.key);
}

function onKeyDown(event) {
  bump("keydown-total");
  if (isModifierEvent(event)) {
    bump("modifier-down");
    return;
  }
  bump(`selected-down-${selectedLabel(event)}`);
}

function onKeyUp(event) {
  bump("keyup-total");
  if (isModifierEvent(event)) {
    bump("modifier-up");
    return;
  }
  bump(`selected-up-${selectedLabel(event)}`);
}

function updatePreconditions() {
  const focused = document.hasFocus();
  const visible = document.visibilityState === "visible";
  const fieldFocused = document.activeElement === field;

  const hasFocusNode = document.getElementById("has-focus");
  const visibilityNode = document.getElementById("visibility-state");
  const fieldNode = document.getElementById("field-focused");
  const stateNode = document.getElementById("precondition-state");

  if (hasFocusNode) {
    hasFocusNode.textContent = focused ? "yes" : "no";
  }
  if (visibilityNode) {
    visibilityNode.textContent = document.visibilityState;
  }
  if (fieldNode) {
    fieldNode.textContent = fieldFocused ? "yes" : "no";
  }
  if (stateNode) {
    const ready = focused && visible && fieldFocused;
    stateNode.textContent = ready
      ? "READY — focused visible field. A zero count is meaningful only for this state."
      : "INVALID — focus the visible test field and keep this tab active before a case.";
  }
}

observe("keydown", onKeyDown);
observe("keyup", onKeyUp);
observe("beforeinput", () => bump("beforeinput-total"));
observe("input", () => bump("input-total"));
observe("compositionstart", () => bump("compositionstart-total"));
observe("compositionend", () => bump("compositionend-total"));
observe("focus", () => {
  bump("focus-total");
  updatePreconditions();
});
observe("blur", () => {
  bump("blur-total");
  updatePreconditions();
});
observe("visibilitychange", () => {
  bump(document.visibilityState === "visible" ? "visible-total" : "hidden-total");
  updatePreconditions();
});
observe("scroll", () => bump("scroll-total"));

function onResetClick() {
  resetCounters();
  resetSeen = true;
  const stateNode = document.getElementById("reset-state");
  if (stateNode) {
    stateNode.textContent = resetSeen
      ? "Counters reset in this session. Refocus the test field before continuing."
      : "Counters not reset in this load.";
  }
  updatePreconditions();
}

const resetButton = document.getElementById("reset");
resetButton.addEventListener("click", onResetClick, LISTENER_OPTIONS);

setInterval(updatePreconditions, 1000);
updatePreconditions();
