up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

shell:
	docker compose exec bot bash

lint:
	ruff check .

format:
	black .

test:
	pytest
