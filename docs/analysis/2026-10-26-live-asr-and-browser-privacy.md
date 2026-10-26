# Escalier — live ASR, browser privacy and configurable conversations

Date: 2026-10-26. Status: research and proposed probes; Spike 001 has four measured small-fixture ASR arms (measurement update in section 7); the native shell/UI and capture/focus spikes have reviewed headless/build/signing slices, while capture/focus/stealth runtime remains NOT RUN. Not an implementation specification or runtime result.

Current authority: [requirements](../requirements.md) and [ADR-0001](../decisions/0001-native-macos-and-omp-rpc.md). The [2026-10-25 report](2026-10-25-feasibility.md) is a historical snapshot.

Research update (2026-10-26): the owner approved a retained, implementation-stage ASR spike that tests both already-installed cached models — [Spike 001](../../spikes/001-transcription/README.md). Synthetic capture/focus and native shell/UI plans now exist at [Spike 004](../../spikes/004-window-capture-focus/PLAN.md) and [Spike 003](../../spikes/003-native-shell-ui/PLAN.md); the Natively/HackerRank claim trace is [Spike 002](../../spikes/002-hackerrank-claims/README.md). The ASR spike has since measured four cached-model arms on the small fixtures (measurement update in section 7); the capture/focus and native shell work have reviewed headless/build/signing slices, not runtime validation; Spike 002 is research complete with no runtime/receiver evidence. This document remains research evidence; no measured capture, focus or stealth result is claimed.

## 1. Decisions and evidence from this discussion

**OWNER-RESOLVED, Fabrizio, 2026-10-26:**

- The cached `parakeet-tdt-0.6b-v3-Q8_0.gguf` is Handy's active, tested multilingual model. The owner's Handy observation remains separate from this probe's independent small-fixture measurements (measurement update in section 7); no independent test of the owner's Handy app or the live interview scenario has run.
- SwiftUI content with AppKit window/application coordination is the primary shell.
- Use the full Natively stealth feature set as a functional baseline; research additional techniques rather than dropping difficult requirements.
- Configure tools and skills per conversation. A permanent no-tools/no-skills policy is not the goal.
- Keep canonical source text/citations outside OMP compaction; keep model selection, completion/cancellation and image fidelity explicit.
- Retain full transcripts, retrieval/search logs and assistance as available, easily deletable conversation results. Remaining storage/deletion details are not decided.
- Start with a browser HackerRank interview as the reference scenario. Firefox is a candidate to investigate.
- Test both already-installed cached ASR artifacts, Parakeet v3 Q8_0 and Nemotron 3.5 streaming Q8_0, in a retained spike. This is a research scope, not a production model choice or measured result.
- Prefer invisibility where it is demonstrably possible and disguise where it is not; record unsupported gaps rather than claiming universal undetectability.
- Retain spikes, tests, plans and reviewed findings in their own directories with reproducible commands and evidence labels.

### Calendar corroboration and invitation access

A matching calendar entry was read directly through a read-only Calendar API command. It corroborated the HackerRank reference scenario and contained no assistance-tool restriction. It also contained no explicit tool-policy permission statement. This is a record of the entry's policy wording, not a new product exclusion or a claim of blanket third-party permission. The private link, event identifier, session description and contact details are intentionally not copied into this repository.

Invitation access to date: **one HEAD request** returned a redirect to HackerRank's `codepair` route. The redirect was not followed. No interview page was loaded, joined, started, submitted or modified. All subsequent browser/platform research used public documentation, not the invitation. The private short link, calendar event ID and contact details are intentionally absent from this repository.

No audio/model/GUI/capture tests ran in this pass. A Swift compiler and `whisper-cli` were found locally; `transcribe-cli` was not found on PATH. The presence of `whisper-cli` does not mean it can load the active Parakeet model merely because both use GGUF-related formats. Later retained-spike work is tracked in [Spike 001](../../spikes/001-transcription/README.md); this paragraph remains the historical record of this research pass.

## 2. Near-live transcription with the existing batch model

### Evidence versus proposal

