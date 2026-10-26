# Spike 004 — findings and evidence template

Date: 2026-10-26. Status: **implementation/headless/static only; runtime matrix NOT
RUN.** This file is a template for the later interactive session. It contains no
receiver-pixel, focus, click-through, Dock-identity or stealth finding. Build/test
passes are not runtime evidence.

Labels used: **LOCALLY-OBSERVED** only for the build/test/audit results recorded in
`review/implementation-report.md`; **NOT RUN** for every interactive cell here;
**N/A** only where a cell structurally cannot show the marker (explain why).

## Non-findings

- No receiver was attached to a real display capture in this pass.
- No browser, app, server or permission prompt was launched.
- No microphone/audio path was used.
- No screen recording, full frame, screenshot or raw frame was retained.
- No claim is made about HackerRank, ScreenCaptureKit composition, Firefox
  compatibility or universal invisibility.
- The native readback is requested/observed AppKit state only. It does not prove
  what another process captures.

## Required session header

Fill every field; do not leave a field silently blank. Use `null` plus an
explanation when a value is unavailable.

| Field | Value |
| --- | --- |
| macOS version/build | `NOT RUN` |
| Hardware/architecture | `NOT RUN` |
| Fixture source hash / commit | `NOT RUN` |
| Fixture build kind (`app-bundle`/unbundled) | `NOT RUN` |
| Fixture bundle signature/identity context | Ad-hoc signed and strict-verified locally; not Developer ID/notarized; launch/TCC/stable identity NOT RUN |
| Browser name and exact version/build | `NOT RUN` |
| Browser channel/profile | `NOT RUN` |
| Display count, arrangement, main display, scale factors | `NOT RUN` |
| Selected source kind (entire display / selected window / other) | `NOT RUN` |
| Source dimensions and pixel scale | `NOT RUN` |
| Capture constraints (`video: true, audio: false`) | `NOT RUN` |
| Secure context (`window.isSecureContext`) | `NOT RUN` |
| Transient user activation (`navigator.userActivation.isActive`) | `NOT RUN` |
| Permission state and who granted it | `NOT RUN` |
| Audio track count observed | `NOT RUN` |
| External request count (must be 0; record method) | `NOT RUN` |
| Clean-display protocol completed | `NOT RUN` |
| Native readback JSON attachment/quote | `NOT RUN` |
| Focus log attachment/quote | `NOT RUN` |
| Receiver evidence summary | `NOT RUN` |
| ROI sample log | `NOT RUN` |
| OS/browser permission revocation completed | `NOT RUN` |

## Evidence object template

Use the actual values from the receiver page, focus log and native stdout. Keep
`null` for unavailable measurements; never substitute a fabricated zero. The
receiver page's summary already excludes raw pixels.

```json
{
  "cell_id": "NOT RUN",
  "fixture": {
    "commit_or_source_hash": null,
    "build_kind": null,
    "bundle_identifier": null
  },
  "environment": {
    "macos": null,
    "browser": null,
    "display_arrangement": null,
    "scale_factors": null,
    "source_kind": null,
    "source_dimensions": null,
    "secure_context": null,
    "user_activation": null,
    "permission_state": null,
    "clean_display_protocol": null
  },
  "capture": {
    "audio_track_count": null,
    "external_request_count": null,
    "selected_source_was_manual": null
  },
  "native_readback": {
    "worker_runtime_status": "NOT RUN IN WORKER",
    "app": null,
    "windows": [],
    "missing_window_roles": [],
    "policy_mismatches": [],
    "lifecycle_journal": [],
    "counters": null
  },
  "receiver": {
    "status": "NO RECEIVER EVIDENCE",
    "inbound": {
      "framesDecoded": null,
      "bytesReceived": null,
      "frameWidth": null,
      "frameHeight": null,
      "framesPerSecond": null,
      "timestamp": null
    },
    "video": {
      "width": null,
      "height": null,
      "currentTime": null,
      "readyState": null
    },
    "roi_samples": [],
    "positive_control": null
  },
  "focus_log": [],
  "interpretation": "NOT RUN",
  "limitations": []
}
```

A receiver row is invalid as evidence if `framesDecoded`, `bytesReceived`, or
`timestamp` is null/zero/invalid, frame or video dimensions are null/zero, transport
stats are missing, or the only video is a sender preview. A marker-absence
interpretation is invalid unless the sharing-readOnly control is positively visible
in the same cell. If occlusion or invisibility is recorded for either marker, both
markers must be positively visible before treatment absence is interpreted; an
occluded cell is not an exclusion result. A selected external window with both
markers outside the source is N/A/control-absent, never “sharing-none excluded”.

## Runtime matrix — all rows NOT RUN

One row per cell. Add rows rather than merging cells. Preserve failed/cancelled
cells.

| Cell | Source/overlap | Treatment observation (sharing-none) | Control observation (sharing-readOnly) | Receiver transport + timestamps | ROI samples | Focus/lifecycle | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1a | Entire display, markers non-overlapping/adjacent, browser frontmost | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| 1b | Entire display, marker overlapping browser content, both markers visible | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| 2 | Selected browser window; both markers outside source | N/A — control absent | N/A — control absent | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| 3 | Selected fixture window; marker inside source | NOT RUN | NOT RUN / same-window control possibly N/A | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| 4 | Both markers occluded/behind browser | NOT RUN (occluded) | NOT RUN (occluded) | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| 5a | Browser active; normal panel shown | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| 5b | Browser active; nonactivating panel shown | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| 6a | Native click-through panel intercepts clicks | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| 6b | Native click-through panel passes clicks to browser underlay | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| 7 | Lifecycle show/hide/reshow/activate/deactivate/accessory | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| 8 | Auxiliary panel (separate row) | NOT RUN | N/A — separate surface | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| 9 | Entire-display audio/privacy checks | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |

