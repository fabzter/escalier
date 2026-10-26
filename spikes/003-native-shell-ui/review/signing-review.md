# Spike 003 signing addendum review

Date: 2026-10-26
Reviewer: independent task reviewer (spec + quality)
Scope: the local ad-hoc self-signing addendum only; not a second whole-shell review.
The initial shell review [`implementation-review.md`](implementation-review.md) is context, and its
seven deferred minors remain assigned to the final broad review.

Diff reviewed once: `spikes/001-transcription/.tools/reviews/native-shell-signing.diff`, range
`f758f34..a79f12e`. Evidence accepted: coordinator fresh `swift test` → **36 XCTest cases, 0
failures**; `tools/test-package-signing.sh` → fake signing failure **42** stops before verification,
fake verification failure **43** propagates after signing, then repackages the genuine bundle; actual
`.build/EscalierShell.app` passes `codesign --verify --strict --verbose=2` and reports
`Signature=adhoc`, `Identifier=local.escalier.spike003.shell`, `TeamIdentifier=not set`, bound
`Info.plist`, and an arm64 Mach-O executable. No app was launched.

### Checks run

- Read the signing diff, `PLAN.md`, `README.md`, `FINDINGS.md`, the report addendum,
  `tools/package-app.sh`, `tools/test-package-signing.sh`, `PackagingScriptTests.swift`,
  `Resources/Info.plist`, and `review/progress.md`.
- Read the recorded `signing-red-test.log`, `signing-static-test.log`, `signing-guard.log`,
  `signing-verify.log`, and `package-final.log`; accepted the coordinator's fresh 36/0 suite run.
- Read-only probe of the actual bundle: `codesign --verify --strict --verbose=2` exits 0 with
  `valid on disk` and `satisfies its Designated Requirement`; `codesign -dv` shows the claimed
  `Identifier`, `Signature=adhoc`, `TeamIdentifier=not set`, `Info.plist entries=11`, and
  `Sealed Resources version=2 rules=13 files=0`; the bundle contains only `Info.plist`, `PkgInfo`,
  `_CodeSignature`, and an arm64 Mach-O executable. I did not rerun the suite or harness, and did not
  launch the app.

## Spec Compliance

✅ **PASS** — the addendum implements the owner-directed local ad-hoc signing flow exactly, fails
closed on both signing and verification errors, and does not cross the prohibited signing, trust,
policy, or launch boundaries. The documented status is accurate.

### Requirement-by-requirement

1. **Owner-approved local self-signing.** The owner direction is recorded in
   `review/progress.md:36` and `review/implementation-report.md:256-261`: local ad-hoc signing for
   later launch testing, with no certificate, keychain trust/identity, entitlements, `--deep`,
   Gatekeeper/TCC/quarantine changes, or GUI launch. This matches the latest owner direction.
2. **Assemble the bundle before signing.** `tools/package-app.sh:17-27` builds and assembles the
   executable, `Info.plist`, and `PkgInfo`, then lints the plist. The static guard checks that the
   plist copy precedes signing (`PackagingScriptTests.swift:32-52`).
3. **Exact signing command.** `tools/package-app.sh:28` runs
   `codesign --force --sign - --timestamp=none "$APP"` after assembly. The static guard pins this
   exact command (`PackagingScriptTests.swift:21,36-39,45-48`).
4. **Exact strict verification.** `tools/package-app.sh:29` runs
   `codesign --verify --strict --verbose=2 "$APP"` after signing. The static guard pins the exact
   command and order (`PackagingScriptTests.swift:22,40-52`).
5. **Fail closed on signing/verification error.** `tools/package-app.sh:4` sets
   `set -euo pipefail`; both `codesign` invocations are direct, unwrapped commands. The executable
   harness injects a failing signer and verifier through `PATH` and proves packaging aborts:
   sign failure 42 produces no verification attempt, and verification failure 43 aborts after the
   sign call (`tools/test-package-signing.sh:35-73`; `signing-guard.log:1-2`).
6. **Prohibited actions absent.** The package script and harness contain no `--deep`, certificate
   creation/trust, keychain identity selection, entitlement grants, `--options`, `spctl`, `xattr`,
   `tccutil`, `security`, or app-launch command (`tools/package-app.sh:1-30`;
   `tools/test-package-signing.sh:1-89`). The README and FINDINGS explicitly leave notarization,
   Developer ID, Gatekeeper approval, Dock/activation identity, and bundle launch as not claimed or
   not tested (`README.md:130-132,152-158`; `FINDINGS.md:93-97,110-152`;
   `review/implementation-report.md:353-364`).
7. **Meaningful tests.** The XCTest suite adds one static guard, but the behavioral evidence is the
   separate executable harness: it exercises failure propagation, then runs the real packager and
   strictly verifies the genuine bundle (`tools/test-package-signing.sh:75-89`). The 36-test run and
   the harness output agree with the report's evidence sections
   (`review/implementation-report.md:306-351`). The original 35 tests remain preserved
   (`FINDINGS.md:57-66`).

