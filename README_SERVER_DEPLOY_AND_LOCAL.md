# Розгортання: Cloud-сервер + Local-машина

> Покроковий посібник із налаштування хмарного бекенду на сервері,  
> локального стеку на on-premise машині та їх з'єднання.

---

## Зміст

1. [Топологія системи](#1-топологія-системи)
2. [Вимоги](#2-вимоги)
3. [Крок 1 — Налаштування Cloud-сервера](#3-крок-1--налаштування-cloud-сервера)
4. [Крок 2 — Налаштування Local-машини](#4-крок-2--налаштування-local-машини)
5. [Крок 3 — Перевірка з'єднання](#5-крок-3--перевірка-зєднання)
6. [Таблиця портів і firewall](#6-таблиця-портів-і-firewall)
7. [Оновлення та перезапуск](#7-оновлення-та-перезапуск)
8. [Типові проблеми](#8-типові-проблеми)

---

## 1. Топологія системи

```
┌──────────────────────────────────────────────────────────────┐
│                  CLOUD-СЕРВЕР  (публічний IP)                │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐   │
│  │PostgreSQL│  │RabbitMQ  │  │ Backend  │  │AI Service │   │
│  │  :5432   │  │  :5672   │  │  :8000   │  │   :5000   │   │
│  └──────────┘  │  :15672  │  └──────────┘  └───────────┘   │
│                └──────────┘                                  │
│  ┌───────────────────────────────────────────┐               │
│  │ MediaMTX  :8554 (RTSP) · :8888 (HLS)     │               │
│  │           :8889 (WebRTC) · :1935 (RTMP)  │               │
│  └───────────────────────────────────────────┘               │
└─────────────────────────┬────────────────────────────────────┘
                          │  Internet / VPN
          ┌───────────────┴──────────────────┐
          │  HTTP :8000  WS :8000  HTTP :5000 │
          │                                  │
┌─────────┴────────────────────────────────────────────────────┐
│                  LOCAL-МАШИНА  (on-premise)                  │
│                                                              │
│  IP-камери──▶ MediaMTX :8554 ──▶ frame_extractor :8100      │
│                    │                    │                     │
│                    │ HLS/WebRTC         │ JPEG-кадри          │
│                    ▼                    ▼                     │
│             Frontend :80          AI Service (cloud)         │
│          (React + nginx)                                     │
└──────────────────────────────────────────────────────────────┘
```

**Короткий опис потоку:**

| Напрям | Протокол | Опис |
|---|---|---|
| IP-камера → local MediaMTX | RTSP | Відеопотік з камери |
| frame_extractor → AI Service | HTTP POST | JPEG-кадри на детекцію |
| AI Service → Backend (через RabbitMQ) | AMQP | Події безпеки |
| Backend → Frontend | WebSocket | Сповіщення в реальному часі |
| local MediaMTX → Frontend | HLS / WebRTC | Live-відео в браузері |

---

## 2. Вимоги

### Cloud-сервер

| Вимога | Мінімум | Рекомендовано |
|---|---|---|
| ОС | Ubuntu 20.04+ / Debian 11+ | Ubuntu 22.04 LTS |
| CPU | 2 ядра | 4 ядра |
| RAM | 4 ГБ | 8 ГБ (YOLO завантажує ~1.5 ГБ) |
| Диск | 20 ГБ | 50 ГБ SSD |
| Docker | ≥ 24.0 | latest |
| Docker Compose | ≥ 2.20 | latest |
| Публічний IP | обов'язково | статичний IP або домен |

### Local-машина

| Вимога | Мінімум |
|---|---|
| ОС | Ubuntu 20.04+ / Windows 10+ / macOS 12+ |
| RAM | 2 ГБ |
| Docker | ≥ 24.0 |
| Docker Compose | ≥ 2.20 |
| Відеофайли | `video/cam1.mp4`, `cam2.mp4`, `cam3.mp4` (або реальні IP-камери) |

### Встановлення Docker (якщо не встановлено)

```bash
# Ubuntu / Debian
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
docker --version            # Docker version 26.x.x
docker compose version      # Docker Compose version v2.x.x
```

---

## 3. Крок 1 — Налаштування Cloud-сервера

### 3.1 Клонування репозиторію

```bash
ssh user@<YOUR_SERVER_IP>

git clone https://github.com/T0ks1k24/secure-monitoring-system.git
cd secure-monitoring-system
```

### 3.2 Відеофайли для демо

Якщо використовуєте демо-відео (FFmpeg-публікатори), скопіюйте файли:

```bash
mkdir -p video
# Завантажте або скопіюйте тестові відеофайли:
# scp local_machine:/path/to/cam1.mp4 ./video/cam1.mp4
# scp local_machine:/path/to/cam2.mp4 ./video/cam2.mp4
# scp local_machine:/path/to/cam3.mp4 ./video/cam3.mp4
```

> **Без реальних камер:** якщо файли відсутні, camera_publisher-контейнери просто не запустяться,  
> але решта стеку працюватиме нормально.

### 3.3 Конфігурація `.env` на сервері

```bash
cp .env.example .env
nano .env          # або: vim .env
```

Встановіть ці значення (решту можна залишити за замовчуванням):

```dotenv
# ── Адреса сервера ────────────────────────────────────────────────
# Публічний IP або домен без http://
CLOUD_HOST=203.0.113.10          # ← замінити на ваш IP/домен

# ── PostgreSQL ────────────────────────────────────────────────────
POSTGRES_USER=postgres
POSTGRES_PASSWORD=S3cur3_P@ssw0rd   # ← змінити!
POSTGRES_DB=security_db

# ── RabbitMQ ──────────────────────────────────────────────────────
RABBITMQ_USER=admin
RABBITMQ_PASS=Rabbit_P@ss          # ← змінити!

# ── JWT ───────────────────────────────────────────────────────────
# Згенеруйте: openssl rand -hex 32
SECRET_KEY=<32-символьний-випадковий-рядок>

# ── CORS ──────────────────────────────────────────────────────────
# Дозволити всі джерела (для продакшну вкажіть точні URL):
ALLOWED_ORIGINS=*
```

> **Генерація SECRET_KEY:**
> ```bash
> openssl rand -hex 32
> ```

### 3.4 Запуск хмарного стеку

```bash
docker compose -f docker-compose.cloud.yml up -d --build
```

Спостерігайте за запуском (AI Service завантажує YOLO ~60 с):

```bash
docker compose -f docker-compose.cloud.yml logs -f
```

Перевірте статус — всі сервіси мають бути `healthy`:

```bash
docker compose -f docker-compose.cloud.yml ps
```

Очікуваний результат:

```
NAME                  STATUS
cloud_postgres        running (healthy)
cloud_rabbitmq        running (healthy)
cloud_mediamtx        running
cloud_backend         running (healthy)
cloud_ai_service      running (healthy)
cloud_camera_cam1     running
cloud_camera_cam2     running
cloud_camera_cam3     running
```

### 3.5 Перевірка API

```bash
# З сервера:
curl http://localhost:8000/health      # {"status":"ok"}
curl http://localhost:5000/api/v1/health  # {"status":"healthy",...}

# Або з будь-якої машини (замінити IP):
curl http://203.0.113.10:8000/health
curl http://203.0.113.10:5000/api/v1/health
```

### 3.6 Відкриття портів на сервері (Firewall)

```bash
# UFW (Ubuntu)
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 8000/tcp    # Backend API
sudo ufw allow 5000/tcp    # AI Service
sudo ufw allow 8554/tcp    # RTSP
sudo ufw allow 8888/tcp    # HLS
sudo ufw allow 8889/tcp    # WebRTC HTTP
sudo ufw allow 8189/udp    # WebRTC UDP
sudo ufw allow 15672/tcp   # RabbitMQ Management (опційно, тільки для адміна)
sudo ufw enable
sudo ufw status
```

> ⚠️ **Порт 5432 (PostgreSQL) і 5672 (RabbitMQ AMQP) НЕ відкривати** у публічний інтернет —  
> вони використовуються лише всередині Docker-мережі.

---

## 4. Крок 2 — Налаштування Local-машини

### 4.1 Клонування репозиторію

```bash
git clone https://github.com/T0ks1k24/secure-monitoring-system.git
cd secure-monitoring-system
```

### 4.2 Відеофайли (для демо без IP-камер)

```bash
mkdir -p video
cp /path/to/test.mp4 ./video/cam1.mp4
cp /path/to/test2.mp4 ./video/cam2.mp4
cp /path/to/test3.mp4 ./video/cam3.mp4
```

### 4.3 Конфігурація `.env` на локальній машині

```bash
cp .env.example .env
nano .env
```

> **Важливо:** замінити `203.0.113.10` на реальний IP вашого cloud-сервера.

```dotenv
# ── Адреса хмарного сервера ───────────────────────────────────────
CLOUD_HOST=203.0.113.10          # ← IP або домен cloud-сервера

# ── URL для frame_extractor → cloud AI ───────────────────────────
AI_SERVICE_URL=http://203.0.113.10:5000/api/v1/detect

# ── URL для frontend → cloud Backend ─────────────────────────────
VITE_API_URL=http://203.0.113.10:8000

# ── WebSocket для real-time подій ─────────────────────────────────
VITE_WS_EVENTS_URL=ws://203.0.113.10:8000/ws/events

# ── HLS/WebRTC — локальний MediaMTX ──────────────────────────────
# (відео стрімиться локально, тому залишається localhost)
VITE_MEDIA_MTX_HLS_URL=http://localhost:8888
VITE_MEDIA_MTX_WEBRTC_URL=http://localhost:8889

# ── Frame Extractor (локальний) ───────────────────────────────────
VITE_FRAME_API_URL=http://localhost:8100
```

### 4.4 Запуск локального стеку

```bash
docker compose -f docker-compose.local.yml up -d --build
```

Слідкуйте за логами:

```bash
docker compose -f docker-compose.local.yml logs -f
```

Перевірте статус:

```bash
docker compose -f docker-compose.local.yml ps
```

Очікуваний результат:

```
NAME                       STATUS
local_mediamtx             running
local_camera_cam1          running
local_camera_cam2          running
local_camera_cam3          running
local_frame_extractor      running (healthy)
local_frontend             running
```

### 4.5 Перевірка локальних сервісів

```bash
# Frame Extractor healthcheck
curl http://localhost:8100/api/v1/health
# {"status":"healthy","cameras":0}

# Frontend (nginx)
curl -I http://localhost:80
# HTTP/1.1 200 OK
```

### 4.6 Відкриття браузера

Відкрийте **http://localhost** або **http://localhost:3000**

Увійдіть з обліковими даними за замовчуванням:

| Поле | Значення |
|---|---|
| Логін | `admin` |
| Пароль | `admin` |

> ⚠️ Змініть пароль адміна після першого входу: **Settings → Users → admin → Change Password**

---

## 5. Крок 3 — Перевірка з'єднання

### 5.1 Перевірка мережевої доступності

Виконайте з **local-машини**:

```bash
# Backend API
curl http://203.0.113.10:8000/health
# Очікувано: {"status":"ok"}

# AI Service
curl http://203.0.113.10:5000/api/v1/health
# Очікувано: {"status":"healthy","model_loaded":true,...}

# WebSocket (якщо є wscat: npm i -g wscat)
wscat -c ws://203.0.113.10:8000/ws/events
# Очікувано: з'єднання відкрито (після авторизації через JWT)
```

### 5.2 Додавання першої камери

1. Відкрийте **http://localhost** у браузері на local-машині
2. Увійдіть: `admin` / `admin`
3. Перейдіть до **Settings → Camera Settings**
4. Натисніть **+ Add Camera**
5. Заповніть форму:
   - **Name:** `Camera 1`
   - **RTSP URL:** `rtsp://localhost:8554/camera1`
   - **FPS:** `2`
6. Натисніть **Save**

Через декілька секунд на сторінці **Monitoring** мають з'явитися:
- ✅ Live-відео (WebRTC або HLS)
- ✅ Детекції об'єктів (bounding boxes)
- ✅ Події у правій панелі

### 5.3 Перевірка потоку подій

```bash
# На cloud-сервері — перевірити що backend отримує події від AI:
docker compose -f docker-compose.cloud.yml logs -f backend | grep -i event

# На local-машині — перевірити що frame_extractor відправляє кадри:
docker compose -f docker-compose.local.yml logs -f local_frame_extractor
```

### 5.4 RabbitMQ Management UI

Відкрийте **http://203.0.113.10:15672** (cloud-сервер):

- **Login:** `admin` / `<RABBITMQ_PASS>`
- Перейдіть до **Queues** — має бути черга `backend.events`
- Перейдіть до **Exchanges** — мають бути `security.events` і `security.zones`

---

## 6. Таблиця портів і Firewall

### Cloud-сервер: відкрити назовні

| Порт | Протокол | Сервіс | Хто підключається |
|---|---|---|---|
| `8000` | TCP | Backend API | local frontend, local frame_extractor |
| `5000` | TCP | AI Service | local frame_extractor |
| `8554` | TCP | MediaMTX RTSP | IP-камери, local frame_extractor |
| `8888` | TCP | MediaMTX HLS | local frontend (опційно) |
| `8889` | TCP | MediaMTX WebRTC | local frontend (опційно) |
| `8189` | UDP | MediaMTX WebRTC UDP | local frontend |
| `1935` | TCP | MediaMTX RTMP | IP-камери з RTMP-публікацією (опційно) |

### Cloud-сервер: тільки внутрішній доступ

| Порт | Сервіс | Причина |
|---|---|---|
| `5432` | PostgreSQL | Тільки між контейнерами |
| `5672` | RabbitMQ AMQP | Тільки між контейнерами |
| `15672` | RabbitMQ UI | Адмін-доступ (відкрити лише для конкретного IP) |

### Local-машина: порти лише в LAN

| Порт | Сервіс |
|---|---|
| `80` / `3000` | Frontend (nginx) |
| `8100` | Frame Extractor API |
| `8554` | Local MediaMTX RTSP |
| `8888` | Local MediaMTX HLS |
| `8889` | Local MediaMTX WebRTC |

---

## 7. Оновлення та перезапуск

### Оновлення коду (обидві машини)

```bash
git pull origin main

# Cloud:
docker compose -f docker-compose.cloud.yml up -d --build

# Local:
docker compose -f docker-compose.local.yml up -d --build
```

### Перебудова окремого сервісу

```bash
# Cloud: перебудувати тільки backend
docker compose -f docker-compose.cloud.yml up -d --build backend

# Cloud: перебудувати тільки AI service
docker compose -f docker-compose.cloud.yml up -d --build ai_service

# Local: перебудувати тільки frontend
docker compose -f docker-compose.local.yml up -d --build frontend
```

> ⚠️ **Frontend:** зміна `VITE_*` змінних вимагає `--build`, бо Vite запікає їх під час збірки образу.

### Перезапуск стеку без перебудови

```bash
docker compose -f docker-compose.cloud.yml restart
docker compose -f docker-compose.local.yml restart
```

### Зупинка

```bash
docker compose -f docker-compose.cloud.yml down
docker compose -f docker-compose.local.yml down
```

### Очищення даних (скидання БД)

```bash
# Cloud: видалити томи PostgreSQL і RabbitMQ
docker compose -f docker-compose.cloud.yml down -v
docker compose -f docker-compose.cloud.yml up -d --build
```

> ⚠️ Це видалить усі події, камери, зони та користувачів!

---

## 8. Типові проблеми

### ❌ `frame_extractor` не може достукатися до AI Service

**Симптом:**
```
ConnectionError: http://203.0.113.10:5000/api/v1/detect
```

**Причини та рішення:**
```bash
# 1. Перевірте AI Service на cloud-сервері
curl http://203.0.113.10:5000/api/v1/health

# 2. Перевірте firewall на cloud-сервері
sudo ufw status | grep 5000

# 3. Перевірте .env на local-машині
cat .env | grep AI_SERVICE_URL
# Має бути: AI_SERVICE_URL=http://203.0.113.10:5000/api/v1/detect
# (не localhost!)

# 4. Перебудуйте local стек після зміни .env
docker compose -f docker-compose.local.yml up -d --build frame_extractor
```

---

### ❌ Frontend не показує відео (чорний екран)

**Причини та рішення:**
```bash
# 1. Перевірте чи запущений local MediaMTX
docker compose -f docker-compose.local.yml ps | grep mediamtx

# 2. Перевірте RTSP потік
ffplay rtsp://localhost:8554/camera1

# 3. Перевірте HLS доступність
curl http://localhost:8888/camera1/index.m3u8

# 4. Перевірте чи camera_publisher відправляє потік
docker compose -f docker-compose.local.yml logs local_camera_cam1
```

---

### ❌ WebSocket не підключається (немає live-подій)

**Симптом:** "Connecting..." у правому нижньому куті Frontend.

**Причини та рішення:**
```bash
# 1. Перевірте .env
cat .env | grep VITE_WS_EVENTS_URL
# Має бути: ws://203.0.113.10:8000/ws/events

# 2. Перевірте Backend на cloud-сервері
curl http://203.0.113.10:8000/health

# 3. Після зміни VITE_WS_EVENTS_URL — ОБОВ'ЯЗКОВО перебудувати
docker compose -f docker-compose.local.yml up -d --build frontend
```

---

### ❌ `ai_service` не стартує (OOMKilled або timeout)

**Причина:** YOLO-модель вимагає ~1.5 ГБ RAM.

**Рішення:**
```bash
# Перевірте доступну пам'ять
free -h

# Збільшіть start_period у docker-compose.cloud.yml:
# start_period: 120s  (за замовч. 90s)

# Перегляньте логи
docker compose -f docker-compose.cloud.yml logs ai_service
```

---

### ❌ PostgreSQL не запускається

```bash
# Перевірте логи
docker compose -f docker-compose.cloud.yml logs postgres

# Часта причина — невірний пароль або corrupt volume
# Скидання (УВАГА: втрата даних!):
docker compose -f docker-compose.cloud.yml down -v
docker compose -f docker-compose.cloud.yml up -d
```

---

### ❌ Frontend показує CORS-помилку

**Симптом:** `Access-Control-Allow-Origin` у браузері.

**Рішення:** Оновіть `ALLOWED_ORIGINS` у `.env` на cloud-сервері:

```dotenv
# Дозволити конкретні адреси (рекомендовано для продакшну):
ALLOWED_ORIGINS=http://192.168.1.50,http://192.168.1.51

# Або дозволити всі (для розробки):
ALLOWED_ORIGINS=*
```

```bash
docker compose -f docker-compose.cloud.yml up -d --build backend
```

---

### Корисні команди для діагностики

```bash
# Переглянути всі контейнери та їх статус
docker compose -f docker-compose.cloud.yml ps
docker compose -f docker-compose.local.yml ps

# Логи конкретного сервісу (остання 100 рядків)
docker compose -f docker-compose.cloud.yml logs --tail=100 backend
docker compose -f docker-compose.local.yml logs --tail=100 local_frame_extractor

# Увійти в контейнер для діагностики
docker exec -it cloud_backend bash
docker exec -it local_frame_extractor bash

# Перевірити з'єднання між контейнерами (з local_frame_extractor до cloud)
docker exec local_frame_extractor curl http://203.0.113.10:5000/api/v1/health

# Подивитися використання ресурсів
docker stats
```

---

## Контрольний список розгортання

### Cloud-сервер ✅

- [ ] Docker і Docker Compose встановлені
- [ ] Репозиторій клоновано
- [ ] Відеофайли у `./video/` (або пропустити для реальних камер)
- [ ] `.env` заповнений: `CLOUD_HOST`, `POSTGRES_PASSWORD`, `RABBITMQ_PASS`, `SECRET_KEY`
- [ ] `docker compose -f docker-compose.cloud.yml up -d --build` виконано
- [ ] `docker compose -f docker-compose.cloud.yml ps` показує усі `healthy`
- [ ] `curl http://localhost:8000/health` повертає `{"status":"ok"}`
- [ ] `curl http://localhost:5000/api/v1/health` повертає `{"status":"healthy"}`
- [ ] Порти відкриті: 8000, 5000, 8554, 8888, 8889, 8189/udp

### Local-машина ✅

- [ ] Docker і Docker Compose встановлені
- [ ] Репозиторій клоновано
- [ ] Відеофайли у `./video/` (або підключені реальні IP-камери)
- [ ] `.env` заповнений: `AI_SERVICE_URL`, `VITE_API_URL`, `VITE_WS_EVENTS_URL` з реальним IP сервера
- [ ] `docker compose -f docker-compose.local.yml up -d --build` виконано
- [ ] `docker compose -f docker-compose.local.yml ps` показує всі `running`
- [ ] `curl http://localhost:8100/api/v1/health` повертає `{"status":"healthy"}`
- [ ] `http://localhost` відкривається в браузері
- [ ] Вхід `admin`/`admin` успішний
- [ ] Камера додана, відео відображається, події надходять
