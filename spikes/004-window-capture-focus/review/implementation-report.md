# Spike 004 — implementation report

Date: 2026-10-26. Worker: delegated implementation (self-report, not an
independent review). Scope: synthetic window/focus/capture harness, headless and
static only. **Runtime matrix NOT RUN.**

## Verdict

The harness builds, its pure policy/browser/evidence logic is unit-tested, its
static no-external/no-audio/no-autostart/public-API guards pass, and the audit
rules were tamper-tested against deliberately broken temporary copies. This is
**not** receiver-pixel, focus, click-through, Dock-identity or stealth evidence.
No app, browser, capture, server listen, permission prompt or GUI automation was
started.

## Environment and fixture identity

| Item | Value |
| --- | --- |
| Host OS | macOS 27.0.1, build 26A434, arm64 |
| Swift | Apple Swift 6.4 (swiftlang-6.4.0.34.1, clang-2100.3.34.1) |
| Swift target | `arm64-apple-macosx27.0.0` host; package deployment target macOS 14 |
| Test target | `arm64e-apple-macos14.0` (from XCTest output) |
| Node | v20.20.2 |
| Repository HEAD at report time | `e50b023b7e5118c0800d3b45e883d62cc7cc7d4e` (not created by this worker) |
| 004 working tree | untracked; no staging or commit performed |
| Source-tree SHA-256 | `f7a974ceaf9e41db49b32991f64206fd18c23d136907252bf2accf41bd08635f` |
| Source hash scope | 47 files under `Sources/`, `Tests/`, `web/`, `tools/`, `Resources/`, plus `Package.swift`; excludes docs and build outputs. The exact reproducible recipe and current 48-file value are in the fix-round section below. |
| Built bundle | `.build/EscalierCaptureFixture.app` |
| Bundle ID / name | `test.escalier.spike004.fixture` / `Escalier Synthetic Capture Fixture` |
| Bundle binary | Mach-O 64-bit executable arm64, 1,038,448 bytes, SHA-256 `3775c55c00e1ef27788ea85b5e989c5a1ba76c8004082e1e19a53d56be3e2d57` |
| Info.plist | `plutil -lint` OK for source and bundled copies |
| Signing (pre-explicit-signing, historical) | No explicit bundle `codesign` was applied in that pass; the Swift-built executable may have carried a linker ad-hoc signature. Not Developer ID/notarized; not launched. |

Historical note: the table above and the pre-signing results below preserve the
original pre-explicit-signing implementation pass (47-file source hash,
1,038,448-byte binary, 75 Node tests), which was reported as unsigned at the time.
The current tree is explicitly ad-hoc signed; the signing addendum records the
signing-pass 48-file source hash, signed binary and 78 Node tests, and the
fix-round section records the current 48-file source hash, rebuilt signed binary
and 80 Node tests. The prior pre-explicit-signing evidence is intentionally
retained, not overwritten.

## Commands and exact results

### RED phase (before implementation)

- `xcrun swift test --scratch-path .build` first failed before test compilation:
  `error: '004-window-capture-focus': Source files for target
  EscalierCaptureFixture should be located under
  'Sources/EscalierCaptureFixture'...` (exit 1). After adding only a placeholder
  target, it failed on undefined policy types, e.g. `cannot find
  'MarkerVisualFingerprint' in scope`, `cannot find type 'WindowReadback' in
  scope` (exit 1). Implementation followed.
- `node --test web/tests/*.test.mjs` failed 4/4 with
  `ERR_MODULE_NOT_FOUND ... web/transport-core.mjs` (and the other not-yet-written
  pure modules): `# pass 0`, `# fail 4`.
- `node --test tools/tests/*.test.mjs` failed 3/3 with
  `ERR_MODULE_NOT_FOUND ... tools/web-audit.mjs` (and the other audit/server
  modules): `# pass 0`, `# fail 3`.
- A later lifecycle-journal coverage test was RED before that field existed:
  `extra argument 'lifecycleJournal' in call` (exit 1). The serialized journal and
  public entry initializer were then implemented; the final suite is 51 tests.
- The web/native audit tests were written before their implementations. After
  implementation, all tamper cases below pass; the tests create temporary copies
  under the OS temp directory and remove them in `finally`.

