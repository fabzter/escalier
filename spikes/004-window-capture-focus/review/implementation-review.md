# Spike 004 — independent implementation review (SPEC + QUALITY)

Date: 2026-10-26. Task-scoped review of the synthetic window/focus/capture harness.
Inputs read: `spikes/004-window-capture-focus/PLAN.md`, the binding
`spikes/003-native-shell-ui/review/preflight-resolutions.md` (N-02–N-05, N-10–N-14),
`spikes/004-window-capture-focus/review/implementation-report.md`, and the review
package `spikes/001-transcription/.tools/reviews/window-capture-focus.diff`
(range `eb8db06..288b64b`).

**Review basis and working-tree note:** all findings and line references below
judge the committed review package at `288b64b`. After that package was produced,
the working tree gained uncommitted edits to
`review/implementation-report.md`, `README.md`, `FINDINGS.md` and
`tools/build-app.sh` (a signing addendum, 48-file source hash, 78 Node tests and
explicit ad-hoc signing). Those edits are not part of this verdict and have not
been reviewed; they appear to address P3 and add new P5 hash/signing evidence,
while P4 remains in the current report text. They need their own review/commit
before they can close those findings. The accepted coordinator evidence is the
pre-addendum run (75 Node tests) that matches this diff.

The coordinator's independent runs are accepted, not repeated here: Swift 51 pass,
Node 75 pass (41 browser + 34 audit/server), web audit 12 files PASS, native audit
14 files PASS, static validator PASS, and a successful `tools/build-app.sh` rebuild
(reported unsigned/unlaunched; see P3 for the ad-hoc signature distinction). I did
not launch the app, a browser, a server or capture; I
did not grant a permission or drive a GUI. I made no code edits and ran no
subagents. This review file is the only write. I ran read-only checks (`plutil`,
`file`, `shasum`, `codesign -dv`, `sw_vers`) and one focused Node probe for a
concrete evidence-gate doubt; no suite was re-run.

## Verdict

- **Spec compliance: ❌ Issues found.** The requested artifact set is substantially
  present and the runtime boundaries are honest, but the receiver-evidence gate is
  fail-open for missing `bytesReceived`/timestamp, the occlusion classifier can
  interpret treatment absence for a partially occluded cell, and the build/report
  misstate the bundle's signing state. Details below (Important P1–P3).
- **Task quality: Needs fixes.**
- **Runtime: NOT RUN.** No receiver pixels, focus/blur/visibility, click-through,
  occlusion, activation-policy, title-visibility, browser-compatibility, TCC,
  bundle-identity or stealth result exists. A native flag is not receiver evidence;
  a sender preview is not receiver evidence.

## Evidence accepted and independent checks

Accepted from the coordinator/worker report (`review/implementation-report.md`):
51 Swift tests, 75 Node tests, both static audits, the tamper tests, the reported
unlaunched rebuild, and the RED→GREEN evidence. No duplicate suite was run.

Read-only checks I performed against the checked-out artifact:

- `.build/EscalierCaptureFixture.app/Contents/MacOS/EscalierCaptureFixture` is
  `Mach-O 64-bit executable arm64`, 1,038,448 bytes, SHA-256
  `3775c55c00e1ef27788ea85b5e989c5a1ba76c8004082e1e19a53d56be3e2d57` — exactly the
  size/hash in `review/implementation-report.md:31`. The rebuilt artifact is the
  reported binary.
- `plutil -lint` is OK for both `Resources/Info.plist` and the bundled copy;
  `file` matches the report; host `sw_vers` (macOS 27.0.1, build 26A434, arm64),
  Swift 6.4 and Node v20.20.2 match `review/implementation-report.md:20-24`.
- `codesign -dv .build/EscalierCaptureFixture.app` reports `Signature=adhoc`,
  `flags=0x2(adhoc)` and an auto-generated code-signing identifier. It is not
  Developer-ID signed or notarized, but the report's “not signed” wording is
  inaccurate (P3).
- The report's 47-file source scope count matches the enumerated files. Its
  `f7a974…` source-tree hash could not be reproduced with straightforward sorted
  path/content SHA-256 variants (NUL/newline/colon separators, content-only,
  content-hash-list, repo-relative prefixes). The exact recipe (separator, path
  prefix, ordering) is not documented (P5). The exact bundle-hash match above
  means this is a reproducibility issue in the report, not evidence of a stale
  binary.
- Focused probe: `buildReceiverEvidence` from `web/receiver-core.mjs` with
  `framesDecoded=90`, frame dimensions and video dimensions but no `bytesReceived`
  returns `RECEIVER TRANSPORT OBSERVED`. This is the concrete confirmation of P1;
  it was not a suite run.

