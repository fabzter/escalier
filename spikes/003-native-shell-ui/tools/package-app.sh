#!/usr/bin/env bash
# Builds and packages the dependency-free spike as a local .app bundle.
# This script never launches the app and never installs anything.
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

swift build -c debug --product EscalierShell

APP=".build/EscalierShell.app"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

cp ".build/debug/EscalierShell" "$APP/Contents/MacOS/EscalierShell"
cp "Resources/Info.plist" "$APP/Contents/Info.plist"
printf 'APPL????' > "$APP/Contents/PkgInfo"

plutil -lint "$APP/Contents/Info.plist"
codesign --force --sign - --timestamp=none "$APP"
codesign --verify --strict --verbose=2 "$APP"
echo "Packaged and ad-hoc signed $APP (not notarized, not launched)"
