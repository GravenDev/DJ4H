#!/bin/sh
poetry run alembic upgrade head
poetry run python main.py