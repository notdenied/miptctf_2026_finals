# Stage 1: Build Frontend
FROM node:20-alpine AS build
WORKDIR /app
COPY zbank-frontend/package.json zbank-frontend/package-lock.json* ./
RUN npm install
COPY zbank-frontend/ ./
RUN npm run build

# Stage 2: Serve with lighttpd
FROM jitesoft/lighttpd:1.4.80

COPY lighttpd/lighttpd.conf /etc/lighttpd/lighttpd.conf
COPY --from=build /app/dist /var/www/html

EXPOSE 8080