### Not in scope

Interactive visuals, keyboard/focus/scroll behavior, VoiceOver, Dock/icon/activation identity, and
bundle launch remain **NOT TESTED** by design. The initial review's seven minors are not re-reviewed
here; no second whole-shell review was performed.

## Task Quality

✅ **Approved** — the addendum is small, focused, and correctly separates the static guard from the
dynamic failure harness. The harness is not a compile-only or string-only check: it falsifies the
two critical failure paths and then verifies the real artifact, which is the right evidence for the
owner's fail-closed requirement.

Strengths:

- The static guard pins the exact sign/verify commands and order, rejects the prohibited signing
  flags, and requires the failure harness to be executable
  (`PackagingScriptTests.swift:21-30,54-71`).
- The fake `codesign` is selected by `PATH`; package output is redirected, and the harness checks
  both non-zero status and the absence/presence/order of the sign and verify calls
  (`tools/test-package-signing.sh:14-73`). A regression that swallows either failure would fail the
  harness, not merely the source check.
- The genuine run after the negative cases restores the real bundle, then verifies it and checks the
  claimed signature facts (`tools/test-package-signing.sh:75-89`). The recorded `signing-guard.log`
  and `signing-verify.log` match the actual bundle.
- The documentation separates local ad-hoc signing from Developer ID signing, notarization, and
  Gatekeeper approval, and refuses to infer launch or Dock identity from the signature
  (`README.md:130-132,152-158`; `FINDINGS.md:93-97`).
- The 35 pre-addendum tests are explicitly preserved; the new test is additional, not a replacement
  (`FINDINGS.md:57-66`).

Caveat, not a defect: the dynamic failure-propagation test is a standalone script rather than an
XCTest. The 36-test count therefore includes only the static guard; a CI that runs `swift test`
alone would not exercise the fake-failure path. The README documents the harness command and the
coordinator ran it, so this is adequate for the spike, but the split should remain explicit.

## Issues

### Critical (Must Fix)

None.

### Important (Should Fix)

None.

### Minor (new, non-blocking)

1. **The static guard does not enforce the no-launch/no-policy prohibitions on the production
   package script.** `PackagingScriptTests.swift:26-30` checks `--deep`, `--keychain`,
   `--entitlements`, `--options`, and `|| true` in `tools/package-app.sh`, but the only `spctl`,
   `xattr`, and `open .build` assertions are applied to the harness (`:68-71`). The package script
   currently complies (`tools/package-app.sh:28-30` has no launch or policy command), so this is a
   guard gap rather than a violation: a future edit adding `open "$APP"`, `spctl`, `xattr`,
   `tccutil`, or `security` to the packager would still pass the XCTest. Minimal fix: apply one
   shared forbidden-token/command list to both scripts, including launch and policy tools.
2. **The failure harness does not pin the exact fake statuses or all of the exact signature facts
   it documents.** `tools/test-package-signing.sh:49-51,61-63` only rejects status 0; it does not
   assert 42/43, while `README.md:115-116` and `FINDINGS.md:39` claim those exact values. Likewise
   `:80-84` checks `Info.plist entries=` and `Sealed Resources version=` as prefixes, not the
   documented `entries=11` and `files=0` (`README.md:121-127`; report `:341-351`). If the fake
   exits change to another non-zero value, or the plist/resource counts drift, the harness can still
   pass while the documented evidence becomes stale. Minimal fix: assert
   `sign_fail_status -eq 42`, `verify_fail_status -eq 43`, and the exact claimed fact values, or
   narrow the documentation to say those are observed values rather than test invariants.

### Out-of-Scope Observations

- The seven minors in `implementation-review.md:117-143` (retained-assistance display, menu phase
  gating, shortcut-hint drift, source-audit scanner coverage, mid-stream snapshot labeling,
  preparation copy, and window-size wording) are unchanged and remain for the final broad review.
- The reviewed commit range also adds `review/implementation-review.md`, which is the
  coordinator-owned initial shell review record rather than an implementation change. The addendum
  report's "Files changed by this addendum only" list is accurate for the worker's implementation
  changes; a final ledger may still want to distinguish that from the commit range as a whole.
- Interactive GUI, keyboard/focus/scroll, VoiceOver, bundle launch, Dock/icon/activation identity,
  and Gatekeeper behavior remain unverified and are correctly labeled **NOT TESTED**.

## Assessment

**Spec compliance:** ✅ **PASS** — every owner-directed signing requirement is implemented and
tested; the prohibited signing, trust, policy, and launch actions are absent; the bundle's actual
ad-hoc signature and strict-verification facts match the documentation.

**Task quality:** **Approved** — the static guard plus executable failure harness and genuine
artifact verification are meaningful evidence for fail-closed signing. The two minor findings are
test-guard precision improvements, not correctness or scope failures. No Critical or Important
finding was identified.

**Signing addendum verdict:** **Approved; no new Critical/Important breakage.**
