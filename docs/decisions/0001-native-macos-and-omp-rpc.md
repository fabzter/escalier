# ADR-0001 — Native macOS shell and OMP RPC

Date: 2026-10-26.
Decision owner: Fabrizio.
State: **OWNER-RESOLVED primary direction, subject to feasibility validation**.

## Context

Escalier deliberately targets the owner's macOS machine. Native window/focus behavior, local audio capture, keyboard-first operation and a locally buildable `.app` matter more than portability. OMP already supplies agent sessions, providers and streaming; embedding its TypeScript SDK is not required to use those capabilities.

The [initial research](../analysis/2026-10-25-feasibility.md) compared SwiftUI/AppKit, Tauri and Electron. These are alternatives, not equal implementation commitments.

## Decision and provenance

- **OMP over RPC**: owner selected RPC in the first follow-up on 2026-10-25 and reconfirmed it on 2026-10-26.
- **SwiftUI content with an AppKit window/application coordinator**: owner selected this as the main option on 2026-10-26: “let's take it as our main option.”
- Keep canonical source text and citations outside OMP's compacted live history, approved 2026-10-26.
- Model, tool and skill selection belong to per-conversation configuration. A permanent no-tools/no-skills architecture is not the decision.

## Consequences

- Native application/window coordination can own panels, focus and platform integration while RPC remains language-neutral.
- Native UI does not establish capture invisibility. The required privacy/focus probes and final `.app` compatibility tests still have to run.
- A renderer choice within the native shell, including a bounded WebKit view if justified, is not yet decided.
- An ASR runtime, exact capture path, OMP executable packaging, safe per-conversation configuration and persistence/deletion design remain open.
- Tauri and Electron are fallback candidates if measured feasibility or engineering cost warrants revisiting this direction; no switch is silently approved.

## Resolves

Primary shell portion of baseline Q-09 and NFR-08; RPC integration direction in FR-02. Does not approve an implementation plan, clinical efficacy, stealth capability or measured latency.
