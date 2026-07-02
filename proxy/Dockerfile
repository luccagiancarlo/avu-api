FROM nginx:1.27-alpine

# Adiciona curl para o HEALTHCHECK.
RUN apk add --no-cache curl

# Remove config default e coloca a nossa.
RUN rm /etc/nginx/nginx.conf /etc/nginx/conf.d/default.conf 2>/dev/null || true
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
