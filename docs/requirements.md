# Escalier — requirements baseline

Status: owner-approved requirements recorded; overall design remains in progress.
Created: 2026-10-25. Updated: 2026-10-26.

> Staircase wit, while you're still on the stairs.

## Purpose

Escalier is a personal conversation-support application for retrieving, organizing, and expressing knowledge during pressured or casual conversation. It supports preparation beforehand and grounded recall and generated assistance during online conversations. This is an assistive product purpose, not a claim of clinical efficacy or medical treatment.

The first target is the owner's Mac mini, Apple M2 Pro, 32 GB RAM. macOS-specific APIs, languages, libraries, and existing tools are welcome; cross-platform portability is not a requirement. The intended project is open-source, even though the immediate use is personal.

## Provenance and evidence rules

- **OWNER-RESOLVED**: explicitly requested or approved by Fabrizio in this design conversation. Initial decisions are dated 2026-10-25; the amendments below identify the 2026-10-26 approvals.
- **OWNER-OBSERVED**: a behavior Fabrizio reports having tested; not an independent test by the research agent.
- **PROPOSED**: an agent recommendation requiring review. Proposals do not become requirements merely by appearing here.
- **DOCUMENTED / SOURCE-OBSERVED / LOCALLY-OBSERVED**: technical evidence, attributed in the research report. None implies end-to-end validation.
- **NOT TESTED**: a runtime claim still requiring an explicit test with recorded versions, conditions, and an observable result.

The research report may refine technical feasibility; it must not silently replace owner decisions. A failing feasibility test requires discussing the constraint or alternative with the owner.

Approval provenance for NFR-03: the first assistant research reply, section 2's **OMP permissions** row, proposed restricting inherited coding-agent powers. This is a paraphrase of that assistant suggestion, not a quote from the owner's paste. Fabrizio replied under **OMP permissions**, “I like your suggestion.” On 2026-10-26 he clarified that wanted tools and skills must be configurable per conversation; this controls the current requirement.

Research-process boundary, not an additional owner privacy preference: cloud-enabled product design does not by itself direct this research pass to upload private files or conversation content.

## Owner-resolved product requirements

All entries below: owner Fabrizio; state OWNER-RESOLVED. Initial approvals are dated 2026-10-25. FR-14/15/16, NFR-08/09 and the amendments to NFR-03/05 and OBS-01 are dated 2026-10-26. Stable IDs are identifiers, not priority rankings.