## Native readback requested/observed template

One row per created surface. Copy the exact requested/observed values from the
readback JSON; do not infer a pass from a matching flag. `missing` and `mismatches`
must be recorded even when empty.

| Role | Requested sharing | Observed sharing | Requested style/level | Observed style/level | Requested activation/click-through | Observed activation/click-through | Missing roles | Mismatches | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| control-window | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| marker-sharing-none | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| marker-sharing-read-only | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| auxiliary-panel | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| click-through-panel | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |

## Focus oracle template

Record before and after every panel action. Page-observable values and native
readback are separate columns; do not infer one from the other.

| Time | Action | Fixture app active | App activation policy | Key window role | Main window role | Panel isKeyWindow | Page visibilityState | Page hasFocus | Page focus/blur/visibility events |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |

Also record the frontmost application identity when available. If it is unavailable,
write `unavailable` and why; do not request more permissions to obtain it.

## Click-through oracle template

| Mode | Native panel `ignoresMouseEvents` | Inert panel hits | Browser inert underlay hits | Real side effects | Notes |
| --- | --- | --- | --- | --- | --- |
| Intercept | `false` | NOT RUN | NOT RUN | None | NOT RUN |
| Pass-through | `true` | NOT RUN | NOT RUN | None | NOT RUN |

The browser underlay count is entered manually from `index.html`; there is no
cross-process automation. A hit in either counter is an inert test hit only.

## Lifecycle oracle template

Run in order. Capture a readback after every stage; do not merge stages.

| Stage | Requested summary | Observed sharing/style/level | App activation policy requested/observed | Missing roles | Mismatches | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| create markers | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| show markers | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| hide markers | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| reshow markers | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| activate fixture | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| deactivate fixture | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| switch accessory | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| switch regular | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |

## Clean-display and privacy protocol (before any capture)

1. Save and close private windows, email, messaging, calendar, documents and any
   unrelated tab. Quit apps that might display private content.
2. Turn on a quiet state: notifications off, Do Not Disturb/Focus on, no pending
   banners or system dialogs in the capture area.
3. Prefer a dedicated Space/display. Record the number of displays, their
   arrangement, scale factors and whether the browser is on the main display.
4. Keep the native control window and stop/close controls reachable. Know how the
   browser's sharing indicator stops a stream.
5. Explain in advance that macOS Screen Recording permission is persistent TCC
   state and must be revoked when finished (System Settings → Privacy & Security →
   Screen Recording). The browser may also remember a per-origin/source choice.
6. A human chooses the source and grants any browser/OS permission. The fixture or
   agent must never select a picker item or grant a TCC/provider prompt unattended.
7. Start capture only by pressing the sender's start button. Verify zero audio
   tracks and no external request before recording any result.
8. Capture the receiver evidence summary and ROI samples **while the stream is
   live**. The receiver clears live transport evidence when the track ends or the
   sender closes; do not record a cleared cell as a positive result.
9. Stop the stream, revoke permission, close the tabs/fixture and confirm no raw
   frame was saved or exported. Only ROI statistics and metadata are retained.

## Browser compatibility notes

- Chrome/Edge are the primary candidates. Firefox is conditional; HackerRank's
  public matrix says Firefox is not supported for the New Interview Experience.
  That is a product compatibility constraint, not a reason to assume legacy capture
  or invisibility.
- Firefox 132+ has macOS screen/window picker support, and modern capture backends
  may use ScreenCaptureKit-like composition. Do not infer exclusions from the
  browser name.
- Record the exact browser build, source type, picker choice, dimensions and
  whether the source was an entire display or one window. A sender preview alone
  is never receiver evidence.
- The static harness rejects external URLs/STUN/TURN/audio/autostart patterns, but
  a clean static audit is not a runtime network capture. If the later session wants
  a network oracle, use an independently approved local observation; do not add
  uploads or third-party services here.
- If `navigator.userActivation` is unavailable, the capture guard fails closed.
  Record that as a limitation; do not bypass it. If `requestVideoFrameCallback` is
  unavailable, use the manual stats refresh and keep missing stats at **NO RECEIVER
  EVIDENCE**.

## Limitations and non-transferability

- All runtime cells above remain **NOT RUN**; no stealth, invisibility, focus,
  click-through, Dock, process-name or identity result follows.
- These findings are specific to Spike 004's fixture and configuration. They do not
  validate Spike 003, Natively parity, transcription/ASR, OMP integration or any
  HackerRank server-side signal.
- A synthetic local observation cannot establish absence of undisclosed
  third-party server-side signals or universal invisibility.
- The app bundle built by the worker is ad-hoc signed and strict-verified locally
  for launch tests, but it is not Developer ID/notarized and was not launched.
  Ad-hoc identity is not stable across rebuilds; Gatekeeper, TCC attribution,
  bundle identity and launch behaviour are untested. No certificate/Keychain/
  trust/Gatekeeper/TCC/quarantine changes were made.
- Missing values are `null`/`NOT RUN`, not zeros. Do not present a partial matrix as
  full coverage.
