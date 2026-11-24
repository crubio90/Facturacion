.PHONY: setup up dev down logs ps test-backend test-scraper build-frontend

setup:
	bash scripts/setup-local.sh

up:
	docker compose up --build -d

dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

down:
	docker compose down

logs:
	docker compose logs -f

ps:
	docker compose ps

test-backend:
	cd backend && pytest tests -v

test-scraper:
	cd scraper && pytest tests -v

build-frontend:
	cd frontend && npm run build