### GREEN phase (final)

```bash
bash tools/run-tests.sh
# exit 0
```

Observed results:

- Swift/XCTest: `Executed 51 tests, with 0 failures (0 unexpected)`.
  - Policy/AppKit raw-value and label tests, marker-pair identity/separation,
    readback schema/round-trip/mismatch, lifecycle ordering/readback gaps and the
    serialized lifecycle journal, click-through counters/modes, evidence-cell
    invalid/occluded/N/A/no-receiver rules, and identity/title-policy tests.
- Node: `# tests 75`, `# pass 75`, `# fail 0`.
  - 41 browser pure-logic tests (`web/tests/`): capture guard, video-only track
    check, signal validation/candidate ordering/cleanup/event log, focus log,
    inbound video stats, ROI stats, receiver evidence, sender-preview rejection.
  - 34 tool tests (`tools/tests/`): 19 browser static-audit/tamper cases, 8 native
    audit/tamper cases, 7 loopback-server/path/MIME/argument cases.
- `node tools/validate.mjs`: `WEB AUDIT: PASS (12 files scanned)`;
  `NATIVE AUDIT: PASS (14 files scanned)`;
  `STATIC VALIDATION PASS — no app/browser/server was launched and no capture was
  started.`
- `node --check` on all 11 `web/*.mjs` + `tools/*.mjs` files: pass (syntax only).

### Build / bundle

```bash
bash tools/build-app.sh
# Building for debugging...
# Build complete!
# Built .build/EscalierCaptureFixture.app
# Bundle is NOT signed and was NOT launched.
# exit 0
```

That last message is a historical quote from the pre-explicit-signing script; the
current script performs and verifies ad-hoc signing (see addendum).

- `file` on the bundled executable: `Mach-O 64-bit executable arm64`.
- The package declares no dependencies, so no package resolution/download was
  required; build/test artifacts stay under ignored `.build/`.
- The bundle contains `Contents/Info.plist`, `Contents/MacOS/EscalierCaptureFixture`
  and `Contents/PkgInfo`. In that historical pass no explicit bundle `codesign` was
  applied; `codesign -dv` may already have shown a linker ad-hoc executable
  signature. See the signing addendum for the current explicit signing.
- All outputs are under ignored `.build/`; no host install was performed.

## What the implementation covers

### Native (AppKit, public APIs only)

- A plainly labelled control window with a synthetic banner, marker legend,
  lifecycle/readback controls, inert click counter and scrollable JSON readback.
- Two otherwise identical marker panels; only role, sharing type and frame origin
  differ:
  - `marker-sharing-none` requests `NSWindow.SharingType.none`;
  - `marker-sharing-read-only` requests `NSWindow.SharingType.readOnly`.
  - Both use the same visual fingerprint, level, style, alpha, shadow, opacity and
    collection behaviour. The readback/builder records requested and observed
    values and reports mismatches.
- Lazy auxiliary `NSPanel` (own marker/policy/readback, `sharing-none`, separate
  surface row; nonactivating style can be toggled).
- Inert click-through `NSPanel` with a local button/counter and
  `ignoresMouseEvents` intercept/pass-through modes; browser underlay count is
  entered manually.
- Lifecycle controls: create/show/hide/reshow markers, activate/deactivate app,
  switch regular/accessory activation policy, cycle two clearly owned neutral
  titles, readback after every action.
- Readback JSON covers the native policy/readback fields: requested vs observed
  sharing, style/level/collection names, occlusion, key/main window references,
  activation policy, frontmost application when available, screens/scale, counters,
  event/lifecycle journals, missing roles and policy mismatches. OS/browser/build,
  permission state, audio-track count, receiver transport, ROI/focus logs and the
  clean-display protocol belong to the manual `FINDINGS.md` template /
  `EvidenceSchema.requiredManualFields`, not to native readback. The JSON prints to
  stdout and displays in the control window; no file is written.
