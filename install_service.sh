#!/bin/bash
#
# Install the marathi-responder launchd service.
#
set -e

PROJECT_DIR="/Users/maxrecursion/Projects/marathi-tweet-responder"
PLIST_NAME="com.akshay.marathi-responder.plist"
SRC_PLIST="${PROJECT_DIR}/${PLIST_NAME}"
DST_PLIST="${HOME}/Library/LaunchAgents/${PLIST_NAME}"

if [ ! -f "${SRC_PLIST}" ]; then
    echo "❌ Plist not found: ${SRC_PLIST}"
    exit 1
fi

mkdir -p "${HOME}/Library/LaunchAgents"
mkdir -p "${HOME}/Library/Logs"

# If already loaded, unload first
if launchctl list | grep -q "com.akshay.marathi-responder"; then
    echo "→ Unloading existing service"
    launchctl unload "${DST_PLIST}" 2>/dev/null || true
fi

echo "→ Copying plist to ${DST_PLIST}"
cp "${SRC_PLIST}" "${DST_PLIST}"

echo "→ Loading service"
launchctl load "${DST_PLIST}"

echo "→ Verifying"
if launchctl list | grep -q "com.akshay.marathi-responder"; then
    echo "✅ Service installed and loaded"
    launchctl list | grep "marathi"
else
    echo "❌ Service failed to load"
    exit 1
fi
