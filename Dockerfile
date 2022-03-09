FROM python:3.7.12-alpine3.15 as builder

COPY . .

RUN apk add gmp-dev g++ gcc libffi-dev

RUN pip3 install poetry

RUN poetry export -f requirements.txt --without-hashes > requirements.txt

RUN pip3 wheel --no-cache-dir --no-deps --wheel-dir /wheels -r requirements.txt starknet-devnet


FROM python:3.7.12-alpine3.15

RUN apk add --no-cache libgmpxx 

COPY --from=builder /wheels /wheels

RUN pip install --no-cache /wheels/*

RUN rm -rf /wheels

ENTRYPOINT [ "starknet-devnet", "--host", "0.0.0.0", "--port", "5000" ]