- No private APIs, global event taps/monitors, accessibility automation,
  screen-capture APIs, `NSTask`/process launch, network APIs or TCC request APIs.
  Static native audit enforces these and the required readback markers; tamper
  tests confirm rejection of a global event tap, `NSTask`, missing
  `sharingType` readback, microphone usage key, changed bundle identity, protection
  wording and an external URL.

### Browser fixture (same-origin, local only)

- `sender.html`/`sender.mjs`: click-only `getDisplayMedia({ video: true,
  audio: false })` after secure-context/transient-activation guard; exact one-video /
  zero-audio stream inspection; sender preview in a separate element explicitly
  labelled not receiver evidence; `RTCPeerConnection({ iceServers: [] })`;
  `addTrack`; track-ended cleanup; BroadcastChannel SDP/local-ICE signaling.
- `receiver.html`/`receiver.mjs`: no capture call; receiver video `srcObject` only
  from `pc.ontrack`; inbound RTP stats via `getStats()` with
  `framesDecoded`/`bytesReceived`/timestamp/dimensions; no receiver evidence
  without positive decoded frames, bytes, timestamp and frame/video dimensions;
  manual ROI sampling only (cropped canvas `drawImage`/`getImageData`, never
  full-frame export); positive-control label for the sharing-readOnly marker.
- `index.html`/`app.mjs`: focus/visibility log and inert underlay counter; no
  capture code.
- Local loopback server: explicit `node tools/serve-local.mjs --port 8642`, binds
  `127.0.0.1`, GET/HEAD only, path traversal/dotfile/extension guards, no directory
  listing, security/CSP/Permissions-Policy headers, no browser launch, direct-run
  guard only.
- Static audit rejects external URLs, STUN/TURN/non-empty ICE servers, audio
  requests, `getUserMedia`, inline script/style, timers, network APIs,
  persistence/export APIs, autoplay attributes, sender/receiver preview confusion
  and any `getDisplayMedia` outside the click-triggered sender function. CSP is
  compared between HTML meta and the server header to catch drift.

## Limitations, concerns and untested surfaces

1. **Runtime matrix is NOT RUN.** No receiver pixels, focus/blur/visibility
   behaviour, click-through behaviour, occlusion, activation policy, title
   visibility or browser compatibility was observed. Build/unit/static success is
   not a stealth result.
2. **`NSWindow.SharingType.none` is legacy.** It is requested and read back, but a
   modern ScreenCaptureKit/browser capture backend may ignore it. Do not read the
   flag as a guarantee.
3. **Panel activation/lifecycle semantics are not runtime-verified.** Toggling
   `.nonactivatingPanel` on an existing lazy auxiliary panel may not behave like a
   fresh panel; `becomesKeyOnlyIfNeeded`, floating level, accessory activation and
   Space/full-screen behavior all need the manual rows. No private activation
   workaround was implemented.
4. **Marker identity is positional by design.** The two marker panels are
   intentionally visually identical; identify them from readback frame origins, not
   appearance. A receiver ROI label is manual and could be mislabelled; the evidence
   records the label and magenta fraction but cannot prove operator intent.
5. **Native readback is requested/observed AppKit state only.** It does not prove
   what another process captured. Missing roles and mismatches are explicit, but a
   matching readback is still not receiver evidence.
6. **Receiver transport may be absent on some browser builds.** The receiver
   requires inbound RTP `framesDecoded > 0`, positive `bytesReceived`, a positive
   finite `timestamp`, frame dimensions and video dimensions. If a browser omits any
   required field or fails to connect with empty ICE servers/host candidates, the
   UI must stay at **NO RECEIVER EVIDENCE** rather than infer success. Same-origin
   two-tab WebRTC with no STUN/TURN was not run.
7. **Browser behavior is not validated.** `getDisplayMedia`, BroadcastChannel
   signaling, mDNS/host ICE, screen/window picker composition, CSP
   `media-src`/`display-capture` interactions and stats field names must be tested
   in the exact Chrome/Firefox/macOS builds. Firefox remains conditional and is not
   supported for HackerRank's New Interview Experience per its public matrix.
8. **Positive control is manual.** The receiver's evidence says “transport
   observed” once inbound frames exist; it does not turn that into a stealth pass.
   The sharing-readOnly control must be positively sampled in the same cell before
   interpreting sharing-none absence. Occlusion/invisibility recorded for either
   marker invalidates the cell until both markers are positively visible. Without
   that, the interpretation explicitly says no positive control.
