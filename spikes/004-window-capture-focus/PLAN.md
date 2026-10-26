# Spike 004 — synthetic window, focus and capture harness

Owner approved parallel stealth spikes on 2026-10-26. This is a local synthetic test harness, not interview participation or a claim of invisibility. Authority: [requirements](../../docs/requirements.md) and [15-group inventory](../../docs/analysis/2026-10-26-live-asr-and-browser-privacy.md). Prefer invisible where observed possible and disguised where not; report unsupported gaps honestly. Firefox remains conditional per HackerRank's published experience matrix.

## Bounded outcome

Build a tiny dependency-free Swift/AppKit fixture with:

- A plainly identified Escalier test control window, protected-marker panel and unprotected control marker, all synthetic.
- Explicit test configurations for sharingType none versus readOnly, normal versus nonactivating panel, accessory app policy, click-through and a representative auxiliary surface. Inspect requested/read-back state through narrow observations; do not infer remote receiver pixels from an NSWindow flag.
- A clearly labelled, owned generic display title for a disguise experiment; no impersonation of a trusted app, no TCC bypass/private APIs, no unsigned-system modifications or process-name injection. Build-time identity remains a documented future comparison, not assumed implemented.
- A local static browser fixture exposing focus/blur/visibility event logging plus sender/receiver views for a browser getDisplayMedia/WebRTC capture test. A receiver must display actual received frames; a sender preview alone is not receiver evidence. Keep all signaling in a single local origin/in-memory channel where possible, no external servers or uploads. User explicitly chooses capture source and grants any browser/OS permission.

No microphone, live audio, real interview page or private files. Do not implement screenshot automation or try to suppress a browser/OS permission prompt. Source selection is manual at point of risk. A website cannot prove absence of undisclosed HackerRank server-side signals. Modern screen capture may ignore legacy exclusion flags; test selected external-window and entire-display separately.

## File ownership

Worker owns this directory's `README.md`, `Sources/**`, `Tests/**`, `web/**`, `tools/**` and `review/implementation-report.md`. Coordinator owns PLAN/review records. No cross-editing other spikes or root docs, commits or subagents.

## Sequence and tests

1. Official AppKit/browser API docs first; relevant authorized Natively source may inform mechanism research but no code copying. Use public APIs; record any unavailable mechanism as a gap.
2. RED tests for pure window-policy configuration mapping, configuration/report identity, marker/control separation and state/readback serialization. If WebRTC helpers have pure state logic, test deterministic event ordering/cleanup using installed runtimes without new dependencies. No mocked green claim of receiver-pixel behavior.
3. Implement native fixture + local browser fixtures, build confined under .tools/.build with installed compiler. Provide explicit start-server command bound to 127.0.0.1, no automatic server start or external requests. Do not launch/drive GUI or trigger getDisplayMedia in a worker.
4. GREEN tests/native compile and static JS/HTML validation, exact commands/results. Browser and native runtime cases remain NOT RUN until interactive testing. Do not launch apps or automate desktop via Bash/AppleScript. Actual UI control later uses computer with live task confirmation.
5. Retain a findings/evidence template with exact OS/browser/source/window-policy, intended/actual readback, private marker receiver-pixel observation, control marker observation and focus-event log. Include selected browser-window versus full-display, overlap/nonoverlap, protected/control/auxiliary surfaces and Chrome/Firefox compatibility notes. No claim based solely on sender preview or transport success.

## Success boundary

Buildable reproducible harness, unit-tested configuration, manual runtime matrix and honest untested limitations. Runtime stealth is not established until independent receiver pixels and focus logs are captured with explicit permissions. This task does not authorize private APIs, unattended permission grants, real assessment access or user interaction interception.
