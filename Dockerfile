# syntax=docker/dockerfile:1
FROM python:3.13.15-slim-trixie@sha256:7c61056e61ac89e852de05f3dc6fa51a6dd2181797bceed46aa725dd7cb2cd3b

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
