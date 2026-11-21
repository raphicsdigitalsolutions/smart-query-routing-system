# Production image for the Next.js 15 BFF/UI.
# Build from the frontend-next/ directory: docker build -t smartquery-frontend ./frontend-next
#
# next.config.ts in this repository does not set `output: 'standalone'`, so the
# runtime stage uses the normal production server (`next start`) with production
# dependencies only. NEXT_PUBLIC_* values are inlined at BUILD time and must be
# supplied as build args; never pass secrets as NEXT_PUBLIC_* variables.

FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

FROM node:20-alpine AS builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
ARG NEXT_PUBLIC_GOOGLE_CLIENT_ID=""
# These are public identifiers, not secrets. They are compiled into client JS.
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL} \
    NEXT_PUBLIC_GOOGLE_CLIENT_ID=${NEXT_PUBLIC_GOOGLE_CLIENT_ID}
COPY --from=deps /app/node_modules ./node_modules
COPY package.json package-lock.json next.config.ts tsconfig.json next-env.d.ts ./
COPY src ./src
COPY public ./public
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

RUN addgroup -g 10001 -S nextjs \
    && adduser -u 10001 -S -G nextjs -h /home/nextjs nextjs

COPY --from=builder --chown=nextjs:nextjs /app/package.json ./
COPY --from=builder --chown=nextjs:nextjs /app/package-lock.json ./
COPY --from=builder --chown=nextjs:nextjs /app/next.config.ts ./
COPY --from=builder --chown=nextjs:nextjs /app/.next ./.next
COPY --from=builder --chown=nextjs:nextjs /app/public ./public

# Production-only dependencies. No dev tooling, no .env, no source secrets.
RUN npm ci --omit=dev --no-audit --no-fund

# `next start` loads next.config.ts at runtime. TypeScript is normally a dev
# dependency, so copy just that package from the deps stage; otherwise Next
# tries to install it as the non-root user and crashes on startup.
COPY --from=deps --chown=nextjs:nextjs /app/node_modules/typescript ./node_modules/typescript

USER nextjs
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["node", "-e", "fetch('http://127.0.0.1:3000/api/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"]

# The package.json `start` script pins 127.0.0.1; the trailing flags override it
# so the server is reachable from outside the container. This is `npm start`.
CMD ["npm", "start", "--", "--hostname", "0.0.0.0", "--port", "3000"]
