# ClinicFlow frontend - multi-stage: Node builds the static bundle, nginx serves it.

# ---- stage 1: build ------------------------------------------------------------
FROM node:22-alpine AS build
WORKDIR /src
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY index.html vite.config.js ./
COPY public/ public/
COPY src/ src/
RUN npm run build

# ---- stage 2: runtime (no Node, no npm, no source - only the static files) ------
FROM nginxinc/nginx-unprivileged:1.31-alpine
# Needs root briefly:
#  - drop the dynamic nginx modules this app never loads. image-filter pulls in libgd -> libtiff,
#    which carried CVE-2026-4775 (HIGH) and failed the Trivy gate on the first build.
#  - apk upgrade picks up Alpine security fixes published after the base image was built.
USER root
RUN apk del --no-cache nginx-module-image-filter nginx-module-xslt nginx-module-geoip nginx-module-njs \
 && apk upgrade --no-cache
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /src/dist /usr/share/nginx/html
ENV BACKEND_URL=http://backend:8000
# The unprivileged image runs as UID 101 and listens on 8080 - no root at runtime.
USER 101
EXPOSE 8080
