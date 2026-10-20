FROM node:22-alpine AS frontend
WORKDIR /build
COPY package*.json ./
RUN npm ci --no-audit --no-fund
COPY index.html tsconfig.json vite.config.ts postcss.config.js tailwind.config.js ./
COPY src ./src
COPY public ./public
RUN npm run build

FROM python:3.13-slim
WORKDIR /site/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./
COPY --from=frontend /build/dist /site/dist
COPY public/images /site/public/images
RUN useradd --create-home cinema && chown -R cinema:cinema /site
USER cinema
EXPOSE 8000
CMD ["python", "-m", "app.start"]