| ID | Requirement |
| --- | --- |
| FR-01 | Start a conversation preparation by selecting files, multiple files, or directories containing the knowledge and context relevant to that conversation. |
| FR-02 | Select OMP-discovered models during conversation configuration. OMP is the agent/LLM backend, integrated over RPC rather than the in-process SDK. Exact model roles and routing remain open. |
| FR-03 | Make microphone/input and computer-audio selection readily available. The capture design must support coexistence with the conversation application, subject to practical validation. |
| FR-04 | Transcribe locally for speed, maintaining two source identities: **me** and **the other side**. Individual identification of multiple remote participants is outside this agreed attribution scope. |
| FR-05 | Show a reference panel containing actual source text, highlighted relevant passages, and reliable source locations. Provide contextual navigation without typing search terms. Finding another candidate must not unexpectedly move the passage currently being read. |
| FR-06 | Show an assistance panel supporting streamed text and images in a continuous, scrollable conversation buffer. Source-backed personal knowledge, suggested wording, and general information must be distinguishable. |
| FR-07 | Provide separate, predictable keyboard shortcuts for finding relevant source material, answering the latest question, formulating the user's recent point, finding a way forward when stuck, and interpreting a deliberately captured screenshot. Exact bindings remain open. |
| FR-08 | Provide a screenshot action for the active window or a selected screen section and pass the image to the assistant. Exact target-selection semantics require refinement. |
| FR-09 | Do not invent the user's experiences, accomplishments, or opinions. Missing personal evidence must not be presented as a personal fact. |
| FR-10 | Support an explicit transition from preparation into live conversation mode, where the conversation stream informs shortcut-triggered assistance and retrieval. |
| FR-11 | Use a minimal, primarily keyboard-driven interface. Shortcut hints should be available without requiring the user to remember every binding; the precise hint presentation remains open. |
| FR-12 | Reuse transcription model artifacts already downloaded through Handy where compatible. Integration with the running Handy application is not required; consider it only if it reduces work and serves the actual use cases. |
| FR-13 | Where feasible, make all transcription models already installed through Handy available for selection, with format/runtime compatibility established rather than assumed. This conditional goal is broader than the single cached candidate identified so far. |
| FR-14 | Keep canonical source text and citations outside OMP's potentially compacted conversation history. |
| FR-15 | Keep conversation results available after the call, including the full transcript, retrieval/search logs and generated assistance, and make saved conversation results easy to delete. Raw-audio/screenshot retention, save defaults and deletion boundaries require refinement. |
| FR-16 | Configure enabled tools and skills per conversation, alongside model selection. Support wanted capabilities rather than permanently stripping all tools/skills; enforce the selected capability set without silently importing unrelated integrations. |
| NFR-01 | Produce a locally buildable macOS `.app` that is readily launchable for personal use. Local build and packaging are acceptable. |
| NFR-02 | Permit conversation content, document/source excerpts, transcripts, and screenshots to be processed through OMP's configured providers, including cloud providers. There is no owner-imposed local-only LLM requirement. |
| NFR-03 | Give each conversation an explicit tool/skill capability configuration. Do not automatically grant all inherited coding-agent powers, and do not impose a blanket no-tools/no-skills policy. Verify enforcement, inherited executable integrations and approval behavior for the selected configuration. |
| NFR-04 | Do not show a Dock icon during the intended unobtrusive operation. Other activation, menu-bar, switcher, and recovery behavior requires design. |
| NFR-05 | Use the complete Natively stealth feature set as the functional implementation baseline and research additional techniques. Map platform-specific mechanisms to macOS equivalents or explicit feasibility gaps; do not silently reduce the requested feature set. Independently implement without copying Natively code, retain HackerRank browser-interview and screen-sharing privacy requirements, and validate bounded claims rather than promise universal undetectability. |
| NFR-06 | Maintain a versioned compatibility matrix for Teams and Zoom, native and browser versions; Google Meet; tab/window/entire-display sharing; LeetCode practice and contests as separate environments; HackerRank modes; and all Escalier surfaces, including auxiliary windows, menus, tooltips, dialogs, notifications, and shortcut hints. Record capture exclusion, process/identity visibility, and applicable assistance rules as separate dimensions, not one stealth result. |
| NFR-07 | Natively and Handy may be studied as implementation/functionality references. Do not copy Natively implementation code into Escalier. The project's intended open-source licence remains to be chosen. |
| NFR-08 | Use SwiftUI content with an AppKit window/application coordinator as the primary macOS shell option, subject to feasibility validation. This is an approved direction, not approval of a complete implementation design. |
| NFR-09 | Begin with a browser-based HackerRank interview as the reference scenario, including stealth/privacy and low-interference interaction. A direct HEAD request observed a CodePair redirect, not the session's settings. Firefox is a candidate to investigate, not a selected or proven privacy solution. |
| PROC-01 | Feed research results and empirical tests into evolving specifications. Research is part of the design work, not an appendix detached from implementation decisions. |
| PROC-02 | Maintain an overall product brief and smaller specifications for preparation/source management, audio/transcription, retrieval, OMP assistance/screenshots, interface/sharing privacy, and `.app` packaging/permissions/recovery. |

## Research-scope amendments — 2026-10-26

These amendments record owner-approved research scope. They add no requirement IDs, renumber nothing, and establish no measured capability, model choice, acceptance threshold or licence.

| Requirement IDs | Amendment |
| --- | --- |
| FR-12, FR-13 | Owner approved testing both already-installed cached artifacts — Parakeet v3 Q8_0 batch and Nemotron 3.5 streaming Q8_0 — in the retained [Spike 001](../spikes/001-transcription/README.md). No inference result or production model choice follows. |
| NFR-05, NFR-09 | Retain the browser HackerRank scenario. Firefox remains a conditional candidate, not a proven privacy solution. Prefer invisibility where it is demonstrably possible and disguise where it is not, recording unsupported gaps rather than claiming universal undetectability. Research uses synthetic pages and does not participate in an interview; no new assistance prohibition is inferred. |
| PROC-01, PROC-02 | Retain spikes, tests, plans and reviewed findings in their own directories with commands, versions and evidence labels. The full application design remains open. Build success, source inspection or a green unit test is not runtime capability. |
| Publication | Public repository approved after privacy and Git-identity review. Do not publish private personal details, invitation/calendar/contact content, work identities, credentials, model weights or absolute cache paths. Small licensed fixtures and selected documented results remain trackable. No licence has been chosen. |

## Owner observations and claims to resolve

