FROM node:22-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/index.html frontend/tsconfig*.json frontend/vite.config.ts ./
COPY frontend/public/ public/
COPY frontend/src/ src/
RUN npm run build

FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev libpq-dev && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt 'waitress==3.0.2'
COPY backend/__init__.py backend/config.py backend/
COPY backend/app/ backend/app/
COPY backend/migrations/ backend/migrations/
COPY local_demo/start.py local_demo/seed.py local_demo/
COPY --from=frontend /build/dist public/
CMD ["python", "-m", "local_demo.start"]
