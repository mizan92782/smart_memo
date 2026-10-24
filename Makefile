# ═══════════════════════════════════════════════════════════════════════════════
#  IKON Backend — Makefile
#  Usage: make <command>
#
#  Run `make` or `make help` to see all available commands.
# ═══════════════════════════════════════════════════════════════════════════════

# ── Config ────────────────────────────────────────────────────────────────────
DEV_COMPOSE  := docker compose -f docker-compose.dev.yml
PROD_COMPOSE := docker compose -f docker-compose.prod.yml

# App container names
DEV_WEB      := ikon_api_dev
PROD_WEB     := ikon_web_prod

# Default Python inside container
PYTHON       := python manage.py

# Colors for terminal output
RESET  := \033[0m
BOLD   := \033[1m
GREEN  := \033[32m
CYAN   := \033[36m
YELLOW := \033[33m
RED    := \033[31m
GREY   := \033[90m

.DEFAULT_GOAL := help
.PHONY: help \
        dev-build dev-up dev-down dev-restart dev-stop dev-logs dev-logs-web \
        dev-logs-celery dev-shell dev-shell-db dev-ps dev-prune \
        prod-up prod-down prod-restart prod-stop prod-logs prod-logs-web \
        prod-logs-celery prod-shell prod-ps \
        migrate makemigrations collectstatic createsuperuser \
        shell dbshell check \
        seed flush \
        test lint format \
        pc-install pc-run pc-update pc-run-hook \
        monitoring-up monitoring-down monitoring-logs prometheus-reload \
        clean clean-all clean-images

# ═══════════════════════════════════════════════════════════════════════════════
#  HELP
# ═══════════════════════════════════════════════════════════════════════════════

help:
	@printf "\n$(BOLD)$(CYAN)  IKON Backend — Make Commands$(RESET)\n"
	@printf "$(GREY)  ─────────────────────────────────────────────────────────$(RESET)\n\n"
	@printf "$(BOLD)$(GREEN)  ── DEV ──────────────────────────────────────────────────$(RESET)\n"
	@printf "  $(CYAN)make dev-build$(RESET)         Build all dev images from Dockerfile\n"
	@printf "  $(CYAN)make dev-up$(RESET)            Start all dev services (attached)\n"
	@printf "  $(CYAN)make dev-upd$(RESET)           Start all dev services (detached / background)\n"
	@printf "  $(CYAN)make dev-down$(RESET)          Stop and remove dev containers\n"
	@printf "  $(CYAN)make dev-restart$(RESET)       Restart all dev services\n"
	@printf "  $(CYAN)make dev-stop$(RESET)          Stop dev services (keep containers)\n"
	@printf "  $(CYAN)make dev-logs$(RESET)          Follow all dev service logs\n"
	@printf "  $(CYAN)make dev-logs-web$(RESET)      Follow Django web logs only\n"
	@printf "  $(CYAN)make dev-logs-celery$(RESET)   Follow Celery worker logs only\n"
	@printf "  $(CYAN)make dev-ps$(RESET)            Show dev container status\n"
	@printf "  $(CYAN)make dev-shell$(RESET)         Bash shell inside dev web container\n"
	@printf "  $(CYAN)make dev-shell-db$(RESET)      psql shell inside dev postgres container\n"
	@printf "  $(CYAN)make dev-prune$(RESET)         Remove dev containers, volumes, and images\n\n"
	@printf "$(BOLD)$(GREEN)  ── PROD ─────────────────────────────────────────────────$(RESET)\n"
	@printf "  $(CYAN)make prod-up$(RESET)           Start all prod services (detached)\n"
	@printf "  $(CYAN)make prod-down$(RESET)         Stop and remove prod containers\n"
	@printf "  $(CYAN)make prod-restart$(RESET)      Restart all prod services\n"
	@printf "  $(CYAN)make prod-stop$(RESET)         Stop prod services (keep containers)\n"
	@printf "  $(CYAN)make prod-logs$(RESET)         Follow all prod service logs\n"
	@printf "  $(CYAN)make prod-logs-web$(RESET)     Follow prod Django web logs only\n"
	@printf "  $(CYAN)make prod-logs-celery$(RESET)  Follow prod Celery worker logs only\n"
	@printf "  $(CYAN)make prod-shell$(RESET)        Bash shell inside prod web container\n"
	@printf "  $(CYAN)make prod-ps$(RESET)           Show prod container status\n\n"
	@printf "$(BOLD)$(GREEN)  ── DJANGO MANAGEMENT ────────────────────────────────────$(RESET)\n"
	@printf "  $(CYAN)make migrate$(RESET)           Run database migrations (dev)\n"
	@printf "  $(CYAN)make makemigrations$(RESET)    Create new migrations (dev)\n"
	@printf "  $(CYAN)make collectstatic$(RESET)     Collect static files (dev)\n"
	@printf "  $(CYAN)make createsuperuser$(RESET)   Create Django superuser (dev)\n"
	@printf "  $(CYAN)make shell$(RESET)             Django interactive shell (dev)\n"
	@printf "  $(CYAN)make dbshell$(RESET)           Django DB shell (dev)\n"
	@printf "  $(CYAN)make check$(RESET)             Run Django system check (dev)\n\n"
	@printf "$(BOLD)$(GREEN)  ── DATA ─────────────────────────────────────────────────$(RESET)\n"
	@printf "  $(CYAN)make seed$(RESET)              Run all seed scripts (dev)\n"
	@printf "  $(CYAN)make flush$(RESET)             Flush database ($(RED)DELETES ALL DATA$(RESET)) (dev)\n\n"
	@printf "$(BOLD)$(GREEN)  ── MONITORING ───────────────────────────────────────────$(RESET)\n"
	@printf "  $(CYAN)make monitoring-up$(RESET)     Start monitoring stack only (dev)\n"
	@printf "  $(CYAN)make monitoring-down$(RESET)   Stop monitoring stack (dev)\n"
	@printf "  $(CYAN)make monitoring-logs$(RESET)   Follow monitoring service logs\n\n"
	@printf "$(BOLD)$(GREEN)  ── CODE QUALITY ─────────────────────────────────────$(RESET)\n"
	@printf "  $(CYAN)make test$(RESET)              Run all Django tests (dev)\n"
	@printf "  $(CYAN)make lint$(RESET)              Run ruff linter\n"
	@printf "  $(CYAN)make format$(RESET)            Run ruff formatter (auto-fix)\n\n"
	@printf "$(BOLD)$(GREEN)  ── PRE-COMMIT ───────────────────────────────────────$(RESET)\n"
	@printf "  $(CYAN)make pc-install$(RESET)        Install pre-commit hooks into git\n"
	@printf "  $(CYAN)make pc-run$(RESET)            Run all hooks on all files (manual check)\n"
	@printf "  $(CYAN)make pc-update$(RESET)         Update all hook versions to latest\n"
	@printf "  $(CYAN)make pc-run-hook hook=ruff$(RESET)  Run a single hook by id\n\n"
	@printf "$(BOLD)$(GREEN)  ── CLEANUP ──────────────────────────────────────────$(RESET)\n"
	@printf "  $(CYAN)make clean$(RESET)             Remove __pycache__ and .pyc files\n"
	@printf "  $(CYAN)make clean-all$(RESET)         clean + prune Docker system\n\n"


# ═══════════════════════════════════════════════════════════════════════════════
#  DEV COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════

## Build dev images
dev-build:
	@printf "$(BOLD)$(CYAN)▶ Building dev images...$(RESET)\n"
	$(DEV_COMPOSE) build

## Build dev images (no cache)
dev-build-nc:
	@printf "$(BOLD)$(CYAN)▶ Building dev images (no cache)...$(RESET)\n"
	$(DEV_COMPOSE) build --no-cache

## Start all dev services (attached — see logs in terminal)
dev-up:
	@printf "$(BOLD)$(GREEN)▶ Starting dev stack (attached)...$(RESET)\n"
	$(DEV_COMPOSE) up

## Start all dev services (detached — background)
dev-upd:
	@printf "$(BOLD)$(GREEN)▶ Starting dev stack (detached)...$(RESET)\n"
	$(DEV_COMPOSE) up -d
	@printf "$(GREEN)✅ Dev stack running. API → http://localhost:8001$(RESET)\n"
	@printf "$(GREEN)   Grafana  → http://localhost:3000$(RESET)\n"
	@printf "$(GREEN)   Prometheus → http://localhost:9090$(RESET)\n"

## Build and start (shortcut for first-time or after code changes)
dev-up-build:
	@printf "$(BOLD)$(CYAN)▶ Building + starting dev stack...$(RESET)\n"
	$(DEV_COMPOSE) up --build

dev-up-build-d:
	@printf "$(BOLD)$(CYAN)▶ Building + starting dev stack (detached)...$(RESET)\n"
	$(DEV_COMPOSE) up --build -d

## Stop and remove dev containers + networks
dev-down:
	@printf "$(BOLD)$(YELLOW)▶ Stopping dev stack...$(RESET)\n"
	$(DEV_COMPOSE) down

## Stop and remove dev containers + volumes (WARNING: deletes DB data)
dev-down-v:
	@printf "$(BOLD)$(RED)▶ Stopping dev stack and removing volumes...$(RESET)\n"
	@printf "$(RED)⚠️  This will delete all dev database data!$(RESET)\n"
	$(DEV_COMPOSE) down -v

## Restart all dev services
dev-restart:
	@printf "$(BOLD)$(CYAN)▶ Restarting dev stack...$(RESET)\n"
	$(DEV_COMPOSE) restart

## Restart only the web container (useful after code changes when not using volume mount)
dev-restart-web:
	@printf "$(BOLD)$(CYAN)▶ Restarting dev web container...$(RESET)\n"
	$(DEV_COMPOSE) restart web

## Stop dev services (keep containers)
dev-stop:
	@printf "$(BOLD)$(YELLOW)▶ Stopping dev services...$(RESET)\n"
	$(DEV_COMPOSE) stop

## Follow all dev service logs
dev-logs:
	$(DEV_COMPOSE) logs -f

## Follow Django web logs
dev-logs-web:
	$(DEV_COMPOSE) logs -f web

## Follow Celery worker logs
dev-logs-celery:
	$(DEV_COMPOSE) logs -f celery

## Follow Celery Beat logs
dev-logs-beat:
	$(DEV_COMPOSE) logs -f celery-beat

## Show dev container status
dev-ps:
	$(DEV_COMPOSE) ps

## Bash shell inside dev web container
dev-shell:
	@printf "$(BOLD)$(CYAN)▶ Opening shell in dev web container...$(RESET)\n"
	docker exec -it $(DEV_WEB) /bin/bash

## psql shell inside dev postgres container
dev-shell-db:
	@printf "$(BOLD)$(CYAN)▶ Opening psql in dev postgres container...$(RESET)\n"
	docker exec -it ikon_postgres_dev psql -U $${POSTGRES_USER:-ikon_user} -d $${POSTGRES_DB:-ikon_db}

## Redis CLI inside dev redis container
dev-shell-redis:
	@printf "$(BOLD)$(CYAN)▶ Opening redis-cli in dev redis container...$(RESET)\n"
	docker exec -it ikon_redis_dev redis-cli -a $${REDIS_PASSWORD:-redis_pass}

## Remove all dev containers, images, and volumes
dev-prune:
	@printf "$(BOLD)$(RED)▶ Pruning dev environment...$(RESET)\n"
	@printf "$(RED)⚠️  This will delete all containers, images, and volumes for dev!$(RESET)\n"
	$(DEV_COMPOSE) down -v --rmi local


# ═══════════════════════════════════════════════════════════════════════════════
#  PROD COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════

## Start all prod services (always detached in production)
prod-up:
	@printf "$(BOLD)$(GREEN)▶ Starting prod stack...$(RESET)\n"
	$(PROD_COMPOSE) up -d
	@printf "$(GREEN)✅ Prod stack running. API → :8005  Grafana → :3000$(RESET)\n"

## Pull latest images and restart prod
prod-deploy:
	@printf "$(BOLD)$(GREEN)▶ Deploying latest prod images...$(RESET)\n"
	$(PROD_COMPOSE) pull
	$(PROD_COMPOSE) up -d --remove-orphans
	@printf "$(GREEN)✅ Deployment complete$(RESET)\n"

## Stop and remove prod containers
prod-down:
	@printf "$(BOLD)$(YELLOW)▶ Stopping prod stack...$(RESET)\n"
	$(PROD_COMPOSE) down

## Restart all prod services
prod-restart:
	@printf "$(BOLD)$(CYAN)▶ Restarting prod stack...$(RESET)\n"
	$(PROD_COMPOSE) restart

## Restart only the prod web container (zero-downtime update)
prod-restart-web:
	@printf "$(BOLD)$(CYAN)▶ Restarting prod web container...$(RESET)\n"
	$(PROD_COMPOSE) restart web

## Stop prod services (keep containers)
prod-stop:
	@printf "$(BOLD)$(YELLOW)▶ Stopping prod services...$(RESET)\n"
	$(PROD_COMPOSE) stop

## Follow all prod service logs
prod-logs:
	$(PROD_COMPOSE) logs -f

## Follow prod Django web logs
prod-logs-web:
	$(PROD_COMPOSE) logs -f web

## Follow prod Celery worker logs
prod-logs-celery:
	$(PROD_COMPOSE) logs -f celery

## Show prod container status
prod-ps:
	$(PROD_COMPOSE) ps

## Bash shell inside prod web container
prod-shell:
	@printf "$(BOLD)$(CYAN)▶ Opening shell in prod web container...$(RESET)\n"
	docker exec -it $(PROD_WEB) /bin/bash


# ═══════════════════════════════════════════════════════════════════════════════
#  DJANGO MANAGEMENT (runs inside dev web container)
# ═══════════════════════════════════════════════════════════════════════════════

## Apply all pending migrations
migrate:
	@printf "$(BOLD)$(CYAN)▶ Running migrations...$(RESET)\n"
	docker exec -it $(DEV_WEB) $(PYTHON) migrate

## Create new migrations (optionally: make makemigrations app=authentication)
makemigrations:
	@printf "$(BOLD)$(CYAN)▶ Creating migrations...$(RESET)\n"
	docker exec -it $(DEV_WEB) $(PYTHON) makemigrations $(app)

## Collect static files
collectstatic:
	@printf "$(BOLD)$(CYAN)▶ Collecting static files...$(RESET)\n"
	docker exec -it $(DEV_WEB) $(PYTHON) collectstatic --noinput

## Create Django superuser interactively
createsuperuser:
	@printf "$(BOLD)$(CYAN)▶ Creating superuser...$(RESET)\n"
	docker exec -it $(DEV_WEB) $(PYTHON) createsuperuser

## Open Django interactive shell
shell:
	@printf "$(BOLD)$(CYAN)▶ Opening Django shell...$(RESET)\n"
	docker exec -it $(DEV_WEB) $(PYTHON) shell

## Open Django DB shell (dbshell)
dbshell:
	@printf "$(BOLD)$(CYAN)▶ Opening Django dbshell...$(RESET)\n"
	docker exec -it $(DEV_WEB) $(PYTHON) dbshell

## Run Django system check
check:
	@printf "$(BOLD)$(CYAN)▶ Running Django system check...$(RESET)\n"
	docker exec -it $(DEV_WEB) $(PYTHON) check

## Show all registered URL patterns
urls:
	@printf "$(BOLD)$(CYAN)▶ Showing URL patterns...$(RESET)\n"
	docker exec -it $(DEV_WEB) $(PYTHON) show_urls 2>/dev/null || \
	  echo "django-extensions not installed. Run: pip install django-extensions"


# ═══════════════════════════════════════════════════════════════════════════════
#  DATA — SEED & FLUSH
# ═══════════════════════════════════════════════════════════════════════════════

## Run all seed scripts (does NOT flush first)
seed:
	@printf "$(BOLD)$(CYAN)▶ Running seed scripts...$(RESET)\n"
	docker exec -it $(DEV_WEB) python scripts/seeds/seed_root.py

## Flush database (⚠️ DELETES ALL DATA) then re-seed
flush:
	@printf "$(BOLD)$(RED)⚠️  WARNING: This will DELETE ALL DATA in the dev database!$(RESET)\n"
	@printf "$(RED)   Continue? Press Ctrl+C to cancel, Enter to proceed.$(RESET)\n"
	@read _
	docker exec -it $(DEV_WEB) $(PYTHON) flush --noinput
	@printf "$(GREEN)✅ Database flushed. Run 'make seed' to re-seed.$(RESET)\n"

## Flush + migrate + seed (full reset)
reset-db: flush migrate seed
	@printf "$(GREEN)✅ Database fully reset and re-seeded.$(RESET)\n"


# ═══════════════════════════════════════════════════════════════════════════════
#  MONITORING ONLY (spin up just the observability stack)
# ═══════════════════════════════════════════════════════════════════════════════

## Start only monitoring services (prometheus, loki, grafana, promtail, alertmanager)
monitoring-up:
	@printf "$(BOLD)$(CYAN)▶ Starting monitoring stack...$(RESET)\n"
	$(DEV_COMPOSE) up -d prometheus loki promtail alertmanager grafana
	@printf "$(GREEN)✅ Monitoring running:$(RESET)\n"
	@printf "$(GREEN)   Grafana    → http://localhost:3000  (admin / admin)$(RESET)\n"
	@printf "$(GREEN)   Prometheus → http://localhost:9090$(RESET)\n"
	@printf "$(GREEN)   Loki       → http://localhost:3100$(RESET)\n"
	@printf "$(GREEN)   Alertmgr   → http://localhost:9093$(RESET)\n"

## Stop only monitoring services
monitoring-down:
	@printf "$(BOLD)$(YELLOW)▶ Stopping monitoring stack...$(RESET)\n"
	$(DEV_COMPOSE) stop prometheus loki promtail alertmanager grafana

## Follow monitoring service logs
monitoring-logs:
	$(DEV_COMPOSE) logs -f prometheus loki promtail alertmanager grafana

## Reload Prometheus config without restart
prometheus-reload:
	@printf "$(BOLD)$(CYAN)▶ Reloading Prometheus config...$(RESET)\n"
	curl -s -X POST http://localhost:9090/-/reload && \
	  printf "$(GREEN)✅ Prometheus config reloaded$(RESET)\n" || \
	  printf "$(RED)❌ Failed — is Prometheus running?$(RESET)\n"


# ═══════════════════════════════════════════════════════════════════════════════
#  CODE QUALITY
# ═══════════════════════════════════════════════════════════════════════════════

## Run all Django tests
test:
	@printf "$(BOLD)$(CYAN)▶ Running tests...$(RESET)\n"
	docker exec -it $(DEV_WEB) $(PYTHON) test --verbosity=2 $(app)

## Run ruff linter (check only)
lint:
	@printf "$(BOLD)$(CYAN)▶ Running ruff linter...$(RESET)\n"
	docker exec -it $(DEV_WEB) ruff check . 2>/dev/null || \
	  ruff check . 2>/dev/null || \
	  echo "ruff not installed. Run: pip install ruff"

## Run ruff formatter + auto-fix
format:
	@printf "$(BOLD)$(CYAN)▶ Running ruff formatter...$(RESET)\n"
	docker exec -it $(DEV_WEB) ruff format . 2>/dev/null || \
	  ruff format . 2>/dev/null || \
	  echo "ruff not installed. Run: pip install ruff"


# ═══════════════════════════════════════════════════════════════════════════════
#  CLEANUP
# ═══════════════════════════════════════════════════════════════════════════════

## Remove all Python __pycache__ and .pyc files
clean:
	@printf "$(BOLD)$(CYAN)▶ Cleaning Python cache files...$(RESET)\n"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "*.pyo" -delete 2>/dev/null || true
	@printf "$(GREEN)✅ Python cache cleaned$(RESET)\n"

## Remove Python cache + prune unused Docker resources (images, containers, volumes)
clean-all: clean
	@printf "$(BOLD)$(RED)▶ Pruning unused Docker resources...$(RESET)\n"
	docker system prune -f
	@printf "$(GREEN)✅ Docker system pruned$(RESET)\n"

## Remove dangling Docker images only
clean-images:
	@printf "$(BOLD)$(CYAN)▶ Removing dangling Docker images...$(RESET)\n"
	docker image prune -f


# ═══════════════════════════════════════════════════════════════════════════════
#  PRE-COMMIT
# ═══════════════════════════════════════════════════════════════════════════════

## Install pre-commit hooks into git (run once per clone)
pc-install:
	@printf "$(BOLD)$(CYAN)▶ Installing pre-commit hooks...$(RESET)\n"
	pip install pre-commit --quiet
	pre-commit install
	pre-commit install --hook-type commit-msg
	@printf "$(GREEN)✅ pre-commit hooks installed (pre-commit + commit-msg)$(RESET)\n"

## Run all pre-commit hooks on every file (manual full check)
pc-run:
	@printf "$(BOLD)$(CYAN)▶ Running all pre-commit hooks on all files...$(RESET)\n"
	pre-commit run --all-files

## Run a single hook by id:  make pc-run-hook hook=ruff
pc-run-hook:
	@printf "$(BOLD)$(CYAN)▶ Running hook: $(hook)...$(RESET)\n"
	pre-commit run $(hook) --all-files

## Update all hooks to their latest versions
pc-update:
	@printf "$(BOLD)$(CYAN)▶ Updating pre-commit hooks to latest versions...$(RESET)\n"
	pre-commit autoupdate
	@printf "$(GREEN)✅ Hook versions updated. Review .pre-commit-config.yaml and commit.$(RESET)\n"

## Generate a fresh detect-secrets baseline
pc-secrets-scan:
	@printf "$(BOLD)$(CYAN)▶ Scanning for secrets and updating baseline...$(RESET)\n"
	pip install detect-secrets --quiet
	detect-secrets scan --baseline .secrets.baseline
	@printf "$(GREEN)✅ .secrets.baseline updated. Review and commit it.$(RESET)\n"

## Uninstall pre-commit hooks from git
pc-uninstall:
	@printf "$(BOLD)$(YELLOW)▶ Uninstalling pre-commit hooks...$(RESET)\n"
	pre-commit uninstall
	pre-commit uninstall --hook-type commit-msg
	@printf "$(YELLOW)⚠️  Hooks uninstalled. Code quality checks will no longer run on commit.$(RESET)\n"
