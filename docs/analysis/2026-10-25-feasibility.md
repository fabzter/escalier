# Escalier — feasibility research and decision inputs

Date: 2026-10-25. Status: historical research snapshot; not a runtime test result. Some then-open decisions were resolved on 2026-10-26; the current requirements and ADR-0001 take precedence.

Related baseline: [owner requirements](../requirements.md).

Subsequent owner updates: the cached v3 GGUF is Handy's active model; SwiftUI + AppKit is the primary shell; tools/skills are configurable per conversation; retained/deletable conversation results are required; the first reference scenario is a browser HackerRank interview; both already-installed cached ASR models are approved for retained testing; spikes, tests and findings are retained in their own directories. See [ADR-0001](../decisions/0001-native-macos-and-omp-rpc.md) and [Spike 001](../../spikes/001-transcription/README.md). Statements below about these items being open describe the earlier research state, not the current requirements.

## 1. Scope and evidence

This pass investigated four independent slices: sharing privacy/Natively, local audio/Handy models, OMP RPC, and macOS app-shell choices. Research followed the owner's explicit authorization to study Natively and Handy implementations as references without copying Natively code. Other implementation code was not needed. This report contains functional observations and API names, not reproduced implementation code.

Evidence labels:

- **DOCUMENTED**: fetched first-party documentation. A documented API is not proof that the integrated product works.
- **SOURCE-OBSERVED**: observed in an authorized reference revision. Repository comments describing measurements are claims by that repository's authors, not independent measurements.
- **LOCALLY-OBSERVED**: narrowly inspected local metadata, not runtime capability.
- **OWNER-OBSERVED**: behavior reported by the owner.
- **PROPOSED**: recommendation or contract requiring review.
- **NOT TESTED**: no empirical Escalier result exists.

### Local baseline actually observed

| Item | Observation |
| --- | --- |
| Host OS | macOS 27.0.1, build 26A434, arm64, observed 2026-10-25. |
| Target hardware | Mac mini M2 Pro, 32 GB RAM, supplied by owner; hardware inventory was not independently measured. |
| Project | No implementation or Git repository existed at initial inspection. This work adds documentation only. |
| OMP | `omp/18.12.6`, executable in a user-local bin directory on PATH (exact location omitted); version/help inspected, no RPC process or model prompt started. |
| Handy | Installed app metadata reports `com.pais.handy`, version 0.9.8. Matching source package version is not proof of identical build provenance. |
| App-specific models | The app-specific models directory under the standard user Application Support location exists and is empty (exact user path omitted). |
| Cached model candidate | A Parakeet v3 GGUF snapshot exists in the standard Hugging Face cache; details below. |

No audio was captured, no model invoked, no meeting/assessment entered, no credentials read, no permissions changed, and no application or dependency installed. No model binary contents or checksums were read. Public reference source was fetched to memory; no reference repository was cloned into this project.

## 2. Findings that affect the design

### R-PRIV-01 — Window/entire-screen browser sharing can use native macOS capture

**DOCUMENTED.** A webpage uses browser APIs such as `getDisplayMedia`; that does not prevent the browser's implementation from using ScreenCaptureKit. The [Chrome capture guide](https://developer.chrome.com/docs/extensions/how-to/web-platform/screen-capture) documents the web-facing API and tab/window/screen choices. Separately, [Chromium's maintainer record, comments 26 and 42](https://issues.chromium.org/issues/40219528), describes a ScreenCaptureKit route for window/entire-screen capture, distinguishes tab capture, and later confirms use of the stream API. This historical first-party evidence establishes that route's existence, not the exact active implementation of the owner's current browser build or its tab-capture backend.

**Consequence for NFR-05/06:** browser build, selected share source, and capture configuration must be part of every result. A successful tab-share test does not establish full-display privacy.

### R-PRIV-02 — Natively's inspected exclusion mechanism has a documented macOS limitation

**DOCUMENTED and SOURCE-OBSERVED.** Apple's current [`NSWindow.SharingType.none` documentation](https://developer.apple.com/documentation/appkit/nswindow/sharingtype-swift.enum/none) calls it a legacy constant that macOS no longer uses. The same page says it “can cause content to not be available in certain sharing situations,” but explicitly says not to use it to hide or omit content from capture. This is not a claim that the flag has no effect on every capture path. [Electron's documentation](https://www.electronjs.org/docs/latest/api/browser-window#winsetcontentprotectionenable-macos-windows) explains that its macOS content protection sets this sharing type, and that newer ScreenCaptureKit capture paths can still capture protected windows.

Natively's inspected [native window implementation](https://github.com/Natively-AI-assistant/natively-cluely-ai-assistant/blob/b9287ec2f24bf0ea5250625286f97248052055e9/native-module/src/stealth_window.rs#L160-L225) uses that public sharing flag and itself acknowledges modern capture limitations. Its private activation selector concerns focus/WindowServer activation state; it is not an additional demonstrated screen-capture exclusion mechanism. The main research agent independently fetched the Apple documentation and this reference-source range.

Apple's page points to FairPlay for protected media; this is not evidence that arbitrary assistant UI can be protected using FairPlay.

**Consequence:** Natively's marketing is not an acceptance-test oracle. Reimplementing these mechanisms may reproduce legacy protection and unobtrusive interaction, but does not establish full-display invisibility on this host. This is an unresolved feasibility risk, not removal of the owner's requirement.

### R-PRIV-03 — Natively uses several distinct mechanisms

Natively reference revision: `b9287ec2f24bf0ea5250625286f97248052055e9`.

| Mechanism observed | Functional purpose | Limits and Escalier implication |
| --- | --- | --- |
| Nonactivating panel behavior, key-window handling, global shortcuts | Let the user trigger/read assistance while another application retains focus. | Distinct from pixel exclusion. Prefer public AppKit behavior first; private activation SPI is a compatibility risk, not an approved Escalier dependency. |
| Dock/activation-policy management | Avoid ordinary Dock presence and manage application activation. | Owner approved no Dock icon. This does not make a process invisible or exclude its pixels. |
| Content-protection/sharing flags on each main window | Request exclusion from capture paths that honor those flags. | Modern capture limitation above remains. Flags need testing after window/activation transitions. |
| Enumeration and repeated protection of auxiliary AppKit windows | Cover menus, tooltips, native dialogs and other surfaces that are not the main Electron window. | Periodic sweeps can race the first captured frame. Flag reapplication is not atomic protection. |
| Process/app-name disguise | Change displayed identity. | Separate from capture and focus; not proof of hiding from OS-level inventory. Exact disguise behavior has not been selected for Escalier. |

Source anchors: [window policy](https://github.com/Natively-AI-assistant/natively-cluely-ai-assistant/blob/b9287ec2f24bf0ea5250625286f97248052055e9/electron/WindowHelper.ts#L298-L333), [auxiliary surfaces](https://github.com/Natively-AI-assistant/natively-cluely-ai-assistant/blob/b9287ec2f24bf0ea5250625286f97248052055e9/native-module/src/capture_exclusion.rs#L1-L24), [sweep scheduling](https://github.com/Natively-AI-assistant/natively-cluely-ai-assistant/blob/b9287ec2f24bf0ea5250625286f97248052055e9/electron/services/foreignWindowCaptureGuard.ts#L39-L99), [identity changes](https://github.com/Natively-AI-assistant/natively-cluely-ai-assistant/blob/b9287ec2f24bf0ea5250625286f97248052055e9/electron/main.ts#L9977-L10003).

**Consequence:** maintain separate focus, application identity, private-surface lifecycle, and capture-visibility contracts. Do not implement a single boolean called undetectable and treat it as evidence.

### R-PRIV-04 — HackerRank is not one environment

**DOCUMENTED.** [HackerRank Proctor Mode](https://support.hackerrank.com/articles/5663779659-proctor-mode) documents tab/fullscreen checks, screen sharing, and screenshot-based monitoring. [Desktop App Mode](https://support.hackerrank.com/articles/5973590014-hackerrank-desktop-app-mode) adds native restrictions and monitoring of other applications. Ordinary browser practice/interview environments and these modes cannot share one unqualified compatibility claim.

[LeetCode's official contest rule post](https://leetcode.com/discuss/post/951105/new-contest-rule-effective-from-december-2020/) prohibits code-generation tools/external assistance for contest problem solving. This does not establish the rules for ordinary practice or every employer-hosted interview. Assessment permission and technical visibility are distinct.

**Open owner question:** which HackerRank modes are actual targets? The owner approved bounded validation in his own environments; no modes are silently deleted from the requirements here. This read-only research pass conducted no assessment test. A specific live third-party assessment/contest experiment needs a defined test plan, point-of-risk confirmation, and applicable authorization; general product approval does not identify an exact assessment to enter. A receiver-side recording can establish tested pixel visibility, not absence of undisclosed server-side flags.

### R-ASR-01 — A cached multilingual v3 artifact offers a candidate explanation for the v2 mismatch

**LOCALLY-OBSERVED, independently metadata-checked by the main agent.**

- Repository: `handy-computer/parakeet-tdt-0.6b-v3-gguf`.
- Snapshot: `85ac09ea12fc4b1112fa76810059364bc6adc9de`.
- File: `parakeet-tdt-0.6b-v3-Q8_0.gguf`.
- Size: 739,508,576 bytes, approximately 705.25 MiB.
- Location: the standard user Hugging Face cache, repository snapshot `85ac09ea12fc4b1112fa76810059364bc6adc9de` (exact cache path omitted).
- The snapshot entry is a symlink to an existing cache blob. Binary identity/integrity and whether Handy currently selects this exact artifact were not verified.

Its pinned [model card](https://huggingface.co/handy-computer/parakeet-tdt-0.6b-v3-gguf/blob/85ac09ea12fc4b1112fa76810059364bc6adc9de/README.md) lists 25 languages including Spanish. This is consistent with the owner's successful multilingual test. The canonical v2 English card was not a sufficient basis for characterizing the installed model.

Handy's [model resolution](https://github.com/cjpais/Handy/blob/73c095857bc4eadff097f64767c40ad129cc372d/src-tauri/src/managers/model.rs#L2305-L2343) prefers its shared Hugging Face cache before the app-specific directory. Therefore an empty app-specific directory does not imply no installed model.

Inventory scope was narrow: known Handy Parakeet v2/v3 cache prefixes under the default cache and known platform cache roots. Custom cache environment overrides, other model families, and the portable legacy cache were not inventoried. Supporting every installed Handy model remains broader than this single verified candidate.

### R-ASR-02 — Model family, file format, and runtime are separate decisions

**SOURCE-OBSERVED and DOCUMENTED.** At Handy revision `73c095857bc4eadff097f64767c40ad129cc372d`, the [macOS dependency configuration](https://github.com/cjpais/Handy/blob/73c095857bc4eadff097f64767c40ad129cc372d/src-tauri/Cargo.toml#L79-L150) uses `transcribe-cpp` and enables Metal. The cached model is a transcribe.cpp-compatible GGUF. A [FluidAudio CoreML model](https://github.com/FluidInference/FluidAudio/blob/1b0ed50d686873128a4129b3510ce3914c849bab/Documentation/ASR/ManualModelLoading.md#L5-L20) is a different collection of assets and cannot be assumed to load this GGUF directly.

**PROPOSED first candidate:** evaluate a GGUF/transcribe.cpp-compatible runtime against the existing cache before downloading or converting another model. This respects FR-12 without depending on the Handy application. Direct cache reuse must tolerate a missing/evicted artifact and keep cache ownership separate from Escalier session ownership; exact recovery behavior is open.

**NOT TESTED:** successful model loading in Escalier, actual CPU/Metal backend, M2 Pro speed, peak memory, simultaneous-channel throughput, Mexican Spanish accuracy, or bilingual code-switching. A Metal build feature is not proof of Metal being used, and a CPU-oriented model description is not proof that this installed runtime cannot use Metal. No M4 benchmark is presented as an M2 Pro estimate.

Model-card licence is CC-BY-4.0; runtime/dependency licences and attribution obligations must be checked for the versions selected for distribution.

### R-ASR-03 — This cached model is batch ASR, not native streaming ASR

**DOCUMENTED.** The pinned [model card](https://huggingface.co/handy-computer/parakeet-tdt-0.6b-v3-gguf/blob/85ac09ea12fc4b1112fa76810059364bc6adc9de/README.md) and [engine documentation](https://github.com/handy-computer/transcribe.cpp/blob/8facde6fcd8fb9caa585a5788ab450df6e8ec7db/docs/models/parakeet-tdt-0.6b-v3.md#L1-L40) describe 16 kHz mono input, optional token timestamps, and no streaming support. Those documents were independently fetched by the main agent.

**Consequence for FR-04/10:** near-live behavior would require endpointed utterances or bounded overlapping audio windows around a batch recognizer. Endpoint delay, inference delay, duplicate-text reconciliation, short-utterance accuracy, and two-channel scheduling must be measured. Do not relabel batch ASR as native streaming. A distinct realtime/EOU model would be an alternative, not the same downloaded artifact.

### R-AUDIO-01 — Separate source channels are supported by documented macOS APIs

**DOCUMENTED, integration NOT TESTED.** [ScreenCaptureKit's macOS guide](https://developer.apple.com/documentation/screencapturekit/capturing-screen-content-in-macos) describes audio capture with distinct system-audio and microphone outputs. [Core Audio process taps](https://developer.apple.com/documentation/coreaudio/capturing-system-audio-with-core-audio-taps) provide another candidate for selected-process/group output capture, alongside independent microphone capture.

**PROPOSED:** compare a ScreenCaptureKit-based capture path against a process-tap plus microphone path on the owner's actual meeting applications. Source selection, not ASR, should limit unrelated application audio. Browser process grouping may still include more than the intended call; per-process is not automatically per-tab isolation.

VAD detects speech/silence, not relevance. Unrelated speech is still speech. Remote playback can also enter the physical microphone when using speakers; source labels alone cannot remove that echo. Capture alongside meeting apps, route changes, Bluetooth format changes, sample-rate conversion, timestamp continuity, and permission revocation remain NOT TESTED. Headphones are a proposed test condition, not a new hardware requirement.

### R-OMP-01 — RPC fits, but request acknowledgement is not answer completion

**DOCUMENTED.** [OMP RPC](https://omp.sh/docs/rpc) supports model discovery/selection, image input/output event shapes, host tools/URIs, streaming and cancellation. `prompt` acknowledgement means accepted/scheduled. Events can arrive before that acknowledgement. Terminal completion is a separate lifecycle event; abort needs its acknowledgement and the run's terminal event.

**PROPOSED:** keep an Escalier request/generation ID and context-snapshot ID, with one primary active run per process until concurrency policy is agreed. A stale stream must not overwrite the response for a newer action. OMP lifecycle events are not all individually tagged with the initiating prompt ID, so host-side generation tracking matters.

### R-OMP-02 — Screenshots face a real transport budget

**DOCUMENTED, installed protocol NOT TESTED.** Live RPC docs advertise a current 1 MiB `maxFrameBytes` transport budget and say inbound JSONL commands should stay below it. Inbound commands remain unchunked even when v2 is negotiated; v2 chunks large output, not large input. Whether the installed build enforces that exact inbound ceiling is unverified. Conservatively respecting the advertised budget leaves less than roughly 0.75 MiB for a raw single image before base64, prompt and JSON overhead.

**Consequence for FR-08:** size/check the serialized command against the actual `ready` budget; crop/compress/rescale while testing text legibility. Do not assume that a high-resolution full-window screenshot fits or that v2 removes the input limit. A separate provider-file/upload path, if needed, must be verified rather than inferred from an optional schema field. Image-generation capability is provider/model-dependent; the presence of an image event type does not guarantee every selected model generates images.

### R-OMP-03 — Reusing auth must not silently import the whole coding environment

**DOCUMENTED.** [OMP tools](https://omp.sh/docs/tools), [MCP](https://omp.sh/docs/mcp), [CLI](https://omp.sh/docs/cli), and [settings](https://omp.sh/docs/settings) describe built-ins, plugins/extensions/custom tools, inherited configuration, and discovered MCP servers. `--no-tools` means no built-ins; it is not by itself proof of a host-only capability boundary. The documented default approval mode is `yolo`, which automatically allows ordinary read/write/executable tiers. [Approvals documentation](https://omp.sh/docs/approvals) says a required prompt fails when no interactive approval UI is attached; do not assume an arbitrary headless/RPC launch can obtain approval or bypass a provider safety check.

The main agent independently fetched the tool and approval documentation. Approvals are documented as not sandboxing an allowed command; RPC itself is a transport/process boundary, not a demonstrated OS security sandbox. Extensions run as the user's process identity.

**PROPOSED:** app-owned working directory, explicit process configuration and approval/deny policies rather than inherited defaults, no ambient executable integrations, a controlled profile or deliberately audited auth-reuse strategy, and only app-approved tools. A loaded-tool audit is necessary but cannot undo executable code already run during configuration/plugin discovery. Prevent unwanted loading as well as rejecting unwanted exposed tools. Preserve the option of curated app skills without blindly importing all developer skills. An exact safe launch configuration and any required host approval-UI bridge need installed-version verification; do not auto-approve merely to avoid a headless error.

A dedicated OMP profile isolates configuration but also credentials; do not promise that it automatically inherits current provider logins. Model selection should use `get_available_models` and `set_model`, with explicit image-capability metadata; ambiguous capability stays unknown rather than guessed from a model name.

### R-OMP-04 — Escalier must own canonical evidence and persistence decisions

**DOCUMENTED plus PROPOSED application boundary.** OMP [compaction](https://omp.sh/docs/compaction) can replace exact historical context with summaries. Its stored history is not the same as its current model context. Host URI immutability is not documented as a guarantee against compaction or a guarantee of provenance.

**PROPOSED:** keep exact normalized source text and locators in Escalier-owned snapshots, independent from OMP summaries. Supply exact relevant excerpts for each action. Expose only bounded, selected-source search/read callbacks if needed; neither arbitrary filesystem access nor writable source URIs are required for the proposed boundary. The host must enforce source membership and cancellation.

`--no-session` suppresses normal OMP session persistence, but does not establish provider-side retention, stderr-log retention, or Escalier's own history behavior. The owner has not chosen retention defaults. Choosing cloud processing does not settle storage policy.

### R-PKG-01 — A `.app` can use installed OMP without choosing a Bun UI

**DOCUMENTED and LOCALLY-OBSERVED.** RPC is language-neutral and subprocess-based. The installed command path is outside the system default PATH. Finder-launched apps must resolve OMP explicitly and validate version/protocol rather than assume an interactive shell environment. Live documentation may differ from installed `18.12.6`; no handshake was run.

**PROPOSED starting dependency model:** use the existing installed OMP, with an explicit executable locator and startup compatibility check. Bundling OMP into Escalier, its licensing/update obligations, and a self-contained distribution contract are not established. This is a proposal, not a new owner requirement to install anything.

## 3. App-shell approaches — comparison, not a decision

Owner decision status: OPEN. Recommendation owner: agent; date: 2026-10-25; state: PROPOSED.

Decision drivers for this project: direct macOS integration, unobtrusive window/focus behavior, verified privacy rather than marketing, keyboard reliability, readable rich streaming output, stable source/response scrolling, straightforward local `.app` delivery, and contained native-runtime/process complexity. No numerical weights or performance thresholds have been approved.

| Approach | Its real advantage here | Concrete cost/risk |
| --- | --- | --- |
| SwiftUI content + AppKit window/application coordinator | Direct access to the exact platform being targeted; OMP RPC does not constrain the UI language. | Custom panel/activation/global-shortcut lifecycle and rich-text streaming work; native UI does not solve capture exclusion. Images need no web renderer, but broad Markdown/diagram rendering may benefit from a WKWebView. |
| Tauri web UI + Rust/native integration | Web rendering without bundling Electron's Chromium runtime; potentially convenient fit with a Rust GGUF binding. | Web/host/native boundaries, capability configuration, and platform-specific helper/FFI packaging. A separate helper is an option, not a proven necessity. |
| Electron web UI + native integration | Mature web rendering and documented global-shortcut/window APIs; closest structural resemblance to Natively. | Bundled Chromium/Node, native audio/window bridge, larger packaging/security surface. Size, RAM and startup cost have not been measured for Escalier. |

Sources: Apple [NSPanel](https://developer.apple.com/documentation/appkit/nspanel), [activation policy](https://developer.apple.com/documentation/appkit/nsapplication/setactivationpolicy(_:)), [Markdown attributed strings](https://developer.apple.com/documentation/foundation/instantiating-attributed-strings-with-markdown-syntax), [WKWebView](https://developer.apple.com/documentation/webkit/wkwebview); Tauri [sidecars](https://v2.tauri.app/develop/sidecar/), [global shortcuts](https://v2.tauri.app/plugin/global-shortcut/), [macOS bundles](https://v2.tauri.app/distribute/macos-application-bundle/); Electron [global shortcuts](https://www.electronjs.org/docs/latest/api/global-shortcut), [code signing](https://www.electronjs.org/docs/latest/tutorial/code-signing).

**Recommendation for discussion:** lead with SwiftUI + AppKit as the native-first candidate, not a settled stack. First test the shared macOS privacy/focus assumptions in a tiny native feasibility probe rather than building three full prototypes. Then evaluate the actual text/image rendering corpus; add a bounded web-rendered view or reconsider the shell if that materially reduces work. The privacy probe cannot establish that every shell will behave identically; the final chosen bundle must still pass the matrix.

Local buildability is different from frictionless downloaded distribution. A stable bundle ID/signing approach and final-bundle permissions need testing across rebuilds. No Developer ID subscription or notarization requirement has been imposed. Exact local signing and TCC behavior remain open.

## 4. Cross-slice contracts proposed for design

These are candidate boundaries, not committed schemas or implementation instructions.

| ID | Producer → consumer | Proposed boundary |
| --- | --- | --- |
| C-01 | Capture → transcription | Timestamped, separate `me`/`other` audio segments with device/format identity and explicit gap/error state; normalize per-track, never silently merge channels. |
| C-02 | Transcription → context | Ordered segments with channel, time interval, text revision and partial/final status. Batch ASR may initially provide only final utterance segments. Source attribution is not individual speaker diarization. |
| C-03 | Shortcut → retrieval/assistant | Immutable action/context snapshot: action type, transcript boundary/revision, selected-source revisions, request/generation ID, and configured model role with known/unknown image capability. A screenshot carries original target/region, resulting pixel dimensions and encoding, byte size, crop/scale transform, and an explicit fidelity/unsupported state. Budget-exceeding and no-image-model behavior remain decisions. |
| C-04 | Retrieval → reference panel | Verbatim excerpt, source snapshot ID and format-appropriate locator (text lines, PDF page/region, etc.), highlight range, and explicit no-match/error. Never replace it with generated text. |
| C-05 | OMP adapter → assistance panel | Incremental text and discrete image blocks plus acceptance, running, cancel-requested, terminal completion and failure events. Host generation association is conditional on the proposed one-active-run-per-process policy, not a wire-provided prompt ID. Track process/run epoch and wait for abort acknowledgement plus terminal completion before reassignment. Independent concurrent actions need a separately specified mapping/isolation strategy. Preserve reading position independently of new content. |
| C-06 | UI coordinator → every surface | Explicit surface registration/lifecycle, activation/focus policy and requested privacy state. Tested capture capability is a separate versioned fact, not inferred from a flag. |
| C-07 | Generated content → trust presentation | Distinguish source-backed personal material with source snapshot IDs/locators, suggested wording, general information, and missing-personal-evidence/uncertainty. Citation validity and whether cited text actually supports a claim are separate checks. Label authority, validation and abstention behavior remain to be designed; labels alone do not prevent hallucinations. |
| C-08 | Session lifecycle → persistence | Explicitly distinguish live buffers/source snapshots, Escalier-owned durable history, OMP session journals, screenshots and diagnostic logs. No retention default is selected; ephemeral and retained options must be discussed under Q-07. A `--no-session` switch is not a global no-storage guarantee. |

A source changing or disappearing during a call, partial transcripts changing the latest-question interpretation, overlapping local/remote speech, and repeated shortcuts are necessary design cases. Policies for these cases remain open; the context snapshot proposal makes them explicit rather than silently choosing behavior.

## 5. Proposed feasibility probes — none executed

The owner approved testing the audio approach and bounded validation in his sharing/HackerRank environments. None has run in this read-only research pass. Before implementing a probe, present its exact scope; before consequential actions, obtain the required point-of-risk confirmation and applicable authorization. Use non-personal fixtures and controlled meetings first. Any particular third-party assessment/contest or disclosure of private material needs explicit scope rather than being inferred from general interest in testing.

2026-10-26 update: T-01 now has a retained implementation harness with both already-installed cached models approved for testing; no measured inference result exists yet. T-01's earlier per-model boundary is superseded by that research scope. T-04 and related window/focus work have a synthetic plan at [Spike 004](../../spikes/004-window-capture-focus/PLAN.md), and shell/UI work has a prototype plan at [Spike 003](../../spikes/003-native-shell-ui/PLAN.md); both are planned/in progress, not run. Every runtime row remains **NOT TESTED**.

| ID | Probe | Observable evidence | Decision informed |
| --- | --- | --- | --- |
| T-01 | Load the cached v3 GGUF and transcribe short known English/Spanish fixtures; no download. | Exact artifact/runtime/backend, cold/warm load, endpoint-to-final latency, output versus known text, peak memory, and explicit failures. | Whether cached batch ASR is a viable first runtime. |
| T-02 | Capture synthetic local and remote phrases separately alongside the target meeting app; repeat with speakers/headphones. | Timestamped separate source tracks, echo/duplicate behavior, missing segments, actual device formats and coexistence. | Capture API and channel/echo strategy. |
| T-03 | Switch the chosen input/output once during a controlled call and revoke a permission in an authorized test. | Detected transition, bounded gap/recovery or explicit failure; no silent continued-success state. | Device UI and recovery requirements. |
| T-04 | Display synthetic distinctive text/image markers in a minimal panel and each auxiliary surface; exercise show/hide and focus transitions while sharing. | Receiver-side recording inspected for markers and transient leakage; exact application/browser/share-mode tuple. | Whether required privacy configurations are feasible. |
| T-05 | Trigger every agreed action from another application while streaming deterministic fixture responses. | Action exactly once, shortcut conflicts, frontmost app/key destination, source and response scroll position. | Shortcut/window/renderer design. |
| T-06 | Start controlled OMP RPC without inference, inspect `ready`, model discovery and allowed tool surface; then separately approve a synthetic text/image turn. | Installed-version support; loaded integrations; event-before-ack; abort/terminal in both orders; stale-generation rejection; second-prompt policy; image capability, transport budget, resulting crop/scale metadata and legibility. | Safe OMP configuration, run identity and image/model contracts. |
| T-07 | Launch the final locally built `.app` through Finder; rebuild/relaunch with the selected signing approach. | OMP resolution without shell PATH, helper discovery, signing validation, permission persistence/denial recovery. | Local distribution and startup contract. |

Pass thresholds, fixture corpus, runtime duration, and required versus exploratory matrix rows must be agreed before results become acceptance claims. These tests do not validate clinical outcomes or undisclosed assessment-side detection.

## 6. Compatibility-matrix schema and initial rows

All rows currently **NOT TESTED**. An empty or unknown result is not PASS. Initial target OS is the actual host, macOS 27.0.1 build 26A434; testing historical macOS releases is not an owner requirement.

Record for every run: date, exact OS build, Escalier build/revision/signing identity, capture client and version, desktop/browser form, browser build, account/assessment mode when applicable, selected capture source, exposed capture settings, output/input devices, focus state, surfaces exercised, receiver/capture oracle, evidence location, result and limits of the claim. Record screen-capture visibility, process/identity visibility, and applicable assistance rules independently. Avoid recording sensitive participant data in test artifacts.

| Environment | Required distinctions to enumerate | Test status |
| --- | --- | --- |
| Google Meet | Exact browser; tab/window/entire-display sources supported by that browser. | NOT TESTED |
| Teams native | Exact client; window/display; native macOS sharing toggle where present. | NOT TESTED |
| Teams browser | Exact browser/build; available share sources. | NOT TESTED |
| Zoom native | Exact client; window/display; installed capture modes including filtering choices where exposed. | NOT TESTED |
| Zoom browser | Exact browser/build; supported sources independent of native Zoom settings. | NOT TESTED |
| HackerRank browser practice/interview/test | Exact product/test configuration; focus/screen-sharing/proctor features; observable authorized sandbox evidence. | NOT TESTED; target mode needs owner clarification |
| HackerRank Proctor/Desktop modes | Native and browser restrictions, permissions/accommodations, and different observability from receiver-only recording. | NOT TESTED; not assumed equivalent to browser practice |
| LeetCode practice | Practice configuration and capture behavior, without assuming contest policy applies. | NOT TESTED |
| LeetCode contests | Separate contest rules/accommodations and test scope; screen-capture behavior does not establish permission. | NOT TESTED; specific experiment and authorization remain open |

Per row, exercise the main/reference/assistance panels, shortcut hints, settings/device/model controls, menus, popovers, tooltips, file pickers, alerts and any notifications that the eventual design can create. An unsupported surface/path and an observed leak must remain visible in the record.

Evidence quality notes: Zoom's official [advanced sharing settings](https://support.zoom.com/hc/en/article?id=zm_kb&sysparm_article=KB0063824) could not be fetched beyond a loading shell; indexed official text and Natively claims identify settings to check, not confirmed installed options. Apple Developer Forums material behind a verification page was only corroborative search evidence and is not needed for the stronger fetched AppKit finding. Teams [sharing documentation](https://support.microsoft.com/en-us/teams/meetings/present-content-in-microsoft-teams-meetings) and Meet [presentation documentation](https://support.google.com/meet/answer/9308856?hl=en&co=GENIE.Platform%3DDesktop) establish source-choice distinctions, not Escalier privacy results.

## 7. Outstanding decisions and next discussion

- Q-R-01: Which HackerRank environment is actually required: ordinary browser practice/interview/test, browser Proctor Mode, Desktop App Mode, or several? This affects feasibility before choosing the shell.
- Q-R-02: What should happen when a required capture configuration exposes the overlay? Warn, hide, change sharing scope, or another workflow are alternatives, not decisions made by this research.
- Q-R-03: What source formats/corpus sizes, language/code-switching patterns and representative call scenario should drive usability and latency criteria?
- Q-R-04: Which proposed context, retrieval, turn/cancellation and retention contracts should become requirements?
- Q-R-05: Should the native-first shell and cached-GGUF runtime candidates be investigated first, or should the owner prefer another trade-off?
- Q-R-06: What response provenance/label validation, image-fidelity fallback, approved assessment-test protocol and participant notice/confidentiality constraints should be adopted? These do not reopen the owner's accepted cloud-processing preference.

Research results narrow the choices but do not settle these questions. No ADR, implementation plan, application scaffold or release artifact is approved by this report.

## 8. Draft review and triage

Three read-only reviewers examined decision provenance/logic, contract coherence, and primary-source facts. Findings below are grouped; a review does not ratify product decisions.

| Finding | Triage | Action/status |
| --- | --- | --- |
| Cloud permission omitted explicit document excerpts; conditional all-Handy-model selection was not recorded. | **FIX** | Baseline now names source excerpts and restores conditional FR-13. Research-data handling is separated from the owner's preference. |
| Assessment-testing wording looked like a new blanket exclusion. | **FIX / DECIDE** | Corrected to preserve the owner's bounded testing approval; exact environments, experiments and applicable authorization remain open. |
| Process visibility, rules and capture visibility could collapse into one result; LeetCode practice/contests were combined. | **FIX** | Dimensions recorded separately; matrix rows split. |
| Claim that NFR-03 had no traceable approval. | **PARTLY WRONG / FIX TRACEABILITY** | The preceding assistant suggestion and owner's approval exist in the conversation. Added the approved wording to the baseline; no new permission decision inferred. |
| Cached v3 candidate was described too conclusively in its heading; size conversion was imprecise. | **FIX** | Candidate explanation only; current Handy selection remains unknown; approximately 705.25 MiB. |
| Generated provenance, screenshot fidelity, discrete image events, run/abort identity, and retention boundary needed clearer proposed contracts. | **FIX / DECIDE** | C-03/05/07/08 and T-06 refined; label authority, concurrency, fallback and retention are still open. |
| Approval default/headless behavior and transport-budget wording needed precision. | **FIX** | Added documented `yolo` default and required-UI caveat; inbound budget is conservative guidance, with installed enforcement unverified. |
| A supporting scout suggested defaulting to `--no-session`. | **NOT ADOPTED** | Report and baseline choose no retention default. Scout suggestions are not owner decisions. |
| Participant notice/confidentiality/assessment obligations were implicit. | **DECIDE** | Added baseline Q-11 and Q-R-06; no jurisdiction-specific rule or new workflow invented. |

Runtime tests remain **NOT TESTED**. The major fetched API/model claims survived factual review; that does not validate an application, current browser backend, active Handy model, clinical benefit, or assessment-side non-detection.
