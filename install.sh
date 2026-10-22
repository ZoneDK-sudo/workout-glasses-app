#!/bin/sh
# Copies Workout Counter (glasses) and Workout Tracker (phone) into your copy of
# MemoMind's plugin-open-platform SDK, then you build with `./build.py`.
# Usage: ./install.sh [path/to/plugin-open-platform]   (default: ~/plugin-open-platform)
set -e
SDK="${1:-$HOME/plugin-open-platform}"
HERE="$(cd "$(dirname "$0")" && pwd)"
[ -d "$SDK/GlassSDK" ] && [ -d "$SDK/PhoneSDK" ] || { echo "Couldn't find the SDK at '$SDK'. Clone https://github.com/memomind-open/plugin-open-platform first." >&2; exit 1; }
cp -R "$HERE/glasses/situp_counter" "$SDK/GlassSDK/examples/"
cp -R "$HERE/phone/situp-tracker" "$SDK/PhoneSDK/examples/"
mkdir -p "$SDK/PhoneSDK/examples/situp-tracker/vendor"
cp "$SDK/PhoneSDK/examples/fighter-controller/vendor/gm-plugin-web-sdk.esm.js" "$SDK/PhoneSDK/examples/situp-tracker/vendor/"
echo "Installed. Now run: cd \"$SDK\" && ./build.py"
