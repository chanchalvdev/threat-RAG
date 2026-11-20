# ---------- build stage ----------
FROM node:22-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci --frozen-lockfile

COPY . .
RUN npm run build


# ---------- runtime stage (nginx) ----------
FROM nginx:1.27-alpine AS runtime

COPY --from=builder /app/dist /usr/share/nginx/html
# Rendered to /etc/nginx/conf.d/default.conf at start-up with BACKEND_URL substituted
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
ENV BACKEND_URL=http://backend:8000
ENV API_KEY=""

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
