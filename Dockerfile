FROM python:3.7.11-slim
RUN apt-get update && apt-get install gcc libgmp3-dev -y
WORKDIR /app
COPY . /app
RUN pip install poetry \
 && poetry -V \
 && poetry check \
 && poetry config virtualenvs.create false \
 && poetry install --no-dev
CMD ["poetry", "run", "starknet-devnet", "--host", "0.0.0.0", "--port", "5000"]
