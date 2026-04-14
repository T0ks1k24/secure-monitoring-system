FROM node:20-alpine AS build

WORKDIR /app

ARG VITE_API_URL=http://localhost:8000
ARG VITE_FRAME_API_URL=http://localhost:8100
ARG VITE_MEDIA_MTX_HLS_URL=http://localhost:8888
ARG VITE_MEDIA_MTX_WEBRTC_URL=http://localhost:8889
ARG VITE_WS_EVENTS_URL=

ENV VITE_API_URL=${VITE_API_URL}
ENV VITE_FRAME_API_URL=${VITE_FRAME_API_URL}
ENV VITE_MEDIA_MTX_HLS_URL=${VITE_MEDIA_MTX_HLS_URL}
ENV VITE_MEDIA_MTX_WEBRTC_URL=${VITE_MEDIA_MTX_WEBRTC_URL}
ENV VITE_WS_EVENTS_URL=${VITE_WS_EVENTS_URL}

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# Use nginx for serving the static files
FROM nginx:stable-alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
