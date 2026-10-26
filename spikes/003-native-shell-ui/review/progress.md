# SDD ledger — plan: spikes/003-native-shell-ui/PLAN.md

This ledger also coordinates the independent `../004-window-capture-focus/PLAN.md` task. User approved parallel shell/UI/stealth spikes on 2026-10-26. They use synthetic data only; GUI/capture permission and runtime evidence remain a separate interactive step. Retain plans/tests/findings, no automatic cleanup.

## Preflight table

| Task/pair | Interface/internal consistency | Disposition |
|---|---|---|
| Native UI | Pure synthetic presentation state + headless tests; AppKit/SwiftUI build; no data/inference integration | No production behavior claim. GUI visuals/focus NOT TESTED by build. |
| Capture/focus | Native policy fixture + local static sender/receiver/event page; unit configuration tests + compile/static checks | Native flags are not receiver pixels; no getDisplayMedia call before human source/permission choice. |
| UI ↔ capture/focus | Independent Sources/Tests/tools under separate directories, no shared implementation | No file conflicts or cross-dependency; compare findings later. |
| Both ↔ root docs | Existing documentation worker owns root index/guidance | Workers report actual commands; coordinator integrates links/status. |

## State

- Native preflight complete; headless/compile/static slice GO. Shell initial/signing and capture/focus fix reviews approved. Both retained headless tasks complete; runtime remains separate and NOT RUN.
- ASR engine/runner, fixture, claim-trace and current-tree guidance fixes passed their scoped reviews. Four real-model ASR arms completed separately with actual Metal backend evidence; findings await the final broad integration review.
- Public GitHub repository created and read back as `isPrivate:false`: `https://github.com/fabzter/escalier`. No commits pushed yet.
- Initial local Git branch `spike/transcription`, personal author/committer. Coordinator-only commits avoid shared-index races.

## Preflight and dispatch

- `native-spikes-preflight`: GO for headless/compile/static slice; runtime conditional. N-01 ownership expanded to Package.swift/resources/bundle/test manifests; N-06..N-09 pure-state/input/test boundaries and all 004 runtime/static oracles captured in preflight-resolutions.md.
- `native-shell-ui` and `window-capture-focus` dispatched together with disjoint directory ownership; no GUI launch, getDisplayMedia or permission requests. Workers compile/test only and retain implementation reports.
- Both receive independent spec/quality review after reports. No runtime result is inferred from compilation.

## Shell and keyboard checkpoint

- `native-shell-ui` initial `11bd597`: meaningful behavioral RED (33 tests, 143 assertion failures), GREEN (35 XCTest cases, zero failures), native build and packaging without an explicit packaging-signing step. The earlier "unsigned" description does not establish absence of linker ad-hoc signing. Independent spec/quality review approved with seven deferred minors. The app was not launched.
- Global keyboard routing is owned only by separate spike 005, explicitly authorized by the owner's subsequent request. 003 remains hook-free and its scoped source audit is unchanged; in-app Cmd+1..5 equivalents are provisional, not browser no-bubble evidence.
- Spike 005 follow-up `94c895b` addressed original adapter/focus/close findings; settling-phase teardown regression fixed in `784a020` passed scoped round-2 spec/quality review with no new important breakage. Headless keyboard task complete. Native tap activation, exact target/chords/text, GUI and TCC grants remain behind live human approval.
- No rendered UI, focus/shortcut delivery, receiver pixels, capture exclusion or global-keyboard runtime case has been tested.

## Signing and independent-review checkpoint

- Owner explicitly approved local self-signing for launch testing. 003 addendum `a79f12e` uses local ad-hoc signing plus strict verification, with no certificate/Keychain trust or Gatekeeper/TCC/quarantine change. Scoped signing review PASS/APPROVED, zero important findings; no second full shell review.
- Coordinator ran 36 XCTest cases with no failures, exercised fake signing/verification failures (42/43), repackaged the genuine `.build/EscalierShell.app` and strictly verified its ad-hoc signature. Identifier `local.escalier.spike003.shell`, TeamIdentifier not set; arm64 Mach-O and plist lint verified. Launch/Dock identity/GUI remain NOT TESTED.
- 004 fix `0b69d2c` addresses missing receiver bytes/timestamp fields and treatment-only occlusion, corrects historical signing interpretation and includes explicit signing. Scoped re-review PASS for P1..P5; no new important breakage. Coordinator verified 54 Swift + 80 Node cases, both static audits, rebuild and genuine ad-hoc strict verification. No launch/capture.
- Spike 005 round-2 coordinator verification: 69 core + 15 adapter XCTest cases (84 total), zero failures; package/lint/ad-hoc sign/strict verify succeeded. CDHash `1b49aea7cb5d1c576b06302eded608bc5899792e`, binary SHA-256 `db1c37a22f32186b6107ed6ff1f4b11df0098e2388bec92f4e5d6ed8a8fc1dc1`. Node's unchanged 12-case suite passed in the worker's round-2 verification. All runtime rows remain NOT RUN; headless tests cannot prove actual OS suppression, browser non-delivery or focused-input restoration.
- Deferred minor lists are retained in 003/004 independent reports and rolled up in the 001 ledger for the single final broad review. 003 has seven original and two signing-test guard/detail notes; runtime boundaries remain unchanged.
- Computer helper capability-only preflight reports Accessibility/input/capture permission denied. No desktop was observed or controlled, no app launched and no permission changed; helper closed. This does not establish anything about Escalier's own TCC/launch behavior.
- Final integration closeout: broad review and the single scoped documentation re-review are complete in `../../001-transcription/review/final-integration-review.md` and `../../001-transcription/review/final-fix-review.md`. All shell/signing residuals were explicitly retained for their bounded-prototype reasons, not silently dropped. Fresh coordinator verification again passed 36 XCTest cases and strict readback/plist of the existing ad-hoc shell bundle; full matrix evidence is in `../../001-transcription/review/final-validation.md`. No app launch or runtime claim.
