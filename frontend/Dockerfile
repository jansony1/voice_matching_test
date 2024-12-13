FROM node:18-alpine as builder

WORKDIR /app

# Install dependencies
COPY frontend/package*.json ./
RUN npm install

# Create directory structure first
RUN mkdir -p public/shared/config
# RUN mkdir -p public/shared/config

# Copy all frontend files
COPY frontend/ .

# Copy shared configuration
COPY shared/config/models_config.json public/shared/config/

# Build production version
RUN npm run build

# Production environment - using nginx to serve static files
FROM nginx:alpine

# Copy built static files
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy config.js and polyfill to nginx html directory
COPY frontend/public/config.js /usr/share/nginx/html/
COPY frontend/public/credentials-polyfill.js /usr/share/nginx/html/

# Create shared config directory and copy configuration
RUN mkdir -p /usr/share/nginx/html/shared/config
COPY --from=builder /app/public/shared/config/models_config.json /usr/share/nginx/html/shared/config/

# Enhanced nginx configuration with extended timeouts and CORS settings
RUN echo 'server { \
    listen 80; \
    \
    # Extended timeout and performance settings \
    client_max_body_size 50M; \
    client_body_timeout 600s; \
    client_header_timeout 600s; \
    keepalive_timeout 600s; \
    send_timeout 600s; \
    proxy_connect_timeout 600s; \
    proxy_send_timeout 600s; \
    proxy_read_timeout 600s; \
    fastcgi_read_timeout 600s; \
    \
    # CORS headers \
    add_header Access-Control-Allow-Origin * always; \
    add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always; \
    add_header Access-Control-Allow-Headers "DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization" always; \
    add_header Access-Control-Expose-Headers "Content-Length,Content-Range" always; \
    \
    location /api { \
        proxy_pass http://backend:8000; \
        proxy_set_header Host $host; \
        proxy_set_header X-Real-IP $remote_addr; \
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; \
        proxy_set_header X-Forwarded-Proto $scheme; \
        \
        # Extended proxy timeouts \
        proxy_connect_timeout 600s; \
        proxy_send_timeout 600s; \
        proxy_read_timeout 600s; \
    } \
    \
    location / { \
        root /usr/share/nginx/html; \
        index index.html; \
        try_files $uri $uri/ /index.html; \
    } \
    \
    # Handle OPTIONS requests \
    if ($request_method = OPTIONS) { \
        return 204; \
    } \
}' > /etc/nginx/conf.d/default.conf

# Copy the entrypoint script
COPY frontend/docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh

EXPOSE 80

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
