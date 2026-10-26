# Spike 003 implementation report

Date: 2026-10-26. Worker: `native-shell-ui`. Scope: bounded synthetic native shell/UI prototype
per [PLAN.md](../PLAN.md), [binding preflight resolutions](preflight-resolutions.md),
[requirements](../../../docs/requirements.md) and
[ADR-0001](../../../docs/decisions/0001-native-macos-and-omp-rpc.md).

## Result

Implemented a dependency-free Swift package with:

- pure `EscalierCore` model and 35 headless XCTest cases;
- SwiftUI content in an AppKit-coordinated one-window shell;
- in-app AppKit menus with provisional `⌘1`–`⌘5` assistance routes and reference navigation;
- 35/35 tests passing, `swift build` passing with no captured warnings, and a local
  `.build/EscalierShell.app` package;
- **no GUI launch, screenshot, app drive, permission request, global hook or runtime capture** by
  this worker.

Interactive visuals/keyboard/focus/scroll/accessibility remain **NOT TESTED**.

## Environment

| Item | Observed |
| --- | --- |
| OS | macOS 27.0.1 (build 26A434), arm64 |
| Xcode | 27.1 (27A9275) |
| Swift | Apple Swift 6.4 (swiftlang-6.4.0.34.1, swift-driver 1.168.6); package tools version 5.9 |
| SDK target | macOS 14.0 deployment; host macOS SDK 27.0 |
| SwiftPM | Swift Package Manager 6.4.0-dev |
| Host installs | None |

## TDD and verification sequence

All commands were run from `spikes/003-native-shell-ui` or with `--package-path`.

### 1. RED

Tests and an API-only skeleton (types present, behavior absent) were written before the real model.
Command:

```sh
swift test --package-path spikes/003-native-shell-ui 2>&1 | tee .build/logs/red-test.log
```

Observed result (exit 1):

```text
Test Suite 'All tests' failed
Executed 33 tests, with 143 failures (0 unexpected) in 0.083 (0.088) seconds
```

The three static source/Info.plist/package assertions already passed against the skeleton; all
behavioral assertions failed. This was a genuine behavioral RED, not only a compile failure. The
skeleton (`ModelSkeleton.swift`) was deleted when implementation began.

### 2. GREEN

Final command:

```sh
swift test --package-path spikes/003-native-shell-ui 2>&1 | tee .build/logs/green-test-final.log
```

Observed result (exit 0):

```text
Executed 6 tests, with 0 failures (0 unexpected)   AssistanceAndStreamingTests
Executed 4 tests, with 0 failures (0 unexpected)   ConversationConfigurationTests
Executed 6 tests, with 0 failures (0 unexpected)   PhaseAndRoutingTests
Executed 10 tests, with 0 failures (0 unexpected)  ReferenceStabilityTests
Executed 5 tests, with 0 failures (0 unexpected)   RetainedResultsTests
Executed 4 tests, with 0 failures (0 unexpected)   SourceAuditTests
Executed 35 tests, with 0 failures (0 unexpected) in 0.051 (0.055) seconds
```

The toolchain also prints an empty Swift Testing summary (`0 tests`); all 35 cases are XCTest in
`EscalierCoreTests`.

### 3. Native build

```sh
swift build --package-path spikes/003-native-shell-ui 2>&1 | tee .build/logs/build-final.log
```

Observed (exit 0):

```text
Building for debugging...
Build complete!
```

No `warning:` lines in the captured final build log. Two compile fixes were required during
development: qualifying `EscalierCore.TextRange` to avoid the CoreServices/AE `TextRange`
collision, and using explicit `Color` values instead of a mixed `.tint`/`.secondary`
`ShapeStyle` ternary.

### 4. Local package (not launched)

```sh
tools/package-app.sh 2>&1 | tee .build/logs/package-final.log
```

Observed (exit 0):

```text
Build complete!
.build/EscalierShell.app/Contents/Info.plist: OK
Packaged .build/EscalierShell.app (not launched)
```

