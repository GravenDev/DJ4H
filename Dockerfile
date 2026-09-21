# syntax=docker/dockerfile:1
FROM python:3.14.6-slim-trixie@sha256:7bec7ddcddeff7975d6ba9b4be7dd6f6b2f55e7491539145e2978f7f97ce9144

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
