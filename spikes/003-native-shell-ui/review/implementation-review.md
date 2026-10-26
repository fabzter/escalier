# Spike 003 implementation review

Date: 2026-10-26
Reviewer: independent task reviewer (spec + quality)
Scope: bounded synthetic native shell/UI prototype for spike 003
Diff reviewed once: `spikes/001-transcription/.tools/reviews/native-shell-ui.diff`, range
`e50b023..11bd597` (27 added files, 3,707 added lines, no deletions).
Evidence accepted: coordinator rerun of
`swift test --package-path spikes/003-native-shell-ui -q` — 35 XCTest cases, zero failures,
0.055 s, cached build, exit 0. I did not rerun the suite or launch the GUI. The test target
depends only on `EscalierCore` (`Package.swift:25-29`), so those 35 tests cover the pure model
and static audits; `Sources/EscalierShell` is compile-checked by the worker's `swift build`
evidence. Interactive behaviour remains **NOT TESTED** by design.

### Checks run

- Read the diff once and checked every hunk against the five requested checks, the retained-state
  rules, the audit, and the labelled evidence boundaries.
- Accepted the coordinator's headless test/build evidence; did not rerun the suite or launch the GUI.
- Inspected `.build/logs/build-3.log` and `build-final.log`: neither captured output contains
  `warning:` lines. `build-final.log` is an incremental no-op, so `build-3.log` is the relevant
  full-compile log.
- `git check-ignore` confirms `spikes/003-native-shell-ui/.build/` is ignored.
- Confirmed top-level `NSMenu` visible titles come from the attached submenu titles, so the empty
  `NSMenuItem` titles at `Sources/EscalierShell/AppDelegate.swift:46,62,74,91,115` are not a
  label defect.
- A minimal `swiftc -typecheck` probe of the `NSApp.activate(ignoringOtherApps:)` call produced no
  diagnostic with the installed SDK; no warning finding.

## Spec Compliance

- ✅ Spec compliant with the bounded 003 requirements. Every requested capability has a
  corresponding implementation, test, and labelled limitation; no requested file is missing and
  no production feature outside the bounded prototype is claimed.
- ⚠️ Cannot verify from the diff: actual window layout at 1240×840 / minimum 1100×700, menu
  key-equivalent dispatch, focus and shortcut bubbling, VoiceOver announcements, scroll-position
  stability, runtime absence of permission prompts, and bundle launch/Gatekeeper/Dock identity.
  These are explicitly marked **NOT TESTED** in `README.md:148-153` and `FINDINGS.md:35-39`, and
  require the separate authorized interactive review. Build success is not treated as a UI pass.

### Verified against the requested checks

1. **Five distinct FR-07 actions.** `AssistanceAction` enumerates five cases with distinct raw
   values, routes/labels/hints/key equivalents (`Sources/EscalierCore/Assistance.swift:104-153`);
   the AppKit menu attaches all five with `⌘1`–`⌘5` (`Sources/EscalierShell/AppDelegate.swift:95-105`);
   the UI buttons show label, route, and hint (`Sources/EscalierShell/AssistancePanelView.swift:44-71`);
   dispatch appends a route-specific synthetic log entry (`Sources/EscalierCore/ConversationState.swift:108-117`).
   Tests pin five cases, five distinct routes/labels/hints/key equivalents, and five distinct
   logged routes (`Tests/EscalierCoreTests/PhaseAndRoutingTests.swift:20-44,46-59`).
2. **Stable source identity/range/anchor with arrival vs navigation.** `ReferenceSelection` carries
   candidate ID, UTF-16 `TextRange`, and anchor (`Sources/EscalierCore/Models.swift:105-131,154-160`);
   candidate arrival preserves a current selection and only auto-selects when nothing is selected
   and no unresolved state exists (`Models.swift:176-221`). Explicit next/previous changes the
   selection and clears the unseen indicator (`Models.swift:223-243`). Removing the selected
   candidate sets an explicit `.selectedCandidateRemoved` with no selection, and later arrival does
   not silently resolve it (`Models.swift:255-264`; tests
   `Tests/EscalierCoreTests/ReferenceStabilityTests.swift:48-65,66-86,88-104,117-131,150-162`).
   The panel displays source ID, locator, range, anchor, and an unresolved banner
   (`Sources/EscalierShell/ReferencePanelView.swift:56-64,114-142`). Scroll-viewport stability is
   explicitly **NOT TESTED** (`ReferencePanelView.swift:106`).
