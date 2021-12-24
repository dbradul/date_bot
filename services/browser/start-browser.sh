#!/bin/bash

Xvfb :10 -ac &
export DISPLAY=:10

socat tcp-listen:${CHROME_REMOTE_DEBUG_PORT},reuseaddr,fork tcp:localhost:9222 &
google-chrome --headless --no-sandbox -incognito --remote-debugging-port=9222 --disable-gpu --user-data-dir=/app/data