| ID | Statement | Treatment |
| --- | --- | --- |
| OBS-01 | Fabrizio reports that the Parakeet model installed through Handy is multilingual and has been tested successfully. | OWNER-OBSERVED; on 2026-10-26 he explicitly confirmed the discovered `parakeet-tdt-0.6b-v3-Q8_0.gguf` is Handy's active model. File metadata was independently inspected; the owner's Handy observation remains separate from the retained small-fixture probe, which measured four cached-model ASR arms ([findings](../spikes/001-transcription/FINDINGS.md), [execution](../spikes/001-transcription/results/EXECUTION.md)) without testing Handy or a live call. |
| OBS-02 | The initial reference event is a browser HackerRank interview; the owner states there is no assistance-tool prohibition. | A read-only calendar check on 2026-10-26 corroborated the HackerRank reference scenario and stated no assistance restriction; no explicit tool-policy permission statement appeared. No blanket product exclusion is inferred. Private link, event ID, session description and contact details are intentionally not copied here. |
| OBS-03 | One read-only HEAD request was made to the supplied short link. | LOCALLY-OBSERVED: HTTP 302 to HackerRank's `codepair` route; redirect not followed. No interview page loaded, joined, started, submitted or modified by this research. |
| Q-TECH-01 | A browser webpage cannot directly call ScreenCaptureKit. | Distinguish the webpage API from the browser's native capture backend. Whether browser-based sharing includes Escalier is NOT TESTED. |
| Q-TECH-02 | A transcription model helps process the speech of interest. | Separate speech detection from content/source filtering. VAD can suppress nonspeech but does not identify which unrelated speech is relevant. Audio-source selection and echo handling need investigation. |
| Q-LEGAL-01 | Algorithms and techniques can be independently implemented without copying code. | Record the no-copying direction, not a blanket legal conclusion. Copyright, licence terms, patents, branding, and jurisdiction are distinct questions. No legal clearance has been established. |

## Proposed design principles — not yet ratified

Owner: agent; date: 2026-10-25; state: PROPOSED.

| ID | Proposal | Reason |
| --- | --- | --- |
| P-01 | Freeze a context snapshot when a shortcut is pressed, including transcript boundary, relevant source versions, optional screenshot, and request ID. | Prevent a response from silently changing its target as later speech arrives. |
| P-02 | Give generated responses a short, immediately useful first section; allow more detail below. | Reduce reading load during a live conversation without removing the full response. |
| P-03 | Preserve the user's scroll position in both panels; expose a deliberate return-to-latest action. | Streaming and retrieval must not take reading control away from the user. |
| P-04 | Make audio capture, screenshot capture, inference, cancellation, pause, and recovery explicit and independently observable. | Hidden failures or ambiguous capture states can undermine confidence. |
| P-05 | Centralize private-surface policy and validate results at the receiver, not only through a local protection flag. | Window flags and application marketing do not prove what another participant sees. |

## Open product decisions

These are questions, not assumed requirements or exclusions. Resolved portions remain labelled for traceability and are not pending approval again.

- Q-01 — RESOLVED initial scenario: browser HackerRank interview. See NFR-09.
- Q-02: What source formats and approximate corpus sizes must the first version handle?
- Q-03: Should shortcut actions immediately replace/cancel older pending work, queue, or run independently?
- Q-04: What defines the latest question or recent personal point, and how can the user correct a wrong selection without typing?
- Q-05: Does screenshot capture mean the frontmost external application's full window, a persistent selected region, or a fresh region choice?
- Q-06: Which languages and code-switching patterns are required, and what runtime latency/accuracy is acceptable?
- Q-07 — PARTLY RESOLVED: retain full transcript, retrieval/search logs and assistance with easy deletion. Still specify save defaults, raw audio/screenshots, source copies, OMP journals/blobs, diagnostic logs and the scope of deletion; local deletion cannot establish cloud-provider erasure.
- Q-08 — PARTLY RESOLVED: start with the browser HackerRank interview. Exact browser/version, share sources, session configuration and observable test evidence remain to be established. Invisible pixels and absence of assessment-side flags are different claims.
- Q-09 — PARTLY RESOLVED: primary shell is SwiftUI + AppKit. Inference runtime, retrieval strategy, model-role mapping, keyboard bindings and licence remain open.
- Q-10: When privacy cannot be established in a configuration, what behavior should Escalier offer? No fallback is chosen yet.
- Q-11: What participant notice/consent, confidentiality, and assessment/workplace permissions apply in the intended environments? The owner's cloud-processing preference does not decide third-party obligations; no new consent workflow is selected here.

## Design status

This file records approved requirements, the primary architecture direction and clearly labelled proposals. It is not an approved complete design, implementation plan or acceptance specification. No runtime capability has been validated by this document. The retained ASR spike has established small-fixture measured inference on four cached-model arms; capture, focus and stealth runtime remain unmeasured.
