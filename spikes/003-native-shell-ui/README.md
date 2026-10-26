# Spike 003 — native macOS shell and UI prototype

Status: **bounded prototype implemented; 36 headless tests and native build pass; local `.app`
is ad-hoc signed and strictly verified; GUI and bundle-launch behavior NOT TESTED.**
Date: 2026-10-26. Owner-approved parallel research spike; not a production UI commitment, a
full-app implementation approval, or evidence of stealth, capture exclusion or latency. Layout,
style and exact shortcut bindings are low-fidelity, provisional and reversible.

Primary direction: [ADR-0001](../../docs/decisions/0001-native-macos-and-omp-rpc.md).
Functional panel behavior: [requirements](../../docs/requirements.md) (especially FR-05, FR-06,
FR-07, FR-10, FR-14, FR-15, FR-16). Binding preflight amendments:
[review/preflight-resolutions.md](review/preflight-resolutions.md).

## Question

Can a dependency-free SwiftUI content layer with an AppKit window/application coordinator
demonstrate:

- explicit preparation → live-conversation transition;
- a synthetic two-source transcript;
- a reference panel whose selected source does not move when another candidate arrives, with
  explicit next/previous navigation and an explicit unresolved state after removal;
- five distinct FR-07 assistance routes with provisional in-app shortcuts;
- per-conversation mock model/tool/skill selection;
- incremental synthetic text and a complete local vector image with a text alternative; and
- in-memory synthetic retained snapshots with scoped, selected deletion —

without real files, vault/history, audio, screenshots, OMP/LLM calls, networking, persistence,
global input hooks or permission requests?

## What is implemented

- **Pure core model** (`Sources/EscalierCore`):
  - immutable synthetic source identities, citations, excerpts, UTF-16 ranges and anchors;
  - `ReferenceState` stable selection, unseen-candidate indicator, next/previous navigation,
    explicit selection and explicit unresolved-after-removal state;
  - `ConversationState` phase transition, two source identities, retrieval log, assistance
    message/chunk identity, complete local diagram item, per-conversation mock capability state,
    and retained aggregates;
  - `ConversationStore` selection scoping and per-conversation mutation isolation.
- **Native shell** (`Sources/EscalierShell`):
  - `NSApplication` + `AppDelegate` window coordinator hosting SwiftUI content;
  - one window with sidebar, transcript, reference panel, assistance panel and retained-results
    panel;
  - app-menu assistance actions with provisional `⌘1`–`⌘5` equivalents and reference
    previous/next menu items. These are **in-app menu shortcuts only**; no global monitor, event
    tap, Accessibility/Input Monitoring API or permission prompt exists in this spike;
  - explicit `MOCK` / `NOT CONNECTED` status chips, including the separate
    `005-global-keyboard-routing` boundary;
  - complete local vector diagram drawn with native SwiftUI shapes and visible alt text.
- **Headless tests** (`Tests/EscalierCoreTests`): 36 XCTest cases covering reference stability,
  routing, phases, isolation, retained aggregates, streaming, a static source audit and the
  packaging/signing guard.
- **Local build/packaging**: `Package.swift` (no dependencies) and
  `tools/package-app.sh` (builds, packages and **locally ad-hoc signs** `.build/EscalierShell.app`,
  then strictly verifies it; does not launch it). The signing-failure harness is
  `tools/test-package-signing.sh`.

## Synthetic and mock boundaries

- Every name, transcript line, source excerpt, citation, retrieval route, assistance message and
  diagram is invented. No owner or third-party history is present.
- The app contains no file/vault access, microphone or computer-audio capture, screen capture,
  browser automation, OMP RPC/LLM call, network client, database, preferences storage or
  persistent deletion. The source audit checks for the listed sensitive APIs and for absence of
  sensitive `Info.plist` usage descriptions.
- Transcript source identities are fixed synthetic labels **ME** and **OTHER SIDE**.
- The screenshot assistance action is a **route placeholder only**. It logs a synthetic route
  summary and explicitly records that no screenshot is captured or stored.
- Model, tool and skill controls are **MOCK** presentation state. They do not select an OMP model,
  route a request or enforce a tool/skill policy.
- The local diagram is complete local vector content, not a generated/downloaded image and not a
  progressive-pixel test.
- Retained snapshots and deletion affect only in-memory synthetic state. No save/deletion policy
  for the eventual application is settled by this spike.
- **No global keyboard hook is implemented in 003.** The owner has scoped active global
  interception and no-bubble routing to a separate spike, forthcoming at
  [`../005-global-keyboard-routing/PLAN.md`](../005-global-keyboard-routing/PLAN.md). That work
  requires its own independent review and live human permission/activation approval. The 003
  source audit is an audit of this UI prototype, not a project-wide prohibition.

## Build and test

Environment observed locally: macOS 27.0.1 arm64, Xcode 27.1 (27A9275), Apple Swift 6.4
(`swift-driver 1.168.6`), macOS 14 deployment target. Build outputs are confined to this spike's
ignored `.build/`. No package or host installation is performed.

From this directory:

```sh
cd spikes/003-native-shell-ui

# Headless model + static-audit tests.
swift test

# Native executable compile check (SwiftUI + AppKit).
swift build

# Package, locally ad-hoc sign and strictly verify a local .app bundle; does not launch it.
tools/package-app.sh

# Headless signing guard: fake signer/verifier failures must propagate, then
# rebuild the genuine ad-hoc signed bundle and verify it. Does not launch it.
tools/test-package-signing.sh
```

Observed final results (2026-10-26):

- `swift test` → **36 tests, 0 failures**, exit 0. The original 35 tests are preserved; one
  packaging/signing guard test was added.
