# Spike 004 — synthetic window, focus and capture harness

Status: **implementation, headless tests and static audits only. The interactive
runtime matrix is NOT RUN.** This is a local synthetic fixture, not interview
participation, not a production UI and not a stealth claim. Neither a build nor a
unit test proves receiver pixels, focus behaviour or invisibility.

Authoritative scope: [`PLAN.md`](PLAN.md) and the binding
[`preflight resolutions`](../003-native-shell-ui/review/preflight-resolutions.md).
This directory is independently implemented; its evidence does **not** validate
Spike 003.

## What is here

| Path | Purpose |
| --- | --- |
| `Sources/CapturePolicy/` | Dependency-free pure Swift policy/readback/evidence model, unit tested. |
| `Sources/EscalierCaptureFixture/` | Programmatic AppKit fixture: control window, identical marker pair, lazy auxiliary panel, click-through panel, lifecycle/readback controls. |
| `Tests/CapturePolicyTests/` | 54 headless Swift tests. No `NSApplication`, `NSWindow` or GUI is created. |
| `web/` | Local static sender/receiver fixture plus focus log and inert underlay. |
| `web/tests/` | 43 deterministic Node tests for pure browser logic. |
| `tools/serve-local.mjs` | Explicit manual `127.0.0.1` static server. It never launches a browser and never starts automatically. |
| `tools/web-audit.mjs`, `tools/native-audit.mjs`, `tools/validate.mjs` | Static no-external/no-audio/no-autostart/public-API audits, with tamper tests in temporary copies. |
| `tools/build-app.sh`, `tools/run-tests.sh` | Build/test recipes; outputs stay under ignored `.build/`. |
| `FINDINGS.md` | Evidence template and manual matrix, all runtime rows `NOT RUN`. |
| `review/implementation-report.md` | Exact commands/results and limitations. |

## Build, test and validate (headless only)

From this directory:

```bash
xcrun swift build --scratch-path .build -c debug
xcrun swift test --scratch-path .build
node --test web/tests/*.test.mjs tools/tests/*.test.mjs
node tools/validate.mjs
bash tools/build-app.sh
```

`bash tools/run-tests.sh` runs the Swift tests, both Node suites and the static
audits in sequence. `bash tools/build-app.sh` produces an **ad-hoc signed,
strict-verified, unlaunched** bundle at `.build/EscalierCaptureFixture.app`.
Signing is local only: `codesign --force --sign - --timestamp=none` followed by
`codesign --verify --strict --verbose=2`. No certificate/Keychain/trust/Gatekeeper/
TCC/quarantine changes are made. Ad-hoc is not Developer ID, notarization,
Gatekeeper approval or a stable TCC identity across rebuilds. No app, browser,
server or capture is started by these commands.

Manual server start (only when you are ready to test interactively):

```bash
node tools/serve-local.mjs --port 8642
```

The server binds exactly `127.0.0.1`, serves `web/` with GET/HEAD only, rejects
path traversal/dotfiles/unknown extensions and does not open a browser. Stop it
with Ctrl-C.

## Native fixture controls

- **Create/show/hide/reshow marker pair.** Two otherwise identical borderless
  nonactivating panels. Only role, sharing type and frame origin differ.
  - `marker-sharing-none` → `NSWindow.SharingType.none` (treatment label
    `sharing-none`). This is a legacy flag, **not** a modern capture guarantee.
  - `marker-sharing-read-only` → `NSWindow.SharingType.readOnly` (control label
    `sharing-read-only`/`sharing-readOnly`). Use this as the per-cell positive
    control.
  - The panels render the same synthetic content on purpose. Identify them from
    the readback frame origins, not from their visual appearance.
- **Lazy auxiliary panel.** A separate `NSPanel` with its own marker, sharing
  `none`, level/style/size/readback. The nonactivating style flag can be toggled
  for a normal-versus-nonactivating comparison. This is a separate row, not
  all-surface validation.
- **Click-through panel.** An inert panel containing one inert button. Toggling
  `ignoresMouseEvents` changes between intercept and pass-through. Place it over
  the browser fixture's inert underlay button; record both counters manually.
  No real action occurs.
- **Focus/lifecycle controls.** Activate/deactivate the fixture, switch
  `.regular`/`.accessory` activation policy, cycle between two clearly owned
  neutral titles, and take a policy/readback snapshot after every action.
