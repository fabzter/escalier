#!/usr/bin/env bash
# Builds and packages the dependency-free fixture as a local .app bundle.
# The bundle is signed ad hoc for local launchability only.
# This script never launches the app, installs anything, creates/trusts a certificate,
# changes Gatekeeper/TCC state or requests a permission.
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v swift >/dev/null 2>&1; then
  echo "error: Swift toolchain not found; this script does not install tools" >&2
  exit 1
fi
if ! command -v plutil >/dev/null 2>&1; then
  echo "error: plutil not found; this script does not install tools" >&2
  exit 1
fi
if ! command -v codesign >/dev/null 2>&1; then
  echo "error: codesign not found; this script does not install tools" >&2
  exit 1
fi

swift build -c debug --product RoutingFixture

APP=".build/RoutingFixture.app"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

cp ".build/debug/RoutingFixture" "$APP/Contents/MacOS/RoutingFixture"
cp "Resources/Info.plist" "$APP/Contents/Info.plist"
printf 'APPL????' > "$APP/Contents/PkgInfo"

test -x "$APP/Contents/MacOS/RoutingFixture"
test -f "$APP/Contents/Info.plist"
plutil -lint "$APP/Contents/Info.plist"

# Local ad-hoc identity only. This is not Developer ID, not notarized, and does not
# provide a Gatekeeper trust guarantee. The ad-hoc code identity may change across
# rebuilds, so TCC grant reuse is not established.
codesign --force --sign - --timestamp=none "$APP"
codesign --verify --strict --verbose=2 "$APP"

SIGNATURE_REPORT="$(codesign --display --verbose=4 "$APP" 2>&1)"
if ! printf '%s\n' "$SIGNATURE_REPORT" | grep -F 'Signature=adhoc' >/dev/null; then
  echo "error: expected an ad-hoc signature; codesign reported:" >&2
  printf '%s\n' "$SIGNATURE_REPORT" >&2
  exit 1
fi
printf '%s\n' "$SIGNATURE_REPORT" | grep -E '^(Identifier|Format|Signature|TeamIdentifier)=' || true
echo "Ad-hoc signed and strictly verified $APP (not launched; no TCC grant)"