## Spec compliance detail

Verified present and well aligned:

- Native fixture: plainly labelled control window, two otherwise identical marker
  panels that differ only in role, sharing type and frame origin
  (`Sources/EscalierCaptureFixture/FixtureController.swift:227-254`), lazy
  auxiliary panel (`:299-338`), inert click-through panel, lifecycle controls,
  activation-policy switches, title experiment and requested/observed readback
  (`:587-652`, `Sources/CapturePolicy/Readback.swift:301-364`).
- `sharing-none`/`sharing-readOnly` naming, legacy `.none` caveat, readback of
  sharing/style/level/alpha/shadow/opacity/click-through/visibility/key/main/
  occlusion/frame/collection and explicit `missingWindowRoles`/`policyMismatches`.
- Marker/control separation, lifecycle journal and gaps
  (`Sources/CapturePolicy/Lifecycle.swift`; `Tests/CapturePolicyTests/LifecycleTests.swift`),
  auxiliary pure-policy/native consistency, click-through counters, and no
  real-side-effect click path.
- Browser receiver path: `getDisplayMedia({video:true,audio:false})` in the click
  function (`web/sender.mjs:171-233`), `addTrack` (`:95-120`), receiver video only
  from `pc.ontrack` (`web/receiver.mjs:142-159`), inbound RTP `getStats`
  (`:96-117`, `web/receiver-core.mjs:12-44`), ROI-only crop sampling
  (`web/receiver.mjs:314-380`), positive-control labeling (`:69-94`) and
  sender-preview rejection (`web/receiver-core.mjs:138-169`).
- Local-only operation: server binds `127.0.0.1` (`tools/serve-local.mjs:6,
  84-160, 182-185`), GET/HEAD and path/MIME guards (`:60-111`), no automatic start
  (`:188-199`); sender/receiver signaling is same-origin `BroadcastChannel` with
  empty ICE servers (`web/sender.mjs:96`, `web/receiver.mjs:133`,
  `web/transport-core.mjs:1-19`). No audio path, no `getUserMedia`, no upload,
  no external STUN/TURN/signaling, no raw-frame export; the static audit and
  tamper tests enforce the expected patterns.
- Evidence template and honest limitations: `FINDINGS.md` has the session header,
  evidence object, per-cell NOT RUN matrix, native/readback/focus/lifecycle/
  click-through templates, clean-display protocol, compatibility notes and
  non-transferability boundaries. `README.md` repeats that runtime is NOT RUN.
- Scope discipline: the diff contains no 005 global keyboard hook/CGEvent
  tap/AX hook; the only keyboard equivalent is the in-app Quit menu item
  (`Sources/EscalierCaptureFixture/AppDelegate.swift:30-34`). No STT or external
  network probe is present. The title presets are the plan-allowed, clearly owned
  disguise experiment; no trusted-app impersonation or build-time identity
  implementation is present.

Cannot verify from this static/unit artifact (runtime remains NOT RUN):

- Receiver pixels/frame content, focus/blur/visibility behavior, click-through,
  occlusion, activation-policy behavior, title visibility, Chrome/Firefox
  compatibility, TCC/permission attribution, Dock/Cmd-Tab/process identity.
- Exact source-tree hash recipe.
- Actual interactive behavior of toggling `.nonactivatingPanel` on an existing
  auxiliary panel.

## Strengths

- Clear separation: pure `CapturePolicy` value/classification logic and Node
  pure helpers are independently testable; AppKit window construction and DOM
  wiring stay thin.
- Requested-vs-observed readback is genuinely two-sided: observed sharing, mask,
  level, alpha, shadow, opacity, click-through, visibility, key/main, floating/
  becoming-key, occlusion and collection are read back; mismatches and missing
  roles are explicit instead of silently treated as success.
  `WindowReadback.mismatches(against:)` compares sharing/mask/level/alpha/shadow/
  opacity/click-through/hides/becoming-key/floating/collection/title
  (`Sources/CapturePolicy/Readback.swift:207-266`), and
  `AppReadback.activationPolicyMismatch()` compares requested/observed activation
  policy (`:108-118`). Tests cover a matching policy and explicit mismatch cases
  (`Tests/CapturePolicyTests/ReadbackTests.swift:37-84`).
- The receiver path is the real one: no second preview is called a receiver;
  `ontrack` is the only source of the receiver stream; inbound RTP is required
  before transport success; sender preview is explicitly excluded.
