PROFILE ?= local
SVC     ?=

# ── Compose file selection ────────────────────────────────────────
ifeq ($(PROFILE),local)
  COMPOSE_FILES = -f deploy/docker-compose.yml -f deploy/docker-compose.local.yml
  BUILD_ARGS    = --build-arg BASE_REGISTRY=docker.io/library \
                  --build-arg PIP_INDEX_URL=https://pypi.org/simple \
                  --build-arg TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
else ifeq ($(PROFILE),enterprise)
  COMPOSE_FILES = -f deploy/docker-compose.yml
  BUILD_ARGS    = --build-arg BASE_REGISTRY=<ARTIFACTORY_DOCKER_REGISTRY_PLACEHOLDER> \
                  --build-arg PIP_INDEX_URL=<ARTIFACTORY_PYPI_URL_PLACEHOLDER> \
                  --build-arg TORCH_INDEX_URL=<ARTIFACTORY_TORCH_CPU_URL_PLACEHOLDER>
else
  $(error Unknown PROFILE '$(PROFILE)'. Use: local (default) or enterprise)
endif

DC = docker compose $(COMPOSE_FILES)

.DEFAULT_GOAL := help

# ── First-time setup ──────────────────────────────────────────────
.PHONY: setup
setup:	## One-time setup: network, data dirs, env file (safe to re-run)
	docker network create observability 2>/dev/null || true
	mkdir -p data/postgres data/qdrant data/redis data/models \
	         data/llm-guard-models data/retrieval/tmp
	@if [ ! -f config/env/.env ]; then \
	  cp config/env/env.template config/env/.env; \
	  echo ""; \
	  echo "  Created config/env/.env — edit POSTGRES_PASSWORD, JWT_SECRET,"; \
	  echo "  TOOL_SECRETS_KEY before running 'make up'."; \
	  echo ""; \
	fi

# ── Build ─────────────────────────────────────────────────────────
.PHONY: build
build:	## Build images (PROFILE=local|enterprise)
	DOCKER_BUILDKIT=0 $(DC) build $(BUILD_ARGS)

.PHONY: build-offline
build-offline:	## Build from local src/wheelhouse — no network required
	DOCKER_BUILDKIT=0 $(DC) build --build-arg OFFLINE=1

# ── Start / stop ──────────────────────────────────────────────────
.PHONY: up
up:	## Start services in the background (backend-core; no llm-guard/UI)
	$(DC) up -d

.PHONY: up-full
up-full:	## Start the FULL stack incl. llm-guard-svc + ui-webapp (--profile full)
	docker compose --env-file config/env/.env $(COMPOSE_FILES) -f deploy/docker-compose.full.yml --profile full up -d

.PHONY: down
down:	## Stop and remove containers
	$(DC) down

.PHONY: down-full
down-full:	## Stop the FULL stack (incl. llm-guard-svc + ui-webapp)
	docker compose --env-file config/env/.env $(COMPOSE_FILES) -f deploy/docker-compose.full.yml --profile full down

.PHONY: restart
restart: down up	## Full stop + start

# ── Observability ─────────────────────────────────────────────────
.PHONY: logs
logs:	## Tail logs — all services, or SVC=<name> for one (e.g. make logs SVC=orchestrator-api)
	$(DC) logs -f $(SVC)

.PHONY: status
status:	## Show running containers and their ports
	$(DC) ps

.PHONY: shell
shell:	## Open a shell in a running container (SVC=<name> required)
	$(DC) exec $(SVC) /bin/bash || $(DC) exec $(SVC) /bin/sh

# ── Models ────────────────────────────────────────────────────────
.PHONY: models
models:	## Download all models into data/ (local profile only)
	python ops/bootstrap/download_embedding_models.py
	python ops/bootstrap/download_llm_guard_models.py --output-dir data/llm-guard-models

.PHONY: models-embedding
models-embedding:	## Download embedding model only
	python ops/bootstrap/download_embedding_models.py

.PHONY: models-llm-guard
models-llm-guard:	## Download llm-guard ONNX models only
	python ops/bootstrap/download_llm_guard_models.py --output-dir data/llm-guard-models

# ── Database ──────────────────────────────────────────────────────
.PHONY: db-reset
db-reset:	## Wipe and reinitialise the database (destroys all data)
	$(DC) rm -sf postgres-db db-init
	rm -rf data/postgres
	$(DC) up -d postgres-db db-init

# ── Cleanup ───────────────────────────────────────────────────────
.PHONY: clean
clean:	## Remove containers and named volumes (keeps data/ directory)
	$(DC) down -v

# ── Help ──────────────────────────────────────────────────────────
.PHONY: help
help:	## Show available targets
	@echo ""
	@echo "Usage: make <target> [PROFILE=local|enterprise] [SVC=<service-name>]"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*##"}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