Artifact checks: `file` reports a Mach-O 64-bit arm64 executable; `otool -L` shows system
Foundation/AppKit/SwiftUI/Combine and Swift runtime libraries only; bundle size observed 1.8 MB.
No app process was started.

### 5. Static audit

`SourceAuditTests` recursively reads `Sources/**/*.swift` and checks this spike's sources for the
following tokens (the audit is 003-scoped, not a project-wide hook ban):

`addGlobalMonitorForEvents`, `addLocalMonitorForEvents`, `NSEvent.addGlobal`, `NSEvent.addLocal`,
`CGEvent`, `eventTap`, `AXIsProcessTrusted`,
`AXUIElement`, `CGRequestListenEventAccess`, `CGPreflightListenEventAccess`,
`CGRequestPostEventAccess`, `IOHID`, `CGWindowListCreateImage`, `SCShareableContent`, `SCStream`,
`AVCapture`, `getDisplayMedia`, `URLSession`, `NSURLConnection`, `NWConnection`, `import Network`,
`Process(`, `NSAppleScript`, `UserDefaults`, `FileManager.default.removeItem`, `.write(to:`.

It also checks `Resources/Info.plist` for absent `NSAccessibilityUsageDescription`,
`NSInputMonitoringUsageDescription`, `NSScreenCaptureUsageDescription`,
`NSMicrophoneUsageDescription` and `NSCameraUsageDescription`, and asserts `Package.swift` has no
remote `.package(` dependency or URL. All four `SourceAuditTests` pass (three audit checks plus a
positive-control test that proves planted tokens are detected). This is a heuristic source/plist
check, not an entitlement or runtime trace.

## Test inventory

| Suite | Cases | Coverage |
| --- | --- | --- |
| `ReferenceStabilityTests` | 10 | source identity/citation/range validity, initial selection, arrival stability, next/previous and indicator clearing, selected/non-selected removal, explicit re-selection, duplicate arrival, arrival after unresolved removal, ConversationState forwarding |
| `PhaseAndRoutingTests` | 6 | explicit/idempotent phase transition, five distinct routes/hints, per-route dispatch log, runtime status values, screenshot placeholder/no-capture status, store routing isolation |
| `ConversationConfigurationTests` | 4 | per-conversation model/tool/skill isolation, invalid-ID rejection, phase/reference isolation, mock/no-enforcement assertions |
| `RetainedResultsTests` | 5 | snapshot contents, immutable value snapshot, selected deletion vs siblings/sources, explicit selection requirement, cross-conversation selection bounds |
| `AssistanceAndStreamingTests` | 6 | stable streaming identity/chunk order, late-chunk rejection, complete diagram alt text/completeness, provenance labels, insertion order, manual stream demo |
| `SourceAuditTests` | 4 | 003 source/API audit + positive-control detection test, sensitive Info.plist keys absent, no remote SwiftPM dependency |
| **Total** | **35** | |

## Requirement traceability (prototype level)

