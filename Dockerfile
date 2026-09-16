# syntax=docker/dockerfile:1
FROM python:3.14.7-slim-trixie@sha256:cad9a2c871761c413caa6fdd6441c783451e740a48aaeba60ae62a8b53525ef6

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
