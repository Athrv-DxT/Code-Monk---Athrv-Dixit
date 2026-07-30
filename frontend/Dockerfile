# Build Stage
FROM node:18-alpine AS build

WORKDIR /app

# Copy dependency files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm ci || npm install

# Copy source code and build
COPY . .
RUN npm run build

# Production Stage
FROM nginx:alpine

# Copy built static files to Nginx public folder
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration if needed, or use default
# We can overwrite the default config to handle SPA routing (fallback to index.html)
RUN echo 'server { \
    listen 80; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html index.htm; \
        try_files $uri $uri/ /index.html; \
    } \
    location /api { \
        proxy_pass http://backend:8000; \
        proxy_http_version 1.1; \
        proxy_set_header Upgrade $http_upgrade; \
        proxy_set_header Connection "upgrade"; \
        proxy_set_header Host $host; \
        proxy_cache_bypass $http_upgrade; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
