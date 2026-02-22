# CONFIG
COMPOSE = docker compose
PROJECT_NAME = secure-monitoring-system

# DOCKER BASIC
docker-build:
	$(COMPOSE) build

docker-start:
	$(COMPOSE) up

docker-start-d:
	$(COMPOSE) up -d

docker-rebuild:
	$(COMPOSE) down --remove-orphans
	$(COMPOSE) build --no-cache
	$(COMPOSE) up

docker-stop:
	$(COMPOSE) down

docker-clean:
	$(COMPOSE) down -v --remove-orphans

docker-logs:
	$(COMPOSE) logs -f

docker-logs-backend:
	$(COMPOSE) logs -f backend

docker-logs-db:
	$(COMPOSE) logs -f postgres

docker-restart:
	$(COMPOSE) restart

# DEV
dev:
	$(COMPOSE) up --build

dev-fast:
	$(COMPOSE) up


# DATABASE
db-reset:
	$(COMPOSE) down -v
	$(COMPOSE) up -d postgres

db-shell:
	$(COMPOSE) exec postgres psql -U postgres -d security_db

# SHELL ACCESS
backend-shell:
	$(COMPOSE) exec backend /bin/sh

# SYSTEM CLEANUP
system-prune:
	docker system prune -af

images:
	docker images

containers:
	docker ps -a
