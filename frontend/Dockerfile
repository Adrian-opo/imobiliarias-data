FROM node:20-alpine AS base

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm ci

# Build
COPY . .
ENV NEXT_PUBLIC_API_URL=https://imoveisjipa.adrianx.dev
ENV NEXT_PUBLIC_SITE_NAME="Imóveis Ji-Paraná"
ENV NEXT_PUBLIC_SITE_DESCRIPTION="Central de imóveis de Ji-Paraná - Encontre o imóvel ideal na capital do café de Rondônia"

RUN npm run build

# Production image
FROM node:20-alpine AS runner
WORKDIR /app

COPY --from=base /app/public ./public
COPY --from=base /app/.next/standalone ./
COPY --from=base /app/.next/static ./.next/static

EXPOSE 3000

ENV HOSTNAME=0.0.0.0
ENV PORT=3000
ENV NODE_ENV=production

CMD ["node", "server.js"]