- `swift build` → **Build complete!**, exit 0, no warnings in the captured log.
- `tools/package-app.sh` → `Info.plist: OK`; `codesign` replaces the linker signature, signs the
  assembled bundle ad hoc, and verification reports `valid on disk` + `satisfies its Designated
  Requirement`; `.build/EscalierShell.app`; exit 0; **not launched**.
- `tools/test-package-signing.sh` → fake signing failure exits 42 and is not swallowed; fake
  verification failure exits 43 after signing and is not swallowed; genuine bundle verifies; exit 0.

Exact signature facts from `codesign -dv --verbose=4`:

```text
Identifier=local.escalier.spike003.shell
Format=app bundle with Mach-O thin (arm64)
CodeDirectory v=20400 size=3894 flags=0x2(adhoc) hashes=115+3 location=embedded
Signature=adhoc
Info.plist entries=11
TeamIdentifier=not set
Sealed Resources version=2 rules=13 files=0
```

This is **local ad-hoc signing**, not notarization, not a Developer ID signature and not
Gatekeeper approval. The signed bundle has not been launched. Local launch remains a separate
manual test; do not change Gatekeeper, TCC or quarantine state to make it launch.

Logs are under ignored `.build/logs/`: `red-test.log`, `green-test-final.log`,
`build-final.log`, `package-final.log`, `signing-red-test.log`, `signing-static-test.log`,
`signing-guard.log`, `signing-verify.log`, `pre-signing-35-tests.log`.

## Manual run and review — requires a human

The implementation worker did **not** launch, drive, screenshot or inspect the GUI. The following
is pending interactive evidence:

```sh
cd spikes/003-native-shell-ui
swift run EscalierShell
# or:
tools/package-app.sh
codesign --verify --strict --verbose=2 .build/EscalierShell.app
open .build/EscalierShell.app
```

`swift run` launches the bare SwiftPM executable, not the signed `.app`; use
`tools/package-app.sh` plus `open .build/EscalierShell.app` for a bundle-signature launch check.

The packaged bundle is locally ad-hoc signed (`Signature=adhoc`, `TeamIdentifier=not set`) so a
human may attempt local launch. That is **not** notarization, a Developer ID signature or Gatekeeper
approval, and this worker did not launch it. If macOS blocks the launch, stop and report it; do not
change Gatekeeper, TCC or quarantine settings. Bundle launch remains **NOT TESTED** until observed.

Review checklist (mark each **NOT TESTED** until directly observed):

1. Window opens at a usable size; sidebar/detail layout resizes without clipped critical controls.
2. Select **Synthetic preparation**; confirm phase is PREPARATION. Click **Start live
   conversation**; confirm phase changes to LIVE CONVERSATION without creating transcript lines or
   external activity. Switch conversations and confirm the transition does not leak.
3. In the live demo, confirm ME and OTHER SIDE transcript badges are visually distinct and all
   text is labelled synthetic.
4. Reference panel: selected passage is highlighted; source identity, locator, range and anchor are
   visible. Click **Simulate new candidate arrival**; confirm the selected passage/range/anchor
   stays fixed while the new-candidate banner appears. Click **Next**/**Previous**; confirm
   selection changes and the banner clears. Click **Simulate candidate removal** on a selected
   candidate; confirm an explicit unresolved state appears and no sibling is silently selected.
5. Click each of the five FR-07 action buttons and each `⌘1`–`⌘5` menu equivalent; confirm the
   displayed route changes distinctly and the UI says MOCK/no generation. Confirm no assistance
   text is produced.
6. Mock model/tool/skill controls: change them in one conversation, switch to the other and back;
   confirm isolation and that all status labels still say MOCK. Confirm no runtime policy appears
   to be enforced.
7. Click **Advance synthetic stream** repeatedly; confirm one message receives chunks in order and
   reaches a completed, non-streaming state. Confirm no timer/network activity.
8. Confirm the local vector diagram is visible, marked COMPLETE/LOCAL VECTOR, and its alt text is
   visible. VoiceOver behavior is untested.
9. Retained results: retain snapshots, select one, inspect its transcript/retrieval log/assistance,
   delete it after confirmation, and confirm the other snapshot, sibling conversation and source
   excerpts remain. Confirm labels say in-memory/no disk data.
10. Reference panel scroll-position stability: compare passage position before/after candidate
    arrival. This spike claims selection stability, **not** visual scroll stability; mark
    **NOT TESTED** unless separately observed.
11. Keyboard focus/menu-equivalent behavior and absence of shortcut bubbling into a browser are
    **NOT TESTED** here. Do not infer global-shortcut or stealth behavior from this shell. That
    belongs to the separate 005 spike and its permissioned runtime evidence.
12. Check for unexpected permission prompts or network/CPU activity. This spike should request
    none; stop and report if one appears.

No screenshot is included because no GUI was launched by the implementation worker.

## Findings

See [FINDINGS.md](FINDINGS.md) for the claim/evidence ledger and
[review/implementation-report.md](review/implementation-report.md) for red/green evidence,
self-review and limitations. Summary:

- Pure presentation semantics are exercised headlessly and pass.
- SwiftUI/AppKit API use and the `.app` bundle are compile/package-checked only; the bundle is
  locally ad-hoc signed and strictly verified, but not notarized, Gatekeeper-approved or launched.
- Actual visuals, keyboard focus, menu shortcut behavior, VoiceOver and scroll stability remain
  **NOT TESTED**.
- This prototype establishes no stealth, capture exclusion, OMP enforcement, latency or
  production readiness claim.
