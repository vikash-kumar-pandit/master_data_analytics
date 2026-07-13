# Build Stage
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Set production env vars for Vite build
ENV VITE_API_URL=/api
ENV VITE_APP_ENV=production
ENV VITE_MOCK_API=false

RUN npm run build

# Runtime Stage
FROM nginx:1.25-alpine

COPY --from=builder /app/dist /usr/share/nginx/html

# Simple server config for local routing inside this container.
RUN echo 'server { \
    listen 80; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html; \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
