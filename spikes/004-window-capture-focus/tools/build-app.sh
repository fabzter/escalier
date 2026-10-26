#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRATCH_PATH="${SCRATCH_PATH:-.build}"
cd "$ROOT"

xcrun swift build --scratch-path "$SCRATCH_PATH" -c debug
BIN_DIR="$(xcrun swift build --scratch-path "$SCRATCH_PATH" -c debug --show-bin-path)"
APP="$SCRATCH_PATH/EscalierCaptureFixture.app"

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$BIN_DIR/EscalierCaptureFixture" "$APP/Contents/MacOS/EscalierCaptureFixture"
cp "Resources/Info.plist" "$APP/Contents/Info.plist"
printf 'APPL????' > "$APP/Contents/PkgInfo"

# Local ad-hoc signing for launch tests only. This is not Developer ID,
# notarization, Gatekeeper approval or stable TCC identity across rebuilds.
codesign --force --sign - --timestamp=none "$APP"
codesign --verify --strict --verbose=2 "$APP"

printf 'Built %s\n' "$APP"
printf 'Bundle is ad-hoc signed and verified; NOT Developer ID/notarized and NOT launched.\n'
