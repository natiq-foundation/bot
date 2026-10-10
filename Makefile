up:
	docker compose up --build

kill:
	docker compose down -v

down:
	docker compose down

logs:
	docker compose logs -f

shell:
	docker compose exec bot bash

lint:
	ruff check .

lint-fix:
	ruff check . --fix

format:
	black .

format-check:
	black --check .

test:
	pytest
