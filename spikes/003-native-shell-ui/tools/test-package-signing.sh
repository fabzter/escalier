#!/usr/bin/env bash
# Headless signing guard. Builds/packages only; it never launches the app.
# Two fake-codesign runs prove that signing and verification failures propagate.
set -euo pipefail

cd "$(dirname "$0")/.."

APP=".build/EscalierShell.app"
HARNESS_DIR="$(pwd)/.build/signing-test"
BIN="$HARNESS_DIR/bin"
rm -rf "$HARNESS_DIR"
mkdir -p "$BIN"

cat > "$BIN/codesign" <<'FAKE_CODESIGN'
#!/usr/bin/env bash
set -u
if [[ -z "${CODESIGN_LOG:-}" ]]; then
  echo "fake codesign: CODESIGN_LOG missing" >&2
  exit 90
fi
printf '%s\n' "$*" >> "$CODESIGN_LOG"
case "${FAKE_CODESIGN_MODE:-ok}" in
  sign-fail) exit 42 ;;
  verify-fail)
    case " $* " in
      *" --verify "*) exit 43 ;;
      *) exit 0 ;;
    esac
    ;;
  *) exit 0 ;;
esac
FAKE_CODESIGN
chmod +x "$BIN/codesign"

run_fake() {
  local mode="$1"
  local log="$2"
  local output="$HARNESS_DIR/package-$mode.log"
  : > "$log"
  set +e
  PATH="$BIN:$PATH" CODESIGN_LOG="$log" FAKE_CODESIGN_MODE="$mode" \
    ./tools/package-app.sh >"$output" 2>&1
  local status=$?
  set -e
  printf '%s\n' "$status"
}

sign_fail_status="$(run_fake sign-fail "$HARNESS_DIR/sign-fail-codesign.log")"
if [[ "$sign_fail_status" -eq 0 ]]; then
  echo "FAIL: signing failure was swallowed" >&2
  exit 1
fi
grep -F -- "--force" "$HARNESS_DIR/sign-fail-codesign.log" >/dev/null
if grep -F -- "--verify" "$HARNESS_DIR/sign-fail-codesign.log" >/dev/null; then
  echo "FAIL: verification ran after signing failed" >&2
  exit 1
fi
echo "PASS: signing failure propagated (status $sign_fail_status); verify not attempted"

verify_fail_status="$(run_fake verify-fail "$HARNESS_DIR/verify-fail-codesign.log")"
if [[ "$verify_fail_status" -eq 0 ]]; then
  echo "FAIL: verification failure was swallowed" >&2
  exit 1
fi
grep -F -- "--force" "$HARNESS_DIR/verify-fail-codesign.log" >/dev/null
grep -F -- "--verify" "$HARNESS_DIR/verify-fail-codesign.log" >/dev/null
sign_line="$(grep -n -F -- "--force" "$HARNESS_DIR/verify-fail-codesign.log" | head -1 | cut -d: -f1)"
verify_line="$(grep -n -F -- "--verify" "$HARNESS_DIR/verify-fail-codesign.log" | head -1 | cut -d: -f1)"
if [[ -z "$sign_line" || -z "$verify_line" || "$sign_line" -ge "$verify_line" ]]; then
  echo "FAIL: signing/verification order or calls incorrect" >&2
  exit 1
fi
echo "PASS: verification failure propagated (status $verify_fail_status) after signing"

# Restore the genuine ad-hoc signed bundle and check its exact signature facts.
./tools/package-app.sh
codesign --verify --strict --verbose=2 "$APP"
codesign -dv --verbose=4 "$APP" 2> "$HARNESS_DIR/signature.txt"

grep -F "Identifier=local.escalier.spike003.shell" "$HARNESS_DIR/signature.txt" >/dev/null
grep -F "Signature=adhoc" "$HARNESS_DIR/signature.txt" >/dev/null
grep -F "TeamIdentifier=not set" "$HARNESS_DIR/signature.txt" >/dev/null
grep -F "Info.plist entries=" "$HARNESS_DIR/signature.txt" >/dev/null
grep -F "Sealed Resources version=" "$HARNESS_DIR/signature.txt" >/dev/null

echo "PASS: real bundle is ad-hoc signed and verified; signature facts:"
grep -E "^(Identifier|Format|CodeDirectory|Signature|Info.plist|TeamIdentifier|Sealed Resources)" \
  "$HARNESS_DIR/signature.txt"
echo "Note: ad-hoc signing is not notarization or Gatekeeper approval; app launch remains untested."
