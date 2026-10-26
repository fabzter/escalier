# Spike 003 findings — native shell and UI prototype

Date: 2026-10-26. Scope: synthetic, dependency-free prototype defined by
[PLAN.md](PLAN.md), [requirements](../../docs/requirements.md), [ADR-0001](../../docs/decisions/0001-native-macos-and-omp-rpc.md)
and [binding preflight resolutions](review/preflight-resolutions.md).

## Evidence ledger

Status vocabulary: **HEADLESS-PASS** = observed in `swift test`; **PACKAGE-TEST PASS** = the
headless `tools/test-package-signing.sh` harness ran to exit 0; **COMPILE/PACKAGE** = compiler or
packager succeeded, not a behavioral UI pass; **SIGNED/VERIFIED** = local ad-hoc `codesign` signed
and strict verification passed, not notarization, Gatekeeper approval or launch evidence;
**NOT TESTED** = needs interactive or measured evidence; **NOT IMPLEMENTED** = deliberately outside
this spike.

| Claim | Evidence | Status |
| --- | --- | --- |
| Five FR-07 actions have distinct nonempty routes, labels, hints and menu key equivalents | `PhaseAndRoutingTests.testFiveFR07ActionsHaveDistinctNonemptyRoutesAndHints`; action dispatch logs five distinct routes | HEADLESS-PASS |
| Preparation → conversation transition is explicit and idempotent; content does not reset | `PhaseAndRoutingTests.testPreparationTransitionsToConversationExplicitlyAndPreservesContent` | HEADLESS-PASS |
| Candidate arrival preserves selected candidate ID/range/anchor and raises a new-candidate indicator | `ReferenceStabilityTests.testCandidateArrivalPreservesSelectedIDRangeAndAnchor` and ConversationState forwarding test | HEADLESS-PASS |
| Explicit next/previous navigation changes selection and clears the indicator | `ReferenceStabilityTests.testNextNavigationChangesSelectionAndClearsNewCandidateIndicator` | HEADLESS-PASS |
| Removing the selected candidate yields explicit unresolved state and no silent jump | `ReferenceStabilityTests.testRemovingSelectedCandidateYieldsUnresolvedStateWithoutSilentJump`, arrival-after-removal test | HEADLESS-PASS |
| Source identities/citations/ranges are stable, synthetic and distinct | sample-content assertions in `ReferenceStabilityTests` | HEADLESS-PASS |
| Model/tool/skill selection is isolated per conversation; unknown IDs are rejected | `ConversationConfigurationTests` | HEADLESS-PASS |
| Retained aggregate contains transcript, retrieval log and assistance; snapshot is immutable after live mutation | `RetainedResultsTests.testRetainSnapshotCapturesTranscriptRetrievalLogAndAssistance`, `...ImmutableAfterLiveMutations` | HEADLESS-PASS |
| Deleting the selected in-memory aggregate leaves sibling aggregates, sibling conversations, transcript and source excerpts intact | `RetainedResultsTests.testDeletingSelectedAggregateLeavesOtherAggregatesSiblingsAndSourcesIntact`, `...RequiresAnExplicitSelection...` | HEADLESS-PASS |
| Synthetic streaming preserves stable message identity and chunk order; late chunks are rejected | `AssistanceAndStreamingTests` | HEADLESS-PASS |
| Manual synthetic stream exposes incremental chunks under one identity | `...testSyntheticStreamAdvancesIncrementallyUnderOneStableIdentity` | HEADLESS-PASS |
| Complete local image/diagram has nonempty alt text and a complete (non-progressive) delivery state | `AssistanceAndStreamingTests.testCompleteLocalDiagramHasAltTextAndNoProgressiveDelivery` | HEADLESS-PASS |
| Source-backed knowledge, suggested wording, general information and local image are distinctly labelled | `...testAssistanceProvenanceKindsAreDistinctAndLabelled` | HEADLESS-PASS |
| Model/tool/skill states are MOCK; input, permissions, OMP, screenshot capture and global shortcut routing are NOT CONNECTED | `PhaseAndRoutingTests.testRuntimeStatusesAreExplicitlyMockOrNotConnected` | HEADLESS-PASS |
| Screenshot action is only a logged placeholder; no capture occurs | `PhaseAndRoutingTests.testScreenshotRouteIsALoggedPlaceholderNotCapture`; no capture symbol in source audit | HEADLESS-PASS for route/status; NOT IMPLEMENTED as capture |
| 003 source tree contains no global input hook, permission request, capture API, network client, process spawn, preferences store or file deletion API from the audited list | `SourceAuditTests.test003SourcesContainNoGlobalInputHooksPermissionRequestsCaptureOrNetworking` | STATIC AUDIT PASS, heuristic and 003-scoped |
| `Info.plist` requests no Accessibility/Input Monitoring/Screen Recording/Microphone/Camera usage | `SourceAuditTests.testInfoPlistDeclaresNoSensitiveCapturePermissionUsage` | HEADLESS-PASS |
| Package has no remote dependency | `SourceAuditTests.testPackageHasNoRemoteDependency` | HEADLESS-PASS |
| Native executable compiles against installed macOS SDK | `swift build` → Build complete, exit 0; shell log has no warnings | COMPILE/PACKAGE |
| Local `.app` bundle can be assembled without installing anything | `tools/package-app.sh` → `Info.plist: OK`; `.build/EscalierShell.app`; not launched | COMPILE/PACKAGE |
| Local `.app` bundle is ad-hoc signed and strictly verified | `tools/package-app.sh`; `codesign --verify --strict --verbose=2` → `valid on disk`, `satisfies its Designated Requirement`; signature facts below | SIGNED/VERIFIED, not notarized/Gatekeeper/launch-tested |
| Signing and verification failure propagate through packaging | `tools/test-package-signing.sh` fake signer exit 42 (verify not attempted) and fake verifier exit 43 (after sign); `PackagingScriptTests` static guard | HEADLESS-PASS (static) + PACKAGE-TEST PASS (fake exits) |
| Window actually opens, lays out correctly, is usable at minimum size and has acceptable visual hierarchy | No GUI launch by worker | NOT TESTED |
| Menu shortcuts actually fire, have expected focus behavior and do not alter browser focus/text | No interactive keyboard test | NOT TESTED |
| Selected reference stays visually stable in the scroll viewport | Selection state is tested; viewport rendering is not | NOT TESTED |
| VoiceOver announces diagram alt text and status badges usefully | Accessibility label exists in code | NOT TESTED |
| No permission prompt appears at runtime | No GUI launch; no permission API in source | NOT TESTED at runtime |
| OMP model/tool/skill policy is enforced | Deliberately mock | NOT IMPLEMENTED / no claim |
| Screenshot capture or image generation | Deliberately absent | NOT IMPLEMENTED |
| Global keyboard interception / no-bubble typing | Deliberately absent from 003; separate 005 spike owns it | NOT IMPLEMENTED in 003 |
| Stealth, capture exclusion, undetectability | Outside this spike | NO CLAIM |
| Latency or runtime performance | Only test/build wall-clock observed, not measured product latency | NOT MEASURED |
| Persistent save/delete policy | In-memory synthetic only | NOT SETTLED |

