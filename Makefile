.PHONY: dev test build up down

dev:
	docker compose up --build

test:
	cd backend && pytest
	cd frontend && npm test

build:
	cd frontend && npm run build

up:
	docker compose up --build -d

down:
	docker compose down
