# Build from repository root: docker build -f frontend/Dockerfile .
FROM node:20-alpine AS build
WORKDIR /app/frontend

COPY application.properties /application.properties
ENV APPLICATION_PROPERTIES=/application.properties

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

COPY frontend/ .
RUN npm run build

FROM nginx:1.27-alpine
ENV BACKEND_PORT=8000
COPY frontend/nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/frontend/dist /usr/share/nginx/html
EXPOSE 80
