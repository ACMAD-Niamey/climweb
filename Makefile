DC = docker compose
MANAGE = $(DC) exec climweb_dev python /climweb/web/src/climweb/manage.py

.PHONY: build up down logs migrate makemigrations createsuperuser collectstatic shell test restart

build:
	$(DC) build

up:
	$(DC) up -d

down:
	$(DC) down

logs:
	$(DC) logs -f

migrate:
	$(MANAGE) migrate

makemigrations:
	$(MANAGE) makemigrations

createsuperuser:
	$(MANAGE) createsuperuser

collectstatic:
	$(MANAGE) collectstatic --noinput

shell:
	$(MANAGE) shell

test:
	$(MANAGE) test --verbosity=2

restart:
	$(DC) down && $(DC) up -d
