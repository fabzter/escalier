# Spike 003 — native shell and UI prototype

Owner approved parallel shell/UI/stealth research spikes on 2026-10-26. This is a self-contained low-fidelity prototype, not a production UI commitment or full-app implementation approval. Primary architecture authority: [ADR-0001](../../docs/decisions/0001-native-macos-and-omp-rpc.md); functional panel behavior: [requirements](../../docs/requirements.md).

## Bounded outcome

A locally buildable SwiftUI + AppKit shell demonstrating preparation/conversation navigation, a synthetic two-source transcript, a reference panel with source excerpts and stable navigation, and an assistance panel with incremental synthetic text and a complete local image/diagram placeholder. Include per-conversation model/tool/skill selection UI as mock state only, plus retained-result selection/delete as in-memory synthetic state only. All sample content is invented. No actual files/vault/private history, OMP/LLM, audio/capture, networking or persistent user-data deletion.

Make controls and evidence labels clear. Use a neutral native wireframe; style and exact layout are provisional and reversible. Model selection and tool/skill controls must not pretend they enforce a runtime policy. Shortcuts can demonstrate distinct actions, but bindings are provisional. Do not copy Natively code or app identity. Build in project-local `.tools/`/`.build/`; no package or host installs. Do not launch or drive a native window via Bash/AppleScript. This worker may compile and run headless tests; GUI launch/observation uses computer with live human confirmation in a separate step.

## File ownership

Worker owns only this directory's `README.md`, `Sources/**`, `Tests/**`, `tools/**`, and `review/implementation-report.md`. Coordinator owns this PLAN and review records. Do not edit root docs, ASR, or stealth spike. No shared Git-index/commits or subagents.

## Implementation/test sequence

1. Read ADR/requirements and official SwiftUI/AppKit docs for any uncertain API; project is dependency-free. Keep pure presentation state separate from AppKit process/window bootstrapping.
2. RED tests for immutable sample-source identities/citations, stable selected reference when another candidate arrives, distinct action routing, per-conversation capability selections, retained synthetic results/delete isolation and stable synthetic streaming history. No real data deletion or CLI/network side effects.
3. Implement the smallest model and native shell satisfying those tests. Keep transcript/search/assistance provenance visually distinct. Model/input/permissions status is explicitly MOCK or NOT CONNECTED. Add a local harmless SVG/vector diagram if useful, not image-generation networking.
4. GREEN headless tests and native build using installed Xcode compiler/SDK, with build outputs confined here. Record exact commands/artifact paths and fail clear if tools are missing, never install them automatically.
5. Write README with question, build/test/run instructions, synthetic/mock boundaries, screenshot/manual review checklist and findings. Mark GUI visual/keyboard/focus behavior NOT TESTED until interactive evidence exists; build success is not a UI pass. Report decisions and limitations.

## Review gate

Independent spec/quality review after implementation; no important open defects accepted silently. Findings must distinguish unit-tested presentation logic, compile-checked API use and untested UI behavior. No latency/stealth/OMP-policy enforcement claim follows from this prototype.
