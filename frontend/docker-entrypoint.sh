#!/bin/sh
set -e

# Log the environment variable for debugging
echo "BACKEND_URL is set to: $BACKEND_URL"

# Replace the backend URL in config.js
if [ -n "$BACKEND_URL" ]; then
    echo "Updating backend URL to: $BACKEND_URL"
    sed -i "s|http://localhost:8000|$BACKEND_URL|g" /usr/share/nginx/html/config.js
    echo "Config.js content after update:"
    cat /usr/share/nginx/html/config.js
else
    echo "Warning: BACKEND_URL is not set, using default"
fi

# Start nginx
echo "Starting nginx..."
exec "$@"
