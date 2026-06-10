# Multi-stage Docker build for Angular application
# Build stage
ARG BASE_REGISTRY=docker.io
FROM ${BASE_REGISTRY}/node:26-alpine AS build

ARG NPM_REGISTRY=
# Empty default uses npm's default registry; set to Artifactory npm URL for enterprise builds

# Set working directory
WORKDIR /app

# Optional enterprise CA bundle: drop *.crt/*.pem into src/certs/ and the npm
# install/build trusts them (corporate TLS interception / internal Artifactory
# CA). Empty in public checkouts — the file stays empty and node ignores it.
COPY certs /certs
RUN touch /tmp/extra-ca.pem && \
    cat /certs/*.crt /certs/*.pem >> /tmp/extra-ca.pem 2>/dev/null || true
ENV NODE_EXTRA_CA_CERTS=/tmp/extra-ca.pem

# Copy package files
COPY frontend-angular/package*.json ./

# Install dependencies from the npm registry.
# npm_cache/ is gitignored and excluded by .dockerignore (absent in CI), so the
# build must not depend on it. --include=dev is required for the Angular CLI
# build; --ignore-scripts skips the Cypress binary download (not needed for the
# production build).
RUN npm ci --include=dev --legacy-peer-deps --ignore-scripts

# Copy source code
COPY frontend-angular/ .

# Verify ng is installed
RUN ls -la node_modules/.bin/ng || echo "ng not found"

# Build the application for production
RUN npm run build -- --configuration=production

# Production stage
FROM ${BASE_REGISTRY}/nginx:alpine AS production

# Install curl for health checks
RUN apk add --no-cache curl

# Copy built application from build stage
COPY --from=build /app/dist/aio-ui/browser /usr/share/nginx/html
# Ensure runtime env template is available for envsubst step
COPY --from=build /app/src/assets/env.js.template /usr/share/nginx/html/assets/env.js.template

# Copy nginx configuration as main config (not as template)
# This allows us to use envsubst manually with proper permissions
COPY --from=build /app/nginx.conf.template /etc/nginx/nginx.conf.template

# Copy PWA service worker configuration from build stage
COPY --from=build /app/ngsw-config.json /usr/share/nginx/html/ngsw-config.json
COPY --from=build /app/dist/aio-ui/browser/ngsw-worker.js /usr/share/nginx/html/ngsw-worker.js

# Create entrypoint script that runs as root before nginx starts
RUN echo '#!/bin/sh' > /docker-entrypoint.sh && \
    echo 'set -e' >> /docker-entrypoint.sh && \
    echo '' >> /docker-entrypoint.sh && \
    echo '# Set default values for environment variables' >> /docker-entrypoint.sh && \
    echo 'export BACKEND_HOST=${BACKEND_HOST:-orchestrator-api-test}' >> /docker-entrypoint.sh && \
    echo 'export BACKEND_PORT=${BACKEND_PORT:-8000}' >> /docker-entrypoint.sh && \
    echo 'export FRONTEND_VERBOSE_LOGGING=${FRONTEND_VERBOSE_LOGGING:-false}' >> /docker-entrypoint.sh && \
    echo '' >> /docker-entrypoint.sh && \
    echo '# Substitute environment variables in nginx config' >> /docker-entrypoint.sh && \
    echo 'envsubst '"'"'$BACKEND_HOST $BACKEND_PORT'"'"' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf' >> /docker-entrypoint.sh && \
    echo '' >> /docker-entrypoint.sh && \
    echo '# Substitute runtime frontend config' >> /docker-entrypoint.sh && \
    echo 'envsubst '"'"'$FRONTEND_VERBOSE_LOGGING'"'"' < /usr/share/nginx/html/assets/env.js.template > /usr/share/nginx/html/assets/env.js' >> /docker-entrypoint.sh && \
    echo '' >> /docker-entrypoint.sh && \
    echo '# Set proper permissions for nginx user' >> /docker-entrypoint.sh && \
    echo 'chown nginx:nginx /etc/nginx/nginx.conf' >> /docker-entrypoint.sh && \
    echo 'chmod 644 /etc/nginx/nginx.conf' >> /docker-entrypoint.sh && \
    echo '' >> /docker-entrypoint.sh && \
    echo '# Start nginx as nginx user' >> /docker-entrypoint.sh && \
    echo 'exec nginx -g "daemon off;"' >> /docker-entrypoint.sh && \
    chmod +x /docker-entrypoint.sh

# Set proper permissions for directories that nginx needs to write to
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    chmod -R 755 /var/cache/nginx && \
    chmod -R 755 /var/log/nginx && \
    mkdir -p /var/run/nginx && \
    chown -R nginx:nginx /var/run/nginx && \
    chmod -R 755 /var/run/nginx

# Note: We don't switch to USER nginx here because the entrypoint needs root
# to write the config file, but nginx itself will run as the nginx user

# Expose port 80
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80/health || exit 1

# Use custom entrypoint
ENTRYPOINT ["/docker-entrypoint.sh"]
