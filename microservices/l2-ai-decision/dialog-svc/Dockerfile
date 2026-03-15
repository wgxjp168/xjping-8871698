# ─── Stage 1: dependency installation ────────────────────────────────────────
FROM node:20-alpine AS deps

WORKDIR /app

# Copy only package manifests first to leverage Docker layer cache.
COPY package.json package-lock.json* ./

# Install production dependencies only; skip optional native addons.
RUN npm ci --only=production --ignore-scripts


# ─── Stage 2: production image ────────────────────────────────────────────────
FROM node:20-alpine AS runtime

# Install dumb-init to handle PID-1 signal forwarding and zombie-process reaping.
RUN apk add --no-cache dumb-init

WORKDIR /app

# Create a non-root user/group for security hardening.
RUN addgroup --system --gid 1001 nodejs \
 && adduser  --system --uid 1001 --ingroup nodejs appuser

# Copy production node_modules from the deps stage.
COPY --from=deps /app/node_modules ./node_modules

# Copy application source code.
COPY src ./src
COPY package.json ./

# Change ownership of all app files to the non-root user.
RUN chown -R appuser:nodejs /app

# Switch to non-root user.
USER appuser

# Document the port this service listens on.
EXPOSE 8013

# Health-check using the built-in /health endpoint.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD wget -qO- http://localhost:8013/health || exit 1

# Use dumb-init as the entrypoint so that Node.js receives OS signals correctly.
ENTRYPOINT ["dumb-init", "--"]
CMD ["node", "src/app.js"]
