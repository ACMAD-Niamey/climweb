DC = docker compose
MANAGE = $(DC) exec climweb_dev python /climweb/web/src/climweb/manage.py

# Disposable Postgis container used only for `make test`, so the suite never
# touches (or depends on) the persistent dev DB volume/credentials.
TEST_DB_CONTAINER = climweb_test_db
TEST_DB_NETWORK = climweb_default

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
	@docker network inspect $(TEST_DB_NETWORK) >/dev/null 2>&1 || docker network create $(TEST_DB_NETWORK)
	@docker rm -f $(TEST_DB_CONTAINER) >/dev/null 2>&1 || true
	docker run -d --name $(TEST_DB_CONTAINER) --network $(TEST_DB_NETWORK) \
		-e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=testpass -e POSTGRES_DB=test_db \
		postgis/postgis:15-master >/dev/null
	@# postgres logs "ready to accept connections" once for its temporary
	@# init-only instance, then again after it restarts as the real listener.
	@# Waiting for pg_isready alone races the restart; wait for the 2nd line.
	@until [ "$$(docker logs $(TEST_DB_CONTAINER) 2>&1 | grep -c 'ready to accept connections')" -ge 2 ]; do sleep 1; done
	@status=0; \
	$(DC) run --rm \
		-e DATABASE_URL=postgis://postgres:testpass@$(TEST_DB_CONTAINER):5432/test_db \
		climweb_dev manage test --settings=climweb.config.settings.test --verbosity=2 || status=$$?; \
	docker rm -f $(TEST_DB_CONTAINER) >/dev/null 2>&1; \
	exit $$status

restart:
	$(DC) down && $(DC) up -d
