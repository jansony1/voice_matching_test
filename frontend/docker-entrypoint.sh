#!/bin/sh

# Replace the backend URL in config.js with the environment variable
sed -i "s|http://localhost:8000|$BACKEND_URL|g" /usr/share/nginx/html/config.js

# Start nginx
exec "$@"