- **Readback JSON** is displayed and printed to stdout. It records requested and
  observed sharing type, style mask, level, alpha, shadow, opacity, click-through,
  visibility, key/main status, can-become-key/main, floating/becoming-key flags,
  occlusion visibility, frame, collection behaviour, application activation
  policy, key/main window references, frontmost application when available,
  screens/scale, counters, event journal, lifecycle journal/gaps and policy
  mismatches. Missing roles and mismatches are explicit; they are never silently
  treated as success.

The bundle identity is deliberately `test.escalier.spike004.fixture` with the name
`Escalier Synthetic Capture Fixture`. The title experiment changes only a window
title. Dock, process-name, executable, signature-identity, Cmd-Tab and identity
surfaces are **NOT TESTED**; no impersonation is implemented. The bundle is ad-hoc
signed for local launch tests and strict-verified, but it is not Developer
ID/notarized and ad-hoc identity is not stable across rebuilds.

## Browser fixture

Open `sender.html` and `receiver.html` in separate tabs on the local origin.

- `sender.html` requests a user-chosen display source only inside the click
  handler, with `video: true, audio: false`, after a secure-context and transient
  user-activation preflight. It checks exactly one video track and zero audio
  tracks, shows a **sender preview that is explicitly not receiver evidence**, and
  offers over a same-origin `BroadcastChannel` using SDP/local ICE only.
- `receiver.html` never starts a capture. It creates its receiver stream only from
  `pc.ontrack`, displays that received track, requires inbound `framesDecoded > 0`
  plus frame/video dimensions before showing “receiver transport observed”, and
  samples only an explicitly cropped marker ROI. Missing transport stats → **NO
  RECEIVER EVIDENCE**. Connection state alone is not evidence.
- `index.html` has the inert underlay counter and a focus/visibility log. Sender
  and receiver pages also expose focus/visibility logs and manual snapshots.
- The marker ROI color is `#FF00AA` (RGB 255/0/170). Sampling uses a per-channel
  tolerance (default 28), records only `nearMarkerFraction` metadata plus crop
  dimensions/time, and never exports or retains a full frame. The visible canvas
  is the cropped ROI, not the receiver frame.
- CSP is shared with the server header: `default-src 'none'; script-src 'self';
  style-src 'self'; ... connect-src 'none'; form-action 'none'; base-uri 'none'`.
  The static audit rejects external URLs, STUN/TURN, audio requests, `getUserMedia`,
  inline script/style, timers, network APIs, persistence/export APIs, autoplay
  attributes and any `getDisplayMedia` outside the click-triggered sender function.

## Manual runtime matrix

**All rows are NOT RUN until a human performs them with explicit permissions.**
Follow the clean-display and permission protocol in `FINDINGS.md`. Use one row per
cell and never fill a missing value with an inferred pass.

| # | Cell | Source | What must be recorded |
| --- | --- | --- | --- |
| 1 | Entire display, browser frontmost, both markers visible, overlap and non-overlap | Entire display | Sharing-none presence/absence with the sharing-readOnly control positively visible; receiver `getStats` (`framesDecoded`, `bytesReceived`, dimensions, timestamps); ROI sample for each marker; focus log |
| 2 | Selected browser window, both markers outside source | Selected external window | N/A / control absent. Never record “sharing-none excluded” from this cell |
| 3 | Selected fixture window with a marker inside the source | Selected fixture window | Positive marker observation; same-window treatment/control may be impossible; say so explicitly |
| 4 | Occluded/behind control | Any | Both markers absent because occluded; occlusion is the reason, not exclusion evidence |
| 5 | Focus: browser active, normal panel vs nonactivating panel, app active/inactive | Entire display or selected source | Pre/post app/key/main window state, panel `isKeyWindow`/config, page `focus`/`blur`/`visibilitychange`/`hasFocus` |
| 6 | Click-through: inert browser button under the native panel, `ignoresMouseEvents` true vs false | Entire display | Inert panel hit count vs browser underlay count; no real actions |
| 7 | Lifecycle: show/hide/activate/deactivate/accessory switch | Entire display | Readback after each stage: requested vs observed sharing/style/level/activation and missing roles/mismatches |
| 8 | Auxiliary surface and title experiment | Entire display or selected source | Separate auxiliary row: marker visibility, style/level/size; window-title visibility only; Dock/process/identity NOT TESTED |
| 9 | Audio/privacy | Entire display | Zero audio tracks, no `getUserMedia`, no external requests, secure context, no full-frame retention |

## How to read the oracles

