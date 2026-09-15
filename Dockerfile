FROM python:3.14-slim

# Update the system
RUN apt update && apt upgrade -y

# Install the required packages
RUN apt install -y --no-install-recommends gcc && apt clean

# Install poetry
RUN pip install poetry==2.2.1

WORKDIR /app

COPY ./ /app

RUN sed -i 's/\r$//' entrypoint.sh

# Disable in-project venvs
RUN poetry config virtualenvs.in-project false

RUN poetry install --without dev

RUN chmod +x entrypoint.sh

# Run the application
CMD ["/app/entrypoint.sh"]
