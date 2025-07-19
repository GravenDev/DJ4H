FROM python:3.10-slim

# Update the system
RUN apt update && apt upgrade -y

# Install the required packages
RUN apt install -y --no-install-recommends gcc libmariadb-dev libmariadb3 && apt clean

# Install poetry
RUN pip install poetry==2.1.3

WORKDIR /app

COPY ./ /app

# Disable in-project venvs
RUN poetry config virtualenvs.in-project false

RUN poetry install --without dev

RUN chmod +x entrypoint.sh

# Run the application
CMD ["/app/entrypoint.sh"]