9. **Sender/receiver separation is static/DOM-level evidence.** The receiver page
   has no sender-preview element and uses only `pc.ontrack`; the audit enforces this,
   but runtime DOM tampering is outside the static claim.
10. **Title/identity scope is narrow.** The title experiment changes only a window
    title. Bundle/executable name, signature, process name, Dock, Cmd-Tab,
    accessibility/process inventory and TCC attribution are **NOT TESTED**. The
    pre-signing bundle was unsigned; the current bundle is ad-hoc signed and
    strict-verified locally (see the signing addendum), but it is not Developer
    ID/notarized, was not launched and does not provide a stable TCC identity.
11. **No raw frames / no privacy claim.** Only a small ROI crop is processed in
    memory and shown as a crop preview; no full frame is stored/exported. The
    fixture does not prove absence of undisclosed third-party server-side signals.
12. **Independent review still required.** Preflight N-16 requires an independent
    spec/quality review before accepting findings. This report is the worker's
    self-report, not that review.
13. **No ASR/OMP/interview/network involvement.** No microphone, audio path,
    private files, real interview page, LLM/OMP call, upload or external signaling
    server was used.

## Bookkeeping

- Owned/created: `README.md`, `FINDINGS.md`, `Package.swift`, `Sources/**`,
  `Tests/**`, `Resources/**`, `web/**`, `tools/**` and this report. `PLAN.md` and
  coordinator review records were not edited. No other spike/root files were
  edited; no subagents, staging or commits.
- The `.build/` bundle and test artifacts are ignored outputs. No `.tools/` output
  was needed. Node tamper tests used short-lived OS-temp copies and removed them.
- An earlier local compile probe under the repository's ignored `.build/probe` was
  removed after use.
- Runtime evidence template and all `NOT RUN` rows are in `FINDINGS.md`.

## Signing addendum (2026-10-26, post-freeze owner direction)

Scope: bounded **local ad-hoc signing** for later launch tests only. This addendum
supersedes the signing status/current artifact, while preserving the prior
pre-explicit-signing implementation evidence above.

### Changes

- `tools/build-app.sh` now runs, after bundle assembly:
  `codesign --force --sign - --timestamp=none "$APP"` then
  `codesign --verify --strict --verbose=2 "$APP"`. `set -e` propagates either
  failure. No certificate, Keychain, trust, Gatekeeper, TCC or quarantine changes;
  no `--deep` workaround and no nested custom code.
- New focused test `tools/tests/build-app-signing.test.mjs` static-pins both
  commands and exercises signing-failure and verification-failure propagation with
  fake `codesign` stubs in OS-temp directories.
- `README.md` and `FINDINGS.md` now describe the bundle as ad-hoc signed/verified,
  not Developer ID/notarized, not launch/TCC-tested and not a stable identity.

### RED/GREEN evidence

Before editing `tools/build-app.sh`, `node --test
tools/tests/build-app-signing.test.mjs` was RED: `# tests 3`, `# pass 0`, `# fail 3`.
The static test could not find the signing commands, and both propagation tests saw
the build script exit 0 because no `codesign` call occurred.

After editing, the same command was GREEN: `# tests 3`, `# pass 3`, `# fail 0`.
Full `bash tools/run-tests.sh` then passed: Swift 51 tests, Node 78 tests
(41 browser logic + 34 audit/server/tamper + 3 signing), web audit 12 files, native
audit 14 files, all exit 0. No app/browser/server/capture was launched.

### Real packaging and signature inspection

`bash tools/build-app.sh` exited 0. Build log highlights:

```text
.build/EscalierCaptureFixture.app: replacing existing signature
.build/EscalierCaptureFixture.app: valid on disk
.build/EscalierCaptureFixture.app: satisfies its Designated Requirement
Built .build/EscalierCaptureFixture.app
Bundle is ad-hoc signed and verified; NOT Developer ID/notarized and NOT launched.
```