The pinned [Parakeet engine documentation](https://github.com/handy-computer/transcribe.cpp/blob/8facde6fcd8fb9caa585a5788ab450df6e8ec7db/docs/models/parakeet-tdt-0.6b-v3.md) describes offline ASR with token timestamps, not a cache-aware streaming recognizer. Independent batch calls should not be assumed to reuse encoder state.

Macháček, Dabre and Bojar's [Whisper-Streaming paper](https://aclanthology.org/2023.ijcnlp-demo.3.pdf) describes **LocalAgreement-2**: confirm the common prefix of two consecutive hypotheses for the unconfirmed portion of the audio. The paper explicitly discusses replacing Whisper with another ASR that supplies word timestamps and punctuation. The main agent fetched and checked that text. The reported 3.3-second English latency used Whisper on an NVIDIA A40 and is **not** a Parakeet/M2 Pro prediction.

The agreement policy is transferable in principle; Whisper-specific prompts, buffer limits and alignment heuristics are not automatically valid for Parakeet. Token-to-word timing exposure and short-window stability in the chosen engine need testing. [AlignAtt](https://arxiv.org/abs/2305.11408), [Simul-Whisper](https://arxiv.org/abs/2406.10052) and [SimulStreaming](https://arxiv.org/abs/2506.17077) include attention/alignment machinery that must not simply be transplanted into a TDT/RNNT path without the necessary model signals.

### Three candidate policies

| Policy | Behavior | Main advantage | Main risk |
| --- | --- | --- | --- |
| Endpoint-only | Run ASR after a VAD-detected pause. | Simple final transcript baseline, little repeated work. | No text while someone speaks continuously; endpoint delay adds to decode delay. |
| Rolling overlapping windows | Re-decode recent bounded audio periodically; reconcile overlap. | Bounded window size and regular updates. | Changing left context, duplicated/missing seam words, repeated compute and revision churn. |
| VAD-gated growing window + agreement | Keep utterance start fixed, periodically decode growing audio, show a tentative tail and agreement-confirmed prefix, then reconcile a final decode. | Stable left context plus updates before an utterance ends. | Repeated work grows with utterance length; requires bounded windows, explicit revisions and backlog handling. |

**PROPOSED first batch candidate:** the hybrid. Preserve two independent channels with their own VAD, audio clock, buffer and text revisions. VAD detects speech/silence, not relevant/irrelevant speech or individual remote participants. Acoustic echo remains a capture problem.

Starting probe values, **not approved thresholds or measured optima**: partial updates every 0.5–1 second; short pre-roll before speech onset; roughly 0.5–0.7 seconds of endpoint hangover; a timestamp guard around unstable trailing tokens; bounded 15–20-second windows with overlap at forced cuts. The exact values belong to the experiment. Do not silently rewrite previously used evidence when a final ASR result corrects a partial hypothesis.

For scheduling, allow at most one pending partial job per channel and coalesce stale partial requests. Finalization must not sit behind an unbounded backlog. Whether the engine can actually cancel an in-flight decode is unverified; the host can at least discard stale results.

### Worked compute example

A 20-second uninterrupted utterance decoded at one-second intervals from a fixed start submits approximately `1 + 2 + ... + 20 = 210` seconds of audio across 20 calls. That is **10.5 times the input duration**, not a measured wall-time multiplier. Encoder behavior, caching within a call, timestamp cost and hardware scheduling determine actual compute. Two active channels make queue measurements essential.

Measure separately:

- Word end → tentative display and agreement-confirmed display.
- Speech end → finalized transcript, including VAD hangover.
- Decode time, queue time, real-time lag and two-channel contention.
- ASR delay → retrieval/OMP first useful text; prompt acknowledgement is not a completed answer.
- Final transcript error, partial churn, duplicate/missing seam words, proper names and code-switch behavior.

Endpoint-only is a useful control, not a sufficient assumption for conversation mode. Conversely, batch ASR should not be rejected solely because its label says offline: measure it against the required experience before choosing a replacement.

## 3. Alternative models and runtimes

| Candidate | Documented behavior | Fit and trade-off |
| --- | --- | --- |
| Existing Parakeet v3 Q8_0 GGUF | Offline multilingual ASR; timestamps; existing owner-tested artifact. | Best starting point for zero extra model download and a final-transcript baseline. Near-live behavior needs a host algorithm and measurements. |
| Nemotron 3.5 ASR Streaming multilingual, GGUF path | Cache-aware streaming FastConformer/RNNT; Spanish among supported locales; punctuation and token/word timing documented by the engine. | Strong true-streaming comparison candidate within the same engine family, but a different model download/licence and unmeasured M2 Pro path. |
| Nemotron CoreML/FluidAudio port | Native Apple-Silicon inference path with configurable streaming chunks and published vendor benchmarks. | Alternative runtime, not the only way to use the model. Asset access, variant timing and timestamp interfaces need verification. |
| Apple SpeechAnalyzer / SpeechTranscriber | On-device progressive/volatile and final results; timed output; system-managed assets. | Native Swift candidate. Actual supported locales/assets, bilingual behavior and two-channel resource use must be queried/tested. |
| Parakeet realtime EOU 120M | Genuine streaming/end-of-utterance model, documented as English-only. | An English-only option, not a drop-in answer for Spanish calls. |

Load-bearing sources independently checked by the main agent: the [NVIDIA multilingual streaming card](https://huggingface.co/nvidia/nemotron-3.5-asr-streaming-0.6b), and the pinned [GGUF engine model page](https://github.com/handy-computer/transcribe.cpp/blob/8facde6fcd8fb9caa585a5788ab450df6e8ec7db/docs/models/nemotron-3.5-asr-streaming-0.6b.md). The latter documents a Q8_0 download of about 751 MB, runtime streaming controls and OpenMDW-1.1. Chunk/lookahead settings are not end-to-end display latency. The installed Handy build has not been shown to expose this candidate, and no model was downloaded during this research pass.

Superseding note (2026-10-26): the owner subsequently approved testing both already-installed cached artifacts, Parakeet v3 Q8_0 and Nemotron 3.5 streaming Q8_0, in [Spike 001](../../spikes/001-transcription/README.md). No new model download is part of that approved scope. No inference result, production model choice or leaderboard claim follows.

Additional sources: [FluidAudio Nemotron documentation](https://github.com/FluidInference/FluidAudio/blob/main/Documentation/ASR/NemotronMultilingual.md), [CoreML model card](https://huggingface.co/FluidInference/Nemotron-3.5-ASR-Streaming-Multilingual-0.6b-CoreML), [Apple SpeechAnalyzer](https://developer.apple.com/documentation/speech/speechanalyzer), [SpeechTranscriber results](https://developer.apple.com/documentation/speech/speechtranscriber/result), [AssetInventory](https://developer.apple.com/documentation/speech/assetinventory), [EOU model card](https://huggingface.co/FluidInference/parakeet-realtime-eou-120m-coreml).

**Recommendation, PROPOSED:** measure the existing model first, but keep the same-engine Nemotron streaming path as the leading replacement candidate if the hybrid has unacceptable latency, churn or queue growth. Apple is a useful native comparator. Do not automatically require CoreML or select an English-only streaming model for bilingual use. Published M2/M4/M5 vendor numbers are not measurements of this M2 Pro, and different datasets/decoding settings do not establish an accuracy winner here. Language changes within one sentence remain a separate test from language support on a model card.

Owner decision (2026-10-26), research scope only: both already-installed cached models are approved for retained testing. The recommendation above is not a production model selection.

## 4. Firefox and the browser-interview path

### Public compatibility evidence

The main agent fetched [HackerRank's browser matrix](https://candidatesupport.hackerrank.com/articles/8455316478-browser-recommendations-for-hackerrank-interviews):

| Browser | New Interview Experience | Legacy Interview Experience |
| --- | --- | --- |
| Chrome | Fully supported | Fully supported |
| Edge | Fully supported | Fully supported |
| Firefox | Not supported | Fully supported |
| Safari | Not supported | Partially supported; Zoom audio/video limitation |

The CodePair redirect and calendar description do not identify which experience/session settings are active. The matrix does not establish whether an unsupported browser is blocked or merely degraded. This is a compatibility constraint to investigate, not a removal of the HackerRank requirement.

### Non-Chromium does not imply legacy capture

Mozilla's [Firefox 132 release notes](https://www.firefox.com/en-US/firefox/132.0/releasenotes/) document macOS 15's screen/window sharing selection support. [Mozilla's ScreenCaptureKit rollout issue](https://bugzilla.mozilla.org/show_bug.cgi?id=1915562) and [picker rollout](https://bugzilla.mozilla.org/show_bug.cgi?id=1918648) provide the backend context. The main agent fetched the release notes; exact per-source backend behavior of an installed Firefox/macOS build remains NOT TESTED.

Firefox therefore cannot be selected on the premise that avoiding Chromium automatically avoids ScreenCaptureKit. Mozilla [tab-sharing issues](https://bugzilla.mozilla.org/show_bug.cgi?id=1651145) and [Zoom's browser-support table](https://developers.zoom.us/docs/meeting-sdk/web/browser-support/) also identify source/audio capability differences. Screen-share audio support is separate from Escalier's local system/app-audio capture; Firefox's limitations do not establish that Escalier cannot hear the other side.

A single selected external window and an entire display are different capture surfaces. Do **not** assume a separate overlay overlapping that window is necessarily included in a true single-window stream. Conversely, do not assume it is omitted: test the actual window/auxiliary-surface composition. Whole-display composition is a different, higher-risk case. Escalier's own `SCContentFilter` can scope **its own** capture; it cannot force another process to use the same exclusions.

HackerRank publicly documents [observation mode](https://support.hackerrank.com/articles/1263202297-observation-mode-in-interviews) and [integrity signals](https://support.hackerrank.com/articles/5161582600-interview-integrity-signals). Focus/visibility events and receiver pixels are different oracles. A local synthetic test can establish observed focus and pixels, not the absence of undisclosed server-side flags. No active interview was used as a test.

**Recommendation, PROPOSED:** retain Firefox as a conditional candidate, not the default privacy solution. Start privacy experiments with synthetic pages in available supported browsers and record exact builds/source types. Do not downgrade the browser-interview requirement or claim Firefox compatibility without identifying the relevant product experience.

**Owner direction (2026-10-26):** prefer invisibility where it is demonstrably possible and disguise where it is not, recording gaps instead of claiming universal undetectability. Neither outcome is established here. A synthetic capture/focus plan now exists at [Spike 004](../../spikes/004-window-capture-focus/PLAN.md); it is planned/in progress, not run. No interview participation is authorized.

## 5. Natively stealth parity inventory

Every row below is **reference evidence / NOT IMPLEMENTED in Escalier**, not a PASS. Functional parity is the owner requirement. Unavailable mechanisms remain explicit gaps; they are not silently omitted.

Reference revisions:

- Inspected main revision: `b9287ec2f24bf0ea5250625286f97248052055e9`.
- Released `v2.9.2`: `b439c1f07f6d2d77cbca64fc0533765bd19fe7f7` (tag metadata checked by the main agent).

Coverage includes window helpers, native window/capture/keyboard modules, stealth-state guards, build identity and own-capture/network policy. The identity delta was checked against the release because current main reverted a previously shipped mechanism. This is not certification of every historical release or every README marketing claim.

The source references in the table use this [main-revision root](https://github.com/Natively-AI-assistant/natively-cluely-ai-assistant/tree/b9287ec2f24bf0ea5250625286f97248052055e9); paths identify the inspected files. No implementation code is reproduced.

| ID | Functional baseline | Reference location | Limits / required evidence |
| --- | --- | --- | --- |
| ST-01 | Apply private-window policy to main and lazily created surfaces. | `electron/WindowHelper.ts`, `electron/NotesWindowHelper.ts`, `native-module/src/stealth_window.rs`. | Legacy sharing flags are not a modern capture guarantee; test each surface and capture backend. |
| ST-02 | Keep mode/state consistent across startup, show/restore and activation transitions; reassert policy. | `electron/utils/stealthProtection.ts`, `electron/main.ts`. | Source uses event paths and periodic backstops. Sampling flags alone cannot prove no leaked frame. |
| ST-03 | Cover native/transient app-owned menus, pickers, alerts, selects and tooltips. | `native-module/src/capture_exclusion.rs`, `electron/services/foreignWindowCaptureGuard.ts`. | Repeated sweeps have races and do not cover windows owned by another process. |
| ST-04 | Suppress or defer app notifications and unsafe synchronous prompts in private mode. | `electron/services/stealthPromptGate.ts`, notification call sites in `electron/main.ts` and dictation wiring. | Cannot retroactively hide delivered OS banners or suppress required OS permission UI. |
| ST-05 | No Dock presence; converge activation policy at startup and after transitions. | `electron/utils/macDockPolicy.ts`, `electron/main.ts`, packaging/plist scripts. | Check actual packaged app, switcher and activation state; source comments are not independent measurements. |
| ST-06 | Hide tray/status-item and application menu presence in private mode. | Tray policy in `electron/main.ts`, `electron/utils/trayIcon.ts`. | Does not remove system privacy indicators or other apps' menu-bar items. |
| ST-07 | Nonactivating panels, appropriate level, Spaces/full-screen behavior and cycle/Mission Control handling. | `native-module/src/stealth_window.rs`, panel setup in `electron/WindowHelper.ts`. | Includes a private activation SPI in the reference. Public-first initialization and actual focus behavior need testing; private API adoption remains an explicit design choice. |
| ST-08 | Click-through/pass-through behavior and predictable popover dismissal. | Pointer/catcher policy in `electron/WindowHelper.ts`. | Verify hit testing without unintended actions in the foreground application. |
| ST-09 | Optional typing into the assistant without moving the foreground app's focus. | `electron/services/StealthKeyboardManager.ts`, `native-module/src/keyboard_tap.rs`, `electron/services/ImeDetector.ts`. | Reference uses a global event tap, permission checks, Escape/submit/idle stop and IME handling. Test explicit mode, exit/recovery and Secure Event Input; do not assume arbitrary IME compatibility or record unrelated typing. |
| ST-10 | Neutralized window titles/tooltips and controlled new-window creation. | `electron/utils/windowTitleGuard.ts`, `src/lib/nativeTooltipGuard.mjs`, `src/lib/stealthTooltips.mjs`, `electron/utils/windowOpenPolicy.ts`. | Native tooltips are separate surfaces. Accessibility labels must remain usable; external-browser links have their own visibility. |
| ST-11 | Runtime displayed-name/title/icon disguise profiles. | Runtime identity in `electron/main.ts`, `electron/utils/disguiseAppName.ts`, `electron/utils/disguiseIcon.ts`. | Cosmetic identity changes are not executable/signature/path hiding. Keep identity and pixel visibility as separate results. |
| ST-12 | Build-time executable/helper identity disguise as a distinct feature from runtime aliases. | `scripts/disguise-name.cjs`, packaging/ad-hoc signing; compare released tag with main. | Release v2.9.2 configured aliases; inspected main reverted them to the brand. This is a version delta, not proof the released feature never existed. Exact Escalier identity/signing strategy remains open. |
| ST-13 | Exclude the assistant from its own screenshots and restore without taking focus, including failure paths. | `electron/ScreenshotHelper.ts`, screenshot session in `electron/main.ts`. | Own-capture hygiene does not establish exclusion from another application's stream. |
| ST-14 | Quiet nonessential telemetry/background activity during private mode. | Stealth network policy in `electron/main.ts`, `electron/services/UsageOutbox.ts`, `electron/services/FunnelTelemetry.ts`. | Reference still permits provider/explicit-user traffic and retains some queued/local records. Escalier need not introduce analytics services merely to suppress them. |
| ST-15 | Map other-platform exclusion/activation/input features to macOS outcomes and record outside-control surfaces. | Windows capture/taskbar/focus helpers; `native-module/src/capture_exclusion.rs`; Apple API docs. | Windows-specific APIs are not macOS evidence. TCC, signing/AX/process inventories, OS-owned UI and external cameras are not made invisible by window policy. |

### Build identity: important correction to a simplistic inventory

The main agent fetched both [main's identity policy](https://github.com/Natively-AI-assistant/natively-cluely-ai-assistant/blob/b9287ec2f24bf0ea5250625286f97248052055e9/scripts/disguise-name.cjs) and the [released v2.9.2 policy](https://github.com/Natively-AI-assistant/natively-cluely-ai-assistant/blob/b439c1f07f6d2d77cbca64fc0533765bd19fe7f7/scripts/disguise-name.cjs). They differ: main explicitly documents a revert; the release configures platform-specific executable/helper aliases. Main's native module declarations do not wire its separate process-name SPI file. Thus neither README text nor a dead source file establishes a working mechanism in the inspected build.

For Escalier, separate requested **functional identity privacy** from copying a particular app's identifier or aliases. An owned stable bundle/signing identity is the proposed starting point; whether/how build-time aliases fit local packaging/TCC is an open design issue. Do not claim that a displayed alias hides a process from all native inspection.

### Candidate additions — PROPOSED, not scope reductions

1. Read back window-policy state after lifecycle transitions and compare requested/observed values; still test receiver pixels because state does not prove capture behavior.
2. Use an explicit app-excluding `SCContentFilter` for Escalier's own captures where appropriate, instead of assuming an arbitrary hide delay is sufficient.
3. Prefer in-window controls/notices during private operation to reduce separate-surface races; still account for mandatory OS pickers/prompts.
4. Construct nonactivating AppKit panels in that state from initialization, then measure whether the reference's private activation workaround is needed.
5. Audit window-menu/accessibility labels and provide a reliable local recovery/stop path, without claiming accessibility/process invisibility.
6. Keep privacy support as a versioned per-source capability with a visible local status; fallback behavior for a failed configuration remains an owner decision.

Apple's [sharing-type warning](https://developer.apple.com/documentation/appkit/nswindow/sharingtype-swift.enum/none), [NSPanel](https://developer.apple.com/documentation/appkit/nspanel), [accessory activation policy](https://developer.apple.com/documentation/appkit/nsapplication/activationpolicy-swift.enum/accessory), and [SCContentFilter](https://developer.apple.com/documentation/screencapturekit/sccontentfilter) are platform context. These additions are proposals; there is no claim that public or private APIs solve full-display invisibility on the host.

## 6. OMP: conversation configuration, streaming and storage

### Conversation capability manifest — PROPOSED implementation boundary

Use a per-conversation manifest containing selected model roles, tool names/integrations, skill names/sources and approval policies. Build the RPC process/session from that manifest. The public RPC `new_session` command is not a documented general replacement for all launch-time configuration; start a fresh configured process when necessary. A reusable UI profile/template is possible without mutating global OMP settings.

First-party [skills documentation](https://omp.sh/docs/skills), independently fetched by the main agent, documents `--skills` comma-separated name-glob filtering and `--no-skills`. Empty include lists, hidden skills and disabled slash-command exposure have different semantics; command absence is not proof a skill cannot match or be invoked. Skills are guidance, while executable plugins/extensions/MCP servers introduce a separate trust boundary. A selected skill may ask to use a tool, but cannot substitute for that tool's authorization.

[Process overlays](https://omp.sh/docs/settings) and [CLI flags](https://omp.sh/docs/cli) should express the chosen set without global `/settings`, `/extensions` or config mutations. Profiles isolate credentials as well as settings, so a fresh profile does not automatically reuse existing provider logins. Do not copy credential databases or log secrets to make the configuration work.

**Proposed policy mechanics:** select wanted capabilities, explicitly deny unselected executable capabilities, suppress unselected executable integrations before they load, and set an explicit approval mode rather than inheriting `yolo`. `always-ask` is a candidate conservative mode; it is not a substitute for per-capability policy. In truly headless contexts a required prompt fails unless a supported interactive bridge exists. Do not auto-approve to hide that failure. User-selected tools remain usable subject to their chosen policies and point-of-risk confirmation for consequential actions.

Important audit distinction: [`get_state.dumpTools`](https://omp.sh/docs/rpc) describes advertised tool definitions, not approval mode or a complete executable-code trust audit. Inspect effective configuration/approval policy separately. The [approvals docs](https://omp.sh/docs/approvals) and controlled startup tests are the evidence for policy; do not certify it from the tool-name list alone. Live skills/catalog discovery details over RPC remain to be established for the installed OMP version.

### Image input versus streamed output

The [RPC protocol](https://omp.sh/docs/rpc) defines:

- Host → OMP: a complete image attachment in an `images` array, subject to the serialized command's advertised transport budget.
- OMP → host: a streamed sequence containing incremental `text_delta` events and discrete, complete `image_end` blocks.
- `rpc_chunk`: transport fragmentation/reassembly of a logical output object, not progressive image pixels.

An image can arrive during the response stream without being progressively painted. Provider-specific image generation, image interpretation and displaying an existing/generated diagram are different capabilities. Selected-model support must be explicit; no universal image-generation capability is inferred from the event schema.

### Retained results and easy deletion

FR-15 now resolves that conversation results must remain available and easy to delete. It does not decide all underlying copies. The proposed canonical archive is Escalier-owned and groups transcript, retrieval/search log and assistance under one conversation identity; exact persistence format and save/deletion defaults remain to be designed.

Deletion coverage must distinguish:

- Escalier's results, indexes, thumbnails/screenshots and any copied source snapshots.
- OMP session journals and image blobs, if written.
- Exports/share links or enabled remote memory integrations.
- Provider-side retention, which local file deletion does not erase.

A shared content-addressed blob might be referenced by another conversation. Do not promise that deleting one journal deletes its blobs, and do not run broad shared-store garbage collection as an implicit per-conversation delete. App-owned storage scopes and deduplication reference handling are design questions. Sources: [OMP session format](https://omp.sh/docs/session-format), [sessions](https://omp.sh/docs/sessions), [memory](https://omp.sh/docs/memory).

## 7. Proposed next probes

Probe A is now an implementation-stage retained spike and has produced **four measured cached-model arms on the small fixtures** (measurement update below). Probes B and C remain **NOT RUN**. These are scoped experiments, not an app scaffold or accepted performance thresholds.

**Measurement update (2026-10-26):** after this document's research pass, [Spike 001](../../spikes/001-transcription/README.md) ran four retained arms — Parakeet endpoint, Parakeet hybrid, Nemotron endpoint and Nemotron native-stream — on the two natural clips and two derived assemblies. [Findings](../../spikes/001-transcription/FINDINGS.md) and the [execution record](../../spikes/001-transcription/results/EXECUTION.md) retain normalized WER, arrival timings, per-trial strict JSON and source/model fingerprints; no model winner or acceptance threshold is selected. These are independent small-fixture observations, separate from the owner's Handy observation in section 1 and from any live-call result. Capture, focus and stealth runtime remain NOT RUN.

### Probe A — retained ASR spike (formerly proposed batch feasibility)

Use a project-local pinned compatible engine and the already-cached models. Start with a short non-personal, known-transcript Spanish/English fixture including a brief pause and a longer uninterrupted utterance. Compare endpoint-only against the hybrid and, separately, genuine native streaming; treat native and offline right-context settings as a labelled confound rather than an architecture-isolated comparison. Track first partial/stable/final delay, decode/queue time, correction/seam behavior, backend and memory. Use the same fixture across models; do not transfer another machine's published timing. No live microphone/call/LLM is required.

Historical acquisition gate (superseded 2026-10-26): an installed compatible standalone engine was not found during the 2026-10-25 research pass; obtaining a contained test executable was then an open scope question. The owner subsequently approved the pinned engine build and testing both already-installed cached models in [Spike 001](../../spikes/001-transcription/README.md); no additional model download is approved. The old proposal to download the streaming candidate separately is superseded. The retained spike later ran four small-fixture ASR arms (measurement update above); capture, focus and stealth runtime remain unmeasured.

### Probe B — native panel + synthetic browser share

Use a small retained synthetic AppKit fixture with a private marker panel and an unprotected control, plus a local browser sender/receiver fixture. (The owner's 2026-10-26 direction retains reviewed spikes, tests and findings rather than discarding them as throwaway scratch work.) Compare selected external-window and entire-display sharing, with the panel overlapping and not overlapping the selected window. Record exact browser/OS builds, source type, frame visibility and focus events. Cover a small representative auxiliary surface before expanding the full matrix. Required OS/browser permissions are interactive decisions, not automatically granted by the harness.

This probe must use `computer` for any host UI automation and obtain live task-scoped human confirmation before control. Do not substitute shell/AppleScript input automation. It can establish local capture/focus evidence, not undisclosed HackerRank server-side behavior. No interview participation is needed to test the underlying mechanisms; testing the real session is a separate exact action, not silently authorized by this research plan.

A bounded synthetic harness plan now exists at [Spike 004 — window, focus and capture](../../spikes/004-window-capture-focus/PLAN.md), with a companion native shell/UI prototype plan at [Spike 003](../../spikes/003-native-shell-ui/PLAN.md). Both are planned/in progress, not validated. A build or unit test would not establish receiver pixels, focus behavior or stealth.

### Probe C — OMP launch contract

After its scope is approved, test a controlled non-inference startup with one deliberately included and one excluded fixture skill/tool. Audit config, advertised tool/command state and protocol behavior; do not mutate global settings. Distinguish catalog presence from enforcement. Then separately scope a synthetic image/text turn if needed.

## 8. Current recommendation and unresolved details

Keep the approved native/RPC direction. Do not silently switch ASR models or reduce stealth parity. Proceed from measured evidence: the retained ASR spike measured all four cached-model batch/hybrid and native-stream arms on small fixtures; the capture/focus and native shell work have reviewed headless/build/signing slices, not runtime validation. Firefox is conditional rather than a guaranteed workaround. No spike has produced a measured capture, visibility or focus result; ASR latency and accuracy are measured only on the tiny fixtures.

Remaining decisions include actual latency/accuracy tolerances, screenshot targeting, repeated-shortcut concurrency, exact conversation capability presets, raw-audio/screenshot/OMP-copy retention, deletion UX, private API/identity choices and privacy fallback behavior. No further assistance prohibition has been inferred from the advisor or the calendar. No runtime capability is claimed here.