| Requirement | Prototype evidence | Limit |
| --- | --- | --- |
| FR-05 actual source text/highlight/locations; stable selection; contextual nav | Synthetic source identities, excerpts, ranges, anchors, selected highlight, previous/next, explicit removal state; headless tests | No real source ingestion, search index or scroll-position test |
| FR-06 streamed text/images, continuous buffer, provenance distinction | Synthetic message chunk history, scrollable buffer, source-backed/suggested/general/image labels, complete local vector item | No generation, image stream or actual model |
| FR-07 five separate predictable actions | Five enums with unique routes, labels, hints and `⌘1`–`⌘5` menu equivalents; distinct route log per action | Actual keyboard/focus/no-bubble behavior NOT TESTED |
| FR-10 preparation → live transition | Explicit `startConversation()` + UI control; phase isolation tested | Transition does not fabricate a transcript |
| FR-14 canonical source/citation outside assistant history | Source candidates held separately from assistance messages; snapshot copies both separately | No persistence/source store |
| FR-15 retained transcript/retrieval/assistance and easy delete | In-memory retained value snapshot with all three; selected deletion only; inspection UI | No save defaults, disk deletion or post-call persistence policy |
| FR-16 per-conversation tools/skills + model | Per-conversation mock selections and UI controls, isolated by tests | Mock only; enforcement NOT IMPLEMENTED |
| NFR-03 explicit capability config / no blanket removal | Per-conversation tool/skill state exists | No OMP enforcement or approval behavior |
| NFR-04 no Dock icon | Not attempted | NOT TESTED / no claim |
| NFR-05 stealth baseline | Not attempted in 003 | NO CLAIM; separate 005 scope |
| NFR-08 SwiftUI + AppKit coordinator | AppKit `NSApplication`/`NSWindow` + `NSHostingController`; package builds | GUI launch/render NOT TESTED |
| NFR-01 locally buildable app | `tools/package-app.sh` produces a local `.app` | Unsigned; not launched; identity surfaces untested |

## What is intentionally excluded

- Real files, vault, source ingestion, search index or canonical source persistence.
- Microphone/computer-audio capture, ASR, audio device enumeration or permission requests.
- Screen capture, screenshot files, image generation, progressive image rendering or vision APIs.
- OMP RPC, model discovery, LLM calls, tool/skill enforcement, network clients or remote deps.
- Global keyboard monitors, event taps, Accessibility/Input Monitoring APIs, permission prompts.
- Persistent user-data storage/deletion, preferences, database, logs of real content.
- Product identity or code copied from Natively.
- Stealth, capture-exclusion, invisibility, focus-isolation, latency or performance claims.
- Launching/driving the GUI from this worker.

The owner separately scoped active global keyboard routing and no-bubble testing to
[`../../005-global-keyboard-routing/PLAN.md`](../../005-global-keyboard-routing/PLAN.md)
(forthcoming at implementation time). 003 includes only a `NOT CONNECTED` status note and
in-app menu key equivalents. The 003 source audit does not constrain that separately reviewed
spike.

## Self-review

### Strengths

- Pure state and UI bootstrapping are separated; all behavioral assertions run without AppKit.
- Reference identity is a value (candidate ID + range + anchor), avoiding index/scroll ambiguity.
- Selected-source removal is intentionally distinct from arrival; no automatic sibling jump.
- Retained aggregates are value snapshots, so mutation isolation and sibling safety are structural,
  not dependent on a “copy” helper.
- Deletion UI has an explicit confirmation and repeated no-disk-data labels.
- Mock/runtime boundaries are labelled in multiple surfaces and pinned by tests.
- The local diagram is complete native vector content with visible alt text and an accessibility
  label; no image pipeline is implied.
- No dependencies; build and package outputs stay under ignored `.build/`.

### Risks / open questions

1. **Rendered behavior unverified.** SwiftUI layout in a 1100×700 window, nested scroll behavior,
   menu target-action, focus traversal and VoiceOver haven't been observed. The build only proves
   API/type correctness.
2. **Menu shortcuts are not tested.** `⌘1`–`⌘5` menu equivalents are provisional and in-app only.
   They do not prove interception, no-bubble behavior or browser safety; that is 005's separate
   scope.
3. **Static audit is limited.** A substring audit can miss dynamically constructed selectors or
   linked-library capability; it also scans comments/test strings if they contain forbidden tokens.
   It currently passes. It is not a guarantee that no AppKit framework exposes global APIs; it is
   evidence that 003 does not call them.
4. **Scroll stability is not proven.** The code preserves selected ID/range/anchor, but no scroll
   anchor or visual viewport assertion exists. README/FINDINGS mark this NOT TESTED.
5. **Preparation start does not create a stream.** The live sample is a separate pre-populated
   conversation. A reviewer should not infer live capture/ASR from the transition.