- The evidence language is consistently honest: no stealth/invisibility claim,
  no native-flag-as-receiver-pixel claim, no HackerRank universal claim, no
  transcript/STT/network scope creep, and runtime rows are NOT RUN.
- Static tamper tests cover the important bans (event tap, `NSTask`, microphone
  usage key, bundle identity, protection wording, external URL, STUN/TURN,
  `getUserMedia`, autoplay, preview confusion, missing `ontrack`/`getStats`).
- Build reproducibility is strong: the rebuilt bundle's size and SHA-256 exactly
  match the report; Info.plist and Mach-O checks also match.

## Issues

### Critical

None.

### Important

**P1. Receiver-evidence gate accepts missing `bytesReceived` and timestamp.**
`Sources/CapturePolicy/Evidence.swift:140-150` requires `framesDecoded`, frame
dimensions and video dimensions but never `bytesReceived`; `ReceiverTransportReadback`
does not even carry a timestamp (`:35-58`). The JavaScript path has the same gap:
`web/receiver-core.mjs:118-156` gates on decoded frames/frame dimensions/video
dimensions only, although `extractInboundVideoStats` extracts `timestamp`
(`:31-43`). The focused probe returned `RECEIVER TRANSPORT OBSERVED` with
`bytesReceived` absent. This contradicts the preflight's required inbound
`framesDecoded`/`bytesReceived`/dimensions/timestamps and the artifact's own rules:
`README.md:174` says “a missing stats field remains NO RECEIVER EVIDENCE”;
`FINDINGS.md:118-120` says a row is invalid if transport stats are missing;
`review/implementation-report.md:182-186` narrows the requirement to
framesDecoded/frame dimensions/video dimensions. Why it matters: the green
`RECEIVER TRANSPORT OBSERVED` status is the gate for interpreting marker
presence/absence; a partial stats record must not produce it. Fix: require
`bytesReceived > 0` (and a recorded timestamp where the preflight requires it) in
both the Swift and JS gates, add missing-field tests for both, and update the
report wording if the model intentionally permits partial stats.

**P2. Occlusion classification can interpret treatment absence when only the
treatment is occluded.** `Sources/CapturePolicy/Evidence.swift:124-126` enters
`.occluded` only when `occlusionReason != nil` **and** `controlVisible != true`.
If `occlusionReason` is set and the control is visible while `treatmentVisible ==
false`, evaluation falls through to `:151-155` and reports `.transportObserved`
with “The sharing-none marker absence is one local observation…”. That is an
absence interpretation for a marker whose treatment was occluded, contrary to
`FINDINGS.md:121-122` (“An occluded cell is not an exclusion result”) and the
cell-4 rule at `FINDINGS.md:128`. The existing test only covers both markers
occluded (`Tests/CapturePolicyTests/EvidenceTests.swift:50-59`), so the partial
case is untested. Why it matters: this is exactly the false-exclusion path the
positive-control rule is meant to prevent. Fix: invalidate whenever occlusion is
recorded for the treatment until both markers are positively visible (or split
treatment/control occlusion fields), and add a test for treatment-occluded,
control-visible.

**P3. Bundle signing/identity is misreported (in the diff under review).**
`review/implementation-report.md:33` (at `288b64b`) says “Signing | not signed”;
`:92` repeats “Bundle is NOT signed”; `:100` says “no signature was applied”.
`README.md:189` and `FINDINGS.md:249` (at `288b64b`) say the built app is unsigned,
and `tools/build-app.sh:19` (at `288b64b`) prints “Bundle is NOT signed”. Read-only
`codesign -dv .build/EscalierCaptureFixture.app` reports `Signature=adhoc`,
`flags=0x2(adhoc)` and an auto-generated code-signing identifier. Why it matters:
the preflight asks for executable/Info.plist/bundle identity context, and TCC/
identity attribution is explicitly an untested surface; an ad-hoc signature is a
different identity state from “not signed,” even though it is not Developer-ID
signed or notarized. Fix: describe the artifact as “ad-hoc linker-signed; no
Developer ID signature/notarization; not launched,” record the code-signing
identifier as an identity surface, and correct the README/FINDINGS/build script
messages. The uncommitted signing addendum in the working tree appears to address
this; the addendum itself is outside this verdict and needs review.

### Minor

**P4. Report overclaims the native readback schema (in the diff under review).**
`review/implementation-report.md:124` (at `288b64b`) says “Readback JSON includes
all preflight schema fields.” The native readback does not include OS/build,
browser name/version, permission state, audio-track count, receiver transport,
ROI/focus logs or clean-display protocol; those live in the manual `FINDINGS.md`
evidence template and `EvidenceSchema.requiredManualFields`
(`Sources/CapturePolicy/Readback.swift:366-387`). The capability is present; the
sentence is inaccurate. Fix: say the native readback covers the native
policy/readback fields and the manual evidence template covers the rest. The
uncommitted working-tree report edits may address this; they are not reviewed
here.

