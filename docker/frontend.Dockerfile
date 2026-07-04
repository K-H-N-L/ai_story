# Build stage
FROM node:22-alpine AS build

WORKDIR /app

ARG VUE_APP_API_BASE_URL=

# Copy package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY frontend/ ./

# Build the application with the API base URL
RUN VUE_APP_API_BASE_URL=${VUE_APP_API_BASE_URL} npm run build

# Production stage
FROM nginx:1.25-alpine

COPY docker/nginx/frontend.conf /etc/nginx/conf.d/default.conf
COPY --from=build /dist /usr/share/nginx/html

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