`codesign --verify --strict --verbose=2 .build/EscalierCaptureFixture.app` exited 0
with the same `valid on disk` / `satisfies its Designated Requirement` lines.
`codesign -dv --verbose=4` reported (sanitized; no local path):

```text
Identifier=test.escalier.spike004.fixture
Format=app bundle with Mach-O thin (arm64)
CodeDirectory v=20400 size=2263 flags=0x2(adhoc) hashes=64+3 location=embedded
CDHash=a483f1dc91c269bc5dc6d600e097c4dade0625f8
Signature=adhoc
Info.plist entries=13
TeamIdentifier=not set
Sealed Resources version=2 rules=13 files=0
Total signatures=1
```

`Contents/_CodeSignature/CodeResources` exists (2,200 bytes). The build log's
`replacing existing signature` line indicates a prior signature (linker ad-hoc on
the executable and/or an earlier bundle signature); the explicit `codesign` step
seals the current bundle. The code-signing identifier
`test.escalier.spike004.fixture` is recorded as an identity surface;
`TeamIdentifier=not set` confirms this is ad-hoc, not a team/Developer ID identity,
and not a stable TCC identity across rebuilds. The signing-pass signed executable
was Mach-O arm64, 1,037,968 bytes, SHA-256
`e5a043c6426610fc283e9d2174017a5828da96b5b0b8ce7221af9fc759971dcb`.
The signing-pass source-tree hash (48 files, including the signing test) was
`27e54adb17cec69948d6129f87f821d49c5cd6e8f94d2d9567076346001af3b1`. The
fix-round section below records the rebuilt current artifact after P1/P2.

### Signing limitations

- Ad-hoc is **not** Developer ID, notarization, Gatekeeper approval or a guarantee
  that macOS will launch the bundle on another machine.
- Ad-hoc identity is not stable across rebuilds; TCC attribution and permission
  persistence for this bundle are **NOT RUN** and must not be inferred.
- No app launch, Gatekeeper assessment, Keychain/trust change, TCC prompt,
  quarantine change, `--deep`, network call, server listen or capture occurred.
- This signing delta does not change any runtime/stealth finding. Independent
  implementation review remains required.

## Fix round 1 (independent review P1–P5)

Date: 2026-10-26, after `review/implementation-review.md`. Scope: only Important
P1/P2 and the cheap documentation/identity clarifications P3/P4/P5. P6–P11 remain
deferred to the final review; no expansion into those code fixes. The signing
method and tests above are retained. No app/browser/server/capture launch and no
policy/TCC/Keychain/trust/quarantine change.

### P1 — receiver-evidence gate

Fixed in both evaluators:

- Swift `ReceiverTransportReadback` now carries `timestamp: Double?`; the gate
  requires positive `bytesReceived` and a finite positive `timestamp` in addition
  to `framesDecoded > 0`, frame dimensions and video dimensions.
- JavaScript `buildReceiverEvidence` now requires positive, finite
  `bytesReceived` and `timestamp` in addition to decoded frames and dimensions.
- `receiver.mjs` displays the timestamp and the static web audit requires
  `framesDecoded`/`bytesReceived`/`timestamp` in the receiver source.

Regression coverage:

- Swift: `testMissingZeroOrNegativeBytesReceivedMeansNoReceiverEvidence`,
  `testMissingZeroNegativeOrNonFiniteTimestampMeansNoReceiverEvidence`.
- JavaScript: `missing, zero or negative bytesReceived means no receiver evidence`
  and `missing, zero, negative or non-finite timestamp means no receiver evidence`.

RED/GREEN evidence:

- Before the Swift model change, adding the timestamp test produced
  `extra argument 'timestamp' in call` (build failed). After implementation, the
  first run exposed 2 occlusion-reason assertion failures; the reason text was
  corrected and the suite reached 54/0. The P1 status gate itself now returns
  `NO RECEIVER EVIDENCE` for nil/0/negative bytes or nil/0/negative/NaN/infinite
  timestamp.
- Before the JS gate change, the receiver-core suite was `16 tests, 14 pass, 2 fail`;
  both new missing/zero-field tests failed. After the change: `16 tests, 16 pass,
  0 fail`.

### P2 — partial occlusion