3. **Per-conversation isolation.** `ConversationState` owns capabilities, reference, assistance,
   retained aggregates, and retained selection (`Sources/EscalierCore/ConversationState.swift:40-47`);
   `ConversationStore.mutateCurrent` scopes every mutation to the selected conversation
   (`Sources/EscalierCore/ConversationStore.swift:31-37`). Tests cover model/tool/skill isolation,
   invalid-ID rejection, phase/reference isolation, routing isolation, retained deletion isolation,
   and cross-conversation retained selection (`Tests/EscalierCoreTests/ConversationConfigurationTests.swift:6-35,37-46,48-70`;
   `Tests/EscalierCoreTests/PhaseAndRoutingTests.swift:86-100`;
   `Tests/EscalierCoreTests/RetainedResultsTests.swift:44-78,80-98,100-112`).
4. **Synthetic stream + retained aggregate/delete semantics.** Assistance messages have stable UUID
   identity, ordered chunks, completion state, and late-chunk rejection
   (`Sources/EscalierCore/Assistance.swift:66-103`; `ConversationState.swift:167-188`). The manual
   stream advances one message through ordered chunks and completes it
   (`ConversationStore.swift:139-167`; tests `Tests/EscalierCoreTests/AssistanceAndStreamingTests.swift:90-112,6-24,26-38`).
   Retained aggregates are immutable value snapshots of transcript, retrieval log, and assistance
   (`ConversationState.swift:203-209`); deletion requires an explicit selection and removes only
   that aggregate (`ConversationState.swift:225-233`), leaving sibling aggregates, sibling
   conversations, transcripts, and source excerpts intact (`Tests/EscalierCoreTests/RetainedResultsTests.swift:6-29,31-42,44-78,80-98`).
   The UI labels the storage as in-memory/no disk data and confirms deletion
   (`Sources/EscalierShell/RetainedResultsPanelView.swift:21,120,126-133`).
5. **AppKit/SwiftUI wiring and labelled limitations.** `main.swift:1-9` is minimal AppKit
   bootstrapping; `AppDelegate` owns the single `NSWindow`, `NSHostingController`, in-app menu, and
   app termination (`Sources/EscalierShell/AppDelegate.swift:8-175`). SwiftUI owns the content
   hierarchy (`Sources/EscalierShell/RootView.swift:8-27`). MOCK/NOT CONNECTED chips are visible in
   the status strip (`Sources/EscalierShell/Theme.swift:57-79`), assistance panel
   (`AssistancePanelView.swift:25,69,166`), retained panel, sidebar, and header. No claim of runtime
   enforcement, capture, OMP, networking, stealth, latency, or persistence is made; GUI/keyboard/
   focus/scroll/VoiceOver limits are stated in the app, README, FINDINGS, and report.
6. **Heuristic guard sensitivity.** `SourceAuditTests` scans this spike's `Sources/**/*.swift` for
   the listed global-input, permission, capture, networking, process-spawn, defaults, and
   file-write/delete tokens (`Tests/EscalierCoreTests/SourceAuditTests.swift:17-44,65-76`), checks
   sensitive `Info.plist` usage keys (`:93-106`), and checks the manifest for remote dependencies
   (`:108-116`). The positive-control test proves the token matcher detects planted tokens and
   ignores benign text (`:79-90`). It is correctly described as a 003-scoped heuristic rather than
   a runtime/entitlement proof (`README.md:57-62,72-76`; `FINDINGS.md:73-76`). See Minor 4 for the
   enumeration-sensitivity gap.

## Strengths

- Clean separation of pure `EscalierCore` presentation state from AppKit/SwiftUI shell code;
  all behavioural assertions run without AppKit.
- Reference stability is expressed as an opaque value (candidate ID + range + anchor), not a row
  index or scroll offset, so arrival/removal/navigation are independently testable.
- Removal of the selected reference is deliberately distinct from arrival: no silent sibling jump,
  and arrival after removal remains unresolved.
- Retained results are value snapshots, making immutability and sibling isolation structural
  rather than dependent on a copy helper; deletion is explicitly selected and confirmed.
- The evidence ledger and README consistently separate HEADLESS-PASS, COMPILE/PACKAGE, and
  NOT TESTED claims; the source audit includes a positive control and is explicitly scoped away
  from spike 005.
- Five action routes are distinct, visible, logged, and labelled MOCK; the screenshot route is an
  explicit placeholder, not a capture claim.
- The local diagram is complete native vector content with visible alt text and an accessibility
  label; there is no image pipeline or progressive-image claim.
- The package is dependency-free, builds in `.build/`, and the packaging script fails clearly
  without installing tools and does not launch the app.

## Issues

### Critical (Must Fix)

None.

### Important (Should Fix)

None.

### Minor (Nice to Have)

