# Escalier documentation

> Staircase wit, while you're still on the stairs.

Escalier is a personal, macOS-first conversation-support project. Design is in progress; no application implementation or validated runtime compatibility is claimed.

## Current documents

| Document | Status | Contents |
| --- | --- | --- |
| [Requirements baseline](requirements.md) | Owner decisions recorded; 2026-10-26 research amendments; proposals clearly separated | Product purpose, 27 stable requirement IDs, reported observations, research scope and open product questions. |
| [Live ASR, browser privacy and configurable conversations — 2026-10-26](analysis/2026-10-26-live-asr-and-browser-privacy.md) | Research evidence; Spike 001 measured four small-fixture ASR arms; 003/004/005 headless/build/signing reviewed; runtime NOT RUN | Batch-ASR algorithms/streaming alternatives, Firefox constraints, Natively stealth parity, per-call capabilities and retained/deletable results. |
| [Initial feasibility research — 2026-10-25](analysis/2026-10-25-feasibility.md) | Historical snapshot; later owner decisions and retained spikes supersede then-open items | Natively/Handy findings, cached model metadata, macOS capture limits, OMP RPC, alternatives and proposed tests. |
| [ADR-0001 — native macOS and OMP RPC](decisions/0001-native-macos-and-omp-rpc.md) | Owner-resolved primary direction, subject to feasibility | SwiftUI + AppKit, OMP RPC and boundaries of that approval. |

## Research spikes

Retained spike plans, harnesses and findings live in [spikes/](../spikes/README.md).
Status there distinguishes planned/in-progress work from measured evidence.

| Spike | Current status |
| --- | --- |
| [001 — transcription](../spikes/001-transcription/README.md) | Four cached-model ASR arms measured on small fixtures; broad review and doc fixes recorded |
| [002 — Natively/HackerRank claims](../spikes/002-hackerrank-claims/README.md) | Research complete; no runtime/receiver-pixel evidence |
| [003 — native shell and UI](../spikes/003-native-shell-ui/README.md) | Headless/build/signing slice reviewed; runtime NOT RUN |
| [004 — window, focus and capture](../spikes/004-window-capture-focus/README.md) | Headless/build/signing slice reviewed; runtime matrix NOT RUN |
| [005 — global keyboard routing](../spikes/005-global-keyboard-routing/README.md) | Headless adapter/close/settling fixes reviewed; runtime hook/recipient evidence NOT RUN |

## How to read the evidence

Owner approval, documentation, source inspection, local metadata, and runtime testing are different kinds of evidence. Source comments and reference-project marketing are not Escalier test results. The retained ASR spike has established small-fixture measured inference for four cached-model arms; capture, focus and stealth runtime remain unmeasured. Interactive runtime cases and compatibility-matrix rows remain **NOT TESTED** unless a review record says otherwise.

## Intended specification decomposition

Approved decomposition; detailed specifications not yet written:

1. Preparation and source management.
2. Audio capture and transcription.
3. Grounded retrieval.
4. OMP assistance and screenshots.
5. Keyboard-first interface and sharing privacy.
6. Local `.app` packaging, permissions, and recovery.

Research and test results will feed those specifications. ADR-0001 records the owner-approved primary shell/RPC direction; remaining design choices and acceptance criteria stay open. No full-app implementation plan has been approved. The retained spikes are separately authorized, bounded research harnesses.
