# syntax=docker/dockerfile:1
FROM python:3.13.15-slim-trixie@sha256:9d2e5553305c7c7b0097999bb17187c69b921ccd6bc9d40e4bb5ebe652c00285

ARG TARGETPLATFORM

# Install poetry
RUN pip install --no-cache-dir poetry==2.2.1

WORKDIR /app

# Install the dependencies first, so this layer is only rebuilt when the lockfile changes
COPY pyproject.toml poetry.lock poetry.toml /app/

RUN --mount=type=cache,target=/root/.cache/pypoetry,id=poetry-${TARGETPLATFORM},sharing=locked \
    poetry install --without dev

COPY ./ /app

RUN sed -i 's/\r$//' entrypoint.sh && chmod +x entrypoint.sh

# Run the application
CMD ["/app/entrypoint.sh"]