## TDD evidence

- RED (model phase): `swift test` against an API-only skeleton (no behavior) → 33 tests executed,
  143 failures, 0 unexpected; the then-three static audit tests already passed. Log:
  `.build/logs/red-test.log`.
- GREEN (pre-signing phase): `swift test` → 35 tests, 0 failures; build/package also passed at
  that time. Current proof that the original 35 tests are preserved:
  `.build/logs/pre-signing-35-tests.log` (35 tests, 0 failures, `PackagingScriptTests` skipped);
  the original report records the earlier run, and `.build/logs/build-final.log` remains.
- RED (signing addendum): `PackagingScriptTests` failed because `tools/package-app.sh` did not yet
  sign/verify. Log: `.build/logs/signing-red-test.log`.
- GREEN (signing addendum): 36 tests, 0 failures; `tools/test-package-signing.sh` proves fake
  signing failure (exit 42) and verification failure (exit 43) propagate; genuine bundle verifies.
  Logs: `.build/logs/green-test-final.log`, `signing-static-test.log`, `signing-guard.log`,
  `signing-verify.log`, `package-final.log`.
- The original 35 tests are preserved; one packaging/signing guard test was added. The skeleton was
  removed before the implementation was reported green. Exact commands/results and self-review are
  in [review/implementation-report.md](review/implementation-report.md).

## Decisions worth carrying forward

- The core model is a pure value-type presentation layer. A `ConversationStore` wrapper publishes
  changes for SwiftUI, but all rules are headless-testable without AppKit or SwiftUI.
- Reference stability is expressed as an opaque `ReferenceSelection` (candidate ID + range +
  anchor). This is a stronger identity than a row index or scroll offset.
- New-candidate arrival only auto-selects when there is no selection and no unresolved state.
  After selected-candidate removal, arrival does not silently resolve; explicit selection is
  required.
- Retained snapshots are value copies in memory. The UI has no code path for disk persistence.
- Mock capability IDs are validated against a local catalog. This prevents arbitrary strings from
  appearing as if they were a real selection, while still enforcing nothing.
- The complete local diagram is native vector content with an accessibility label and visible
  alt text; no image pipeline is implied.

## Gaps and risks

- Headless tests prove state semantics, not rendered behavior. SwiftUI layout, focus, menu
  dispatch, VoiceOver and scroll anchoring need a separate interactive review.
- The source audit is a substring check over this spike's Swift sources and a few `Info.plist`
  keys. It is not a binary entitlement inspection, not a runtime trace and not a project-wide
  policy. The related 005 spike may legitimately contain active interception APIs outside 003.
- The `.app` is locally ad-hoc signed and strictly verified (`Signature=adhoc`,
  `TeamIdentifier=not set`, Info.plist bound, sealed resources), but it is **not notarized**, not a
  Developer ID signature and not Gatekeeper-approved. It was never launched. Dock/icon/activation
  identity and bundle-launch behavior remain untested. The report's signing addendum preserves the
  earlier pre-addendum unsigned-bundle evidence; that earlier state is not the current one.
- The window uses `.regular` activation policy for visibility. NFR-04 (no Dock icon) is not
  demonstrated or claimed here.
- The sample preparation conversation starts with no transcript. Starting it demonstrates the
  phase transition but does not fabricate a live stream; the separate live sample contains the
  invented transcript.
- A reviewer can simulate candidate arrival and removal, but there is no real file ingestion,
  search index or canonical source store. FR-05/FR-14 integration is future work.
- The screenshot route is only a route. FR-08 target selection and FR-07 screenshot interpretation
  are not implemented.
- No runtime OMP, model, tool or skill behavior exists to evaluate. Mock selections must not be
  cited as policy enforcement evidence.

## Signing addendum — local ad-hoc bundle signing

Added after the original findings on 2026-10-26 at explicit owner direction. This section
supersedes only the current bundle-signature status; earlier model/signing-phase evidence is kept
as historical.

- `tools/package-app.sh` now assembles the bundle, runs `plutil -lint`, then:
  `codesign --force --sign - --timestamp=none "$APP"` followed by
  `codesign --verify --strict --verbose=2 "$APP"`.
- No certificate creation, keychain trust/identity selection, entitlement grants, `--deep` signing,
  Gatekeeper/TCC/quarantine policy changes or GUI launch were performed. The bundle contains only
  system frameworks and the main executable, so no nested-code signing path is in play.
- `PackagingScriptTests` statically guards the exact sign/verify order, requires `set -euo
  pipefail`, rejects `--deep`/`--keychain`/`--entitlements`/`--options`/`|| true`, and checks the
  failure harness.
- `tools/test-package-signing.sh` substitutes a fake signer/verifier: sign failure exits 42 with no
  verification attempted; verify failure exits 43 after signing. Both must abort packaging. It then
  restores and verifies the genuine signed bundle.
- Observed actual package/verify output:

```text
.build/EscalierShell.app: replacing existing signature
.build/EscalierShell.app: valid on disk
.build/EscalierShell.app: satisfies its Designated Requirement
```

- Exact signature facts from `codesign -dv --verbose=4`:

```text
Identifier=local.escalier.spike003.shell
Format=app bundle with Mach-O thin (arm64)
CodeDirectory v=20400 size=3894 flags=0x2(adhoc) hashes=115+3 location=embedded
Signature=adhoc
Info.plist entries=11
TeamIdentifier=not set
Sealed Resources version=2 rules=13 files=0
```

- Current status: **ad-hoc signed + strict verification pass**. Not notarized, not Developer ID,
  not Gatekeeper-approved, not launch-tested. Earlier pre-addendum packaging produced a bundle
  without this explicit bundle signature (the executable carried SwiftPM's linker ad-hoc signature
  with `Info.plist=not bound` and `Sealed Resources=none`); that evidence remains in the
  implementation report addendum and is not rewritten.

## Related spike boundary

The owner has separately scoped global keyboard capture and stealth typing tests to
[`../005-global-keyboard-routing/PLAN.md`](../005-global-keyboard-routing/PLAN.md), with an
independently reviewed active-interception adapter and local browser no-bubble oracle. 003
contains only app-menu key equivalents and the explicit `NOT CONNECTED` status placeholder; it
implements no hook and triggers no permission prompt. The 003 audit proves only that the 003 UI
prototype has no such hook. It does not argue that the project can never use one.
