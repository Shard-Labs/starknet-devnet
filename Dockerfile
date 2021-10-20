FROM python:3.7.11-slim
RUN apt-get update && apt-get install gcc libgmp3-dev -y
COPY pyproject.toml pyproject.toml
COPY poetry.lock poetry.lock
COPY starknet_devnet starknet_devnet
COPY README.md README.md
RUN pip install poetry \
 && poetry -V \
 && poetry check \
 && poetry config virtualenvs.create false \
 && poetry install --no-dev
CMD ["poetry", "run", "starknet-devnet", "--host", "0.0.0.0", "--port", "5000"]