**P5. Source-tree fingerprint recipe is not reproducible (in the diff under
review).** The report at `288b64b` claims a specific `f7a974…` SHA-256 over 47
files “sorted path/content” (`:27-28`) but does not document the separator, path
prefix or ordering, and straightforward variants did not reproduce it. The bundle
hash matches exactly, so this is a report reproducibility issue. Fix: record the
exact command/recipe, or provide a script that recomputes the value. The
uncommitted working-tree addendum reports a new 48-file hash and retains the
pre-signing 47-file value as historical; the addendum is outside this verdict.

**P6. Click-through counters are cumulative across modes.** `ClickThroughCounters`
has one `mode` and one `panelHits`/`browserUnderlayHits` pair
(`Sources/CapturePolicy/ClickThrough.swift:20-57`); `setMode` changes the mode but
does not reset or bucket the counters. The click-through oracle asks for separate
intercept and pass-through rows (`FINDINGS.md:171-176`), so the readback alone can
show cumulative rather than per-mode counts. The event journal allows manual
reconstruction, but the structured evidence is ambiguous. Fix: add per-mode
counters or an explicit reset/reset-on-mode-switch, and test both modes.

**P7. Receiver evidence is not cleared on peer-connection failure.** The receiver
clears live transport evidence on track-ended (`web/receiver.mjs:149-155`) and on
sender `bye` (`:231-236`), but `onconnectionstatechange` (`:172-179`) only logs and
updates status. A connection that has already produced frames and then fails can
leave `lastInbound`/`RECEIVER TRANSPORT OBSERVED` visible until the track also
ends. Fix: clear or mark stale on `failed`/`disconnected`/`closed`, or include
`connectionState` and a timestamp-freshness check in the evidence.

**P8. Sender setup failure can leave capture running with the page stop disabled.**
In `web/sender.mjs:226-229`, `openChannel()`/`setupPeerConnection()` run before
the start button is disabled and the stop button enabled. If either throws (for
example no `RTCPeerConnection` support), the promise rejects and the page leaves
the capture live but the stop button disabled. The browser's sharing indicator is
still a stop route, but the page's stop control is not reachable as promised.
Fix: enable stop before signaling setup, wrap setup in try/catch, and stop tracks
on failure.

**P9. Static external-URL guard is bypassable by protocol-relative or concatenated
URLs.** `tools/web-audit.mjs:78-83` and `tools/native-audit.mjs:107-109` check only
absolute schemes; `web/transport-core.mjs:12-19` deliberately builds markers with
`"stun" + ":"`/`"http" + "://"` to avoid self-flagging. A future JS
`new Image().src = "//host/path"` or a concatenated URL would not be caught by
these lines (static HTML `src="//"` is caught elsewhere; network APIs are
separately banned). The audit is a guard, not a proof, but the tamper tests do
not cover this bypass. Fix: add protocol-relative/concatenation detection or
document the audit's limit and add a tamper case.

**P10. Unused imports in audit modules.** `tools/native-audit.mjs:1` and
`tools/web-audit.mjs:1` import `statSync` but never use it. Cosmetic; remove.

**P11. `FINDINGS.md` cell 3 carries a compound control value.** `FINDINGS.md:135`
uses “NOT RUN / same-window control possibly N/A” in a single cell. The matrix
instruction says one row per cell and no missing values silently treated as pass;
split this into a decided value or separate rows when the runtime session runs.

## What remains NOT RUN / outside scope

- All runtime cells: entire display, selected browser window, selected fixture
  window, occlusion, focus/nonactivation, click-through, lifecycle, auxiliary
  surface, audio/privacy. No receiver pixels or focus logs exist.
- TCC/permission attribution, bundle/code-signing identity, Dock/Cmd-Tab/process
  visibility, title visibility and Chrome/Firefox compatibility.
- No 005 keyboard hook, STT, or external network probe was added; this diff does
  not duplicate 005. The title presets are within Spike 004's plan and remain
  clearly owned; build-time identity is not implemented.
- No private home/cache paths, work identities, secrets or model names are in the
  artifact set; the content is explicitly synthetic. No invented product
  exclusion or universal-undetectability claim is present. Runtime stealth is not
  established; a synthetic local observation cannot establish absence of
  undisclosed third-party server-side signals.