1. **Retained-results inspection does not show retained assistance text.**
   `Sources/EscalierShell/RetainedResultsPanelView.swift:89-94` lists each retained assistance
   message only as `provenanceLabel · N chunks`, never rendering `message.text` (or the local
   diagram alt text). `README.md:145` tells the reviewer to “inspect its transcript/retrieval
   log/assistance”, and `review/implementation-report.md:156` claims an “inspection UI” for all
   three. The data is retained correctly (`ConversationState.swift:203-209`; tests
   `Tests/EscalierCoreTests/RetainedResultsTests.swift:6-29`), so this is a display-completeness
   gap, not data loss. Minimal fix: render `message.text` (and a diagram/alt-text summary for
   `.localImage`) in the snapshot viewer, or narrow the README/report wording.

2. **Menu key equivalents bypass the phase gate applied to the five action buttons.**
   The action buttons are disabled outside live conversation
   (`Sources/EscalierShell/AssistancePanelView.swift:69`), but the menu items are always enabled
   and dispatch unconditionally (`Sources/EscalierShell/AppDelegate.swift:95-105,155-162`).
   The “Start live conversation” menu item is likewise always enabled even when the phase is
   already conversation (`AppDelegate.swift:66-72`; no-op at `ConversationState.swift:87-91`).
   A reviewer can therefore log an FR-07 route from preparation via `⌘1`–`⌘5` while the UI presents
   those actions as unavailable. Minimal fix: implement `NSMenuItemValidation`/`validateMenuItem`
   (or refresh `isEnabled`) from `store.currentConversation?.phase == .conversation`, and disable
   the start item outside preparation; alternatively remove the button gate if menu dispatch in
   preparation is intentional and document it.

3. **Shortcut hint and key equivalent duplicate the same mapping and can drift.**
   `Sources/EscalierCore/Assistance.swift:125-133` and `:135-143` encode `⌘1`–`⌘5` twice.
   `Tests/EscalierCoreTests/PhaseAndRoutingTests.swift:23-36` only asserts each collection is
   distinct, not that each hint corresponds to its key equivalent. A one-sided edit would make the
   visible hint lie about the shortcut. Minimal fix: derive `shortcutHint` from `keyEquivalent`
   (`"⌘\(keyEquivalent)"`) or add a pairing assertion for every action.

4. **Source-audit positive control exercises the matcher, not the file scanner.**
   The positive control plants tokens in a string and calls `matches(in:)`
   (`Tests/EscalierCoreTests/SourceAuditTests.swift:79-90`); the scanner itself
   (`:46-58`) is covered only by `files.count >= 2` (`:67`). A regression that drops one shell
   source from enumeration would still pass while the audit silently misses it. The audit is
   explicitly heuristic, so this does not invalidate its current evidence. Minimal fix: assert the
   scan includes every expected source file (e.g. `AppDelegate.swift`, `ConversationStore.swift`)
   or add a temporary-file planted-token scan.

5. **A snapshot retained mid-stream displays “streaming” permanently.**
   `ConversationState.retainSnapshot` copies `assistance` as-is (`ConversationState.swift:203-209`),
   so a message with `isStreaming == true` is frozen into the value snapshot. The retention button
   is enabled during a stream (`RetainedResultsPanelView.swift:106-110`), and the inspection label
   then says “streaming” (`:91`) even though the snapshot can never receive another chunk.
   Minimal fix: normalize `isStreaming = false` on copied messages, or label the snapshot as
   “captured mid-stream” and/or disable retention while a stream is active.

6. **Preparation empty-state copy contradicts the documented demo behaviour.**
   `Sources/EscalierShell/ConversationDetailView.swift:101` says “Start the conversation to use the
   invented live sample”, but `startConversation()` only flips the phase
   (`Sources/EscalierCore/ConversationState.swift:87-91`) and never adds the live transcript; the
   preparation conversation stays empty. `FINDINGS.md:82-84` correctly documents the separate live
   sample, but the in-app copy still promises otherwise. Minimal fix: say the preparation sample
   stays empty after the transition and point to the separate live demo.

7. **Report describes the window with its minimum size as if it were the initial size.**
   `review/implementation-report.md:199` says “SwiftUI layout in a 1100×700 window”, while
   `Sources/EscalierShell/AppDelegate.swift:29` creates a 1240×840 content rect and
   `:36` sets 1100×700 only as `window.minSize`. Minimal fix: state the initial 1240×840 content
   size and the 1100×700 minimum so a reviewer resizes the right baseline.

## Assessment

**Spec compliance:** ✅ — all bounded 003 deliverables are implemented and covered as described;
the only unverifiable items are interactive GUI behaviours that the task explicitly leaves to a
separate permissioned review and that the implementation labels NOT TESTED.

**Task quality:** Approved — the pure model, isolation rules, reference-stability semantics,
retained-result deletion scoping, route enumeration, and audit structure are clean, focused, and
well tested. The remaining findings are minor UI-completeness, menu-consistency, drift-guard,
edge-case-label, and documentation-accuracy issues; none undermines the bounded prototype or its
stated evidence boundaries.
