FROM node:20-alpine AS build

WORKDIR /app

# Build args for Vite env vars (baked at build time)
ARG VITE_API_URL=http://localhost:8000
ARG VITE_FRAME_EXTRACTOR_URL=http://localhost:8100/api/v1

ENV VITE_API_URL=$VITE_API_URL
ENV VITE_FRAME_EXTRACTOR_URL=$VITE_FRAME_EXTRACTOR_URL

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# Serve with nginx
FROM nginx:stable-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