Swift evaluation now treats an occlusion/invisibility record as `.occluded`
whenever either marker is not positively visible. It cannot fall through to
`.transportObserved` and interpret treatment absence when only the treatment is
occluded. New test:
`testTreatmentOccludedButControlVisibleRemainsOccluded` (treatment false, control
true, occlusion reason recorded) expects `.occluded` and no “absence is one local
observation” reason. The existing both-occluded test remains green.

### P3 — signing/identity wording

Corrected earlier wording as recorded above: no explicit packaging signing before
the addendum is not proof that no linker ad-hoc signature existed; historical
commands are annotated. The code-signing identifier
`test.escalier.spike004.fixture` is recorded as an identity surface;
`Signature=adhoc`, `TeamIdentifier=not set`, not Developer ID/notarized. README/
FINDINGS/build-script messages now describe the current ad-hoc signed state.

### P4 — native vs manual schema

The report now says native readback covers native policy/readback fields only.
OS/browser/build, permission state, audio-track count, receiver transport, ROI/
focus logs and clean-display protocol are explicitly assigned to the manual
`FINDINGS.md` template / `EvidenceSchema.requiredManualFields`.

### P5 — reproducible source hash

Exact recipe used for the current 48-file value (relative paths from this spike
directory; sorted by path; path UTF-8 + NUL + file bytes + NUL for each; SHA-256):

```python
import hashlib, os
paths = []
for base in ["Sources", "Tests", "web", "tools", "Resources"]:
    for directory, subdirectories, filenames in os.walk(base):
        subdirectories[:] = [
            name for name in subdirectories if name not in (".build", "__pycache__")
        ]
        for name in filenames:
            paths.append(os.path.join(directory, name))
paths.append("Package.swift")

digest = hashlib.sha256()
for path in sorted(paths):
    digest.update(path.encode("utf-8"))
    digest.update(b"\0")
    digest.update(open(path, "rb").read())
    digest.update(b"\0")
print(digest.hexdigest())
```

Current result: `2508c55909280e82f4ae22220745593adc9e4f57a161d50194a868a2acbc2e00`
over 48 files. The historical `f7a974…` 47-file value above refers to an earlier
tree; the same recipe applied to that tree would reproduce it, but the current
tree cannot by construction.

### Covering commands and current fingerprints

```text
xcrun swift test --scratch-path .build
# Executed 54 tests, with 0 failures

node --test web/tests/*.test.mjs tools/tests/*.test.mjs
# # tests 80, # pass 80, # fail 0
# 43 browser logic + 34 audit/server/tamper + 3 signing

node tools/validate.mjs
# WEB AUDIT: PASS (12 files scanned)
# NATIVE AUDIT: PASS (14 files scanned)
# STATIC VALIDATION PASS

bash tools/build-app.sh
# Build complete!
# valid on disk
# satisfies its Designated Requirement
# Bundle is ad-hoc signed and verified; NOT Developer ID/notarized and NOT launched.
```

Current signed artifact (supersedes the earlier signing-addendum hash/CDHash; the
signing method/tests are unchanged):

- Signed executable: Mach-O arm64, 1,055,648 bytes, SHA-256
  `e84ee23e1713754fb8db71bd963313f1a9939654deee24c67f5ddcf3c8f27246`.
- `codesign --verify --strict --verbose=2 .build/EscalierCaptureFixture.app`:
  exit 0, `valid on disk`, `satisfies its Designated Requirement`.
- `codesign -dv --verbose=4`: `Identifier=test.escalier.spike004.fixture`,
  `CodeDirectory v=20400 size=2295 flags=0x2(adhoc) hashes=65+3`,
  `CDHash=e00cf564c5989c07e85125537d82c4ed454181b3`, `Signature=adhoc`,
  `TeamIdentifier=not set`, `Sealed Resources version=2 rules=13 files=0`,
  `Total signatures=1`.
- Current source hash: `2508c55909280e82f4ae22220745593adc9e4f57a161d50194a868a2acbc2e00`
  over 48 files.
- `plutil -lint` source and bundled Info.plist: OK.

No runtime matrix cell was run; runtime remains **NOT RUN**. P6–P11 from the
independent review remain deferred to final review.
