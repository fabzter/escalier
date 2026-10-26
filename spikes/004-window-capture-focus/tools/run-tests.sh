#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

xcrun swift test --scratch-path .build
node --test web/tests/*.test.mjs tools/tests/*.test.mjs
node tools/validate.mjs

printf 'All headless tests and static audits passed. No app, browser, server or capture was started.\n'
