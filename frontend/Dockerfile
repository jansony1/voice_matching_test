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

# Enhanced nginx configuration with CORS and file upload settings
RUN echo 'server { \
    listen 80; \
    \
    # File upload settings \
    client_max_body_size 10M; \    

    \
    # CORS headers \
    add_header Access-Control-Allow-Origin * always; \
    add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always; \
    add_header Access-Control-Allow-Headers "DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization" always; \
    add_header Access-Control-Expose-Headers "Content-Length,Content-Range" always; \
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