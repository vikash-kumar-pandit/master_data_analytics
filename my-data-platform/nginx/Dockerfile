# Stage 1: Build the React Frontend
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency files relative to build context (repository root)
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Copy frontend source code and build it
COPY frontend/ ./
ENV VITE_API_URL=/api
ENV VITE_APP_ENV=production
ENV VITE_MOCK_API=false
RUN npm run build

# Stage 2: Serve via Nginx reverse proxy
FROM nginx:1.25-alpine

# Copy compiled static assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy unified Nginx config
COPY nginx/nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