6. **No source ingestion or persistence.** FR-14/FR-15 real implementations, save defaults, file
   format/deletion semantics and recovery remain open. The prototype's deletion is synthetic and
   in-memory only.
7. **Packaging is minimal.** `.app` is unsigned, not launched, and not checked for Dock/menu-bar/
   activation identity or Gatekeeper. The activation policy is `.regular` for a visible manual
   review window; NFR-04 is not demonstrated.
8. **Mock controls could be misread.** Multiple labels say MOCK/no enforcement, and tests pin the
   status enum, but a visual reviewer should confirm the labels survive layout. The code has no
   model routing or tool/skill enforcement path.
9. **Data model choices are provisional.** Source range uses UTF-16 offsets for future AppKit text
   APIs; a WebKit/textkit renderer could prefer different anchors. Stable logical anchor strings
   are included, but an offscreen anchor/scroll strategy is not designed.
10. **No real image asset.** The “image” is a SwiftUI vector diagram, not a bitmap/SVG resource.
    This satisfies the bounded “complete local image/diagram placeholder with alt text” goal, but
    it does not exercise image decoding, asset catalogs or progressive image UI.
11. **Test dates/logs are local artifacts.** `.build/logs/` is intentionally ignored; the transcript
    above is the retained evidence. No commit was made by this worker.
12. **AppKit lifecycle not runtime-verified.** `NSApplication.run`, window key/order-front,
    application menu installation and quit-after-last-window-closed are compile-checked only.

### Self-check against the review gate

- Important open defects are not hidden: interactive behavior is labelled NOT TESTED throughout.
- Unit-tested presentation logic, compile-checked API use and untested UI behavior are separated in
  this report, README and FINDINGS.
- The prototype makes no latency, stealth, capture-exclusion or OMP-policy enforcement claim.
- All sample content is synthetic; no private files/history, microphone/audio, screenshots,
  network or persistent deletion path exists.
- Global-hook exclusion is explicitly scoped to 003 and does not contradict the separately owned
  005 spike.

---

## Addendum — local ad-hoc bundle signing phase (appended 2026-10-26)

This addendum is appended after the original report. It does **not** rewrite the earlier
implementation evidence or the earlier packaging state; those sections above remain the record of
what was done and observed before this addendum. At that time the bundle was assembled without an
explicit bundle-signing step and was never launched. A pre-addendum `codesign -dv` check showed the
executable carried SwiftPM's linker ad-hoc signature while the bundle was not sealed with its
`Info.plist`/resources (`Signature=adhoc`, `Info.plist=not bound`, `Sealed Resources=none`,
auto-generated `Identifier=EscalierShell-…`). The current state below is different.

### Owner direction and scope

The owner directed a bounded packaging addendum: locally ad-hoc sign the `.app` so local launch can
be tested later, without certificate creation, keychain trust/identity selection, entitlement
grants, `--deep` signing, Gatekeeper/TCC/quarantine policy changes, GUI launch or unrelated edits.
The coordinator sends this delta to the already-running packaging reviewer.

### RED — signing guard before implementation

A static `PackagingScriptTests` case was added first. It requires the package script to sign after
assembly and verify after signing, rejects `--deep`/`--keychain`/`--entitlements`/`--options`/
`|| true`, and requires an executable failure-propagation harness. With the package script still
unsigned, the focused test failed:

```text
Test Case '...testPackagingScriptAdHocSignsThenVerifiesAndGuardsFailureModes' failed
error: Package script must ad-hoc sign the assembled bundle after assembly
Executed 1 test, with 1 failure (0 unexpected) in 0.044 (0.044) seconds
```

Log: `.build/logs/signing-red-test.log`. Exit 1.

### Implementation

`tools/package-app.sh` now does the following after copying the executable, `Info.plist` and
`PkgInfo`, and after `plutil -lint`:

```sh
codesign --force --sign - --timestamp=none "$APP"
codesign --verify --strict --verbose=2 "$APP"
```

It uses `set -euo pipefail`, so a nonzero signing or verification exit aborts packaging. The script
does not select a signing identity, access a keychain, create a certificate, add entitlements, use
`--deep`, or launch the app. No nested code is present: the bundle contains only the main executable
and system-framework dependencies. The success message now says the bundle is ad-hoc signed, not
notarized and not launched.

`tools/test-package-signing.sh` is the executable failure-propagation harness. It substitutes a
fake `codesign` under `.build/signing-test/bin` and checks two modes:

- `sign-fail`: fake signer exits 42; packaging must fail and verification must not be attempted.
- `verify-fail`: fake signer succeeds, fake verifier exits 43; packaging must fail after the sign
  call.

The harness then performs a genuine packaging run, strict verification, and checks the signature
facts. This is the negative/tamper evidence: swallowing either exit would make the harness fail.
`PackagingScriptTests` statically guards the harness modes and the exact commands/order in the
package script.

### GREEN and actual signature evidence

Focused guard: `.build/logs/signing-static-test.log` → 1 test passed, exit 0.
Full suite: `.build/logs/green-test-final.log` → **36 tests, 0 failures**, exit 0.
Preserved-test check: `swift test --skip PackagingScriptTests` →
`.build/logs/pre-signing-35-tests.log` → **35 tests, 0 failures**, exit 0. The original 35 tests
remain present and passing; one packaging/signing guard test was added.

Signing guard:

```text
PASS: signing failure propagated (status 42); verify not attempted
PASS: verification failure propagated (status 43) after signing
```

Log: `.build/logs/signing-guard.log`, exit 0.

Actual package (`tools/package-app.sh`, `.build/logs/package-final.log`):

```text
.build/EscalierShell.app/Contents/Info.plist: OK
.build/EscalierShell.app: replacing existing signature
.build/EscalierShell.app: valid on disk
.build/EscalierShell.app: satisfies its Designated Requirement
Packaged and ad-hoc signed .build/EscalierShell.app (not notarized, not launched)
```

Actual strict verification (`codesign --verify --strict --verbose=2`, exit 0; log
`.build/logs/signing-verify.log`):

```text
.build/EscalierShell.app: valid on disk
.build/EscalierShell.app: satisfies its Designated Requirement
```

Exact `codesign -dv --verbose=4` facts (exit 0; `.build/logs/signing-verify.log`):

```text
Identifier=local.escalier.spike003.shell
Format=app bundle with Mach-O thin (arm64)
CodeDirectory v=20400 size=3894 flags=0x2(adhoc) hashes=115+3 location=embedded
Signature=adhoc
Info.plist entries=11
TeamIdentifier=not set
Sealed Resources version=2 rules=13 files=0
```

### Current status distinctions

- Locally ad-hoc signed: **yes** (`Signature=adhoc`, code-directory flags `0x2(adhoc)`).
- Strict code-signature verification: **yes** (`valid on disk`, `satisfies its Designated
  Requirement`).
- Developer ID identity: **no**; `TeamIdentifier=not set`.
- Notarization: **no**; no notarization/ticket step was performed.
- Gatekeeper approval: **not claimed and not tested**; no `spctl`, quarantine or policy change was
  made.
- Bundle launch: **NOT TESTED**; no app was launched.
- Dock/icon/activation identity: **NOT TESTED**.
- UI visual/keyboard/focus/scroll/VoiceOver: **NOT TESTED**, unchanged from above.

### Files changed by this addendum only

- `tools/package-app.sh` (assembly → ad-hoc sign → strict verify; failure-propagating)
- `tools/test-package-signing.sh` (new executable failure harness)
- `Tests/EscalierCoreTests/PackagingScriptTests.swift` (new static guard; one added test)
- `README.md`, `FINDINGS.md`, and this appended report section (current/historical status wording)
- No changes to `PLAN.md`, coordinator review records, other spikes, Git index or commits.
