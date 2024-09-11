ifneq (,$(wildcard ./.envs/.local/.postgres))
	include .envs/.local/.postgres
	export
endif

build:
	docker compose -f docker-compose.dev.yml up --build -d --remove-orphans

up:
	docker compose -f docker-compose.dev.yml up -d
down:
	docker compose -f docker-compose.dev.yml down

show-logs:
	docker compose -f docker-compose.dev.yml logs -f
show-logs-cms-web:
	docker compose -f docker-compose.dev.yml logs -f cms_web
show-logs-cms-nginx:
	docker compose -f docker-compose.dev.yml logs -f cms_nginx