- **Receiver transport oracle:** inbound RTP video stats from `pc.getStats()`:
  `framesDecoded`, `framesReceived`, `bytesReceived`, `packet` counts, `jitter`,
  `frameWidth`/`frameHeight`, `framesPerSecond`, `timestamp`, plus receiver-video
  `videoWidth`/`videoHeight`. `framesDecoded > 0`, positive `bytesReceived`, a
  positive finite `timestamp`, frame dimensions and video dimensions are all
  required for “receiver transport observed”. A connected peer, partial stats or
  sender preview is not evidence.
- **Marker/control oracle:** marker presence is determined from the cropped
  receiver-video ROI, not from a native flag. The sharing-readOnly control must be
  positively visible in the same cell before interpreting a sharing-none absence.
  Both visuals are identical; frames identify which panel was sampled.
- **Focus oracle:** page-observable `focus`, `blur`, `visibilitychange`,
  `document.hasFocus()` plus native key/main/app-active/frontmost readback. These
  are recorded observations, not a claim of undisclosed HackerRank signals.
- **Click-through oracle:** inert panel hits and browser underlay hits. No real
  action is triggered.
- **Native flag oracle:** readback of requested vs observed values, not inference
  from the setter. A native flag alone is not remote receiver-pixel evidence.

## Browser/platform notes

- Chrome/Edge are the reference browser candidates; Firefox remains conditional.
  HackerRank’s public matrix lists Firefox as not supported for the New Interview
  Experience, so a synthetic Firefox capture result would not establish HackerRank
  compatibility. See the public matrix and Mozilla release notes in the repository
  research report; no HackerRank page is used here.
- A single selected external window and an entire display are different capture
  surfaces. Modern screen capture may ignore legacy exclusion flags. Do not assume
  an overlapping auxiliary panel is included or omitted in a single-window stream.
- `NSWindow.SharingType.none` is documented as legacy and is not a guarantee.
  `ScreenCaptureKit`/browser pickers may use different composition rules. Runtime
  cells must record the actual source, overlap, browser build and macOS build.
- Screen-recording permission is persistent macOS TCC state. Grant it yourself,
  verify under System Settings → Privacy & Security → Screen Recording, and revoke
  it when finished. The fixture never requests TCC or displays permission UI on
  your behalf.
- The capture guard fails closed if `navigator.userActivation` is unavailable or
  inactive; record that as a browser limitation rather than bypassing the check.
  On browsers without `requestVideoFrameCallback`, use the manual stats refresh
  button; a missing stats field remains **NO RECEIVER EVIDENCE**.
- No microphone or audio path exists. No real interview page, private files,
  LLM/OMP call, upload or external signaling server is used.

## Limitations

- Runtime matrix, receiver pixels, focus behaviour, click-through behaviour,
  accessory/Dock identity, title visibility and browser compatibility are
  **NOT RUN**.
- Native readback proves only requested/observed AppKit state, not remote capture
  composition.
- A synthetic local fixture cannot prove absence of undisclosed third-party
  server-side signals or establish universal invisibility.
- This spike does not test tab sharing, the full NFR-06 matrix, Natively parity or
  Spike 003.
- The built `.app` is ad-hoc signed and strict-verified locally; launch, Gatekeeper,
  TCC attribution and stable identity attribution remain untested. Ad-hoc is not
  Developer ID/notarization or a stable TCC identity across rebuilds.

## References

- Apple: [`NSWindow.SharingType.none`](https://developer.apple.com/documentation/appkit/nswindow/sharingtype-swift.enum/none),
  [`NSPanel`](https://developer.apple.com/documentation/appkit/nspanel),
  [`NSApplication.ActivationPolicy.accessory`](https://developer.apple.com/documentation/appkit/nsapplication/activationpolicy-swift.enum/accessory),
  [`SCContentFilter`](https://developer.apple.com/documentation/screencapturekit/sccontentfilter).
- HackerRank: [browser recommendations](https://candidatesupport.hackerrank.com/articles/8455316478-browser-recommendations-for-hackerrank-interviews),
  [observation mode](https://support.hackerrank.com/articles/1263202297-observation-mode-in-interviews),
  [integrity signals](https://support.hackerrank.com/articles/5161582600-interview-integrity-signals).
- Mozilla: [Firefox 132 release notes](https://www.firefox.com/en-US/firefox/132.0/releasenotes/),
  [ScreenCaptureKit rollout](https://bugzilla.mozilla.org/show_bug.cgi?id=1915562),
  [picker rollout](https://bugzilla.mozilla.org/show_bug.cgi?id=1918648).

A build or test pass in this directory is not a UI, capture, focus or stealth
result.
