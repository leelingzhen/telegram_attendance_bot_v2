FROM python:3.12-slim AS builder

WORKDIR /attendance-bot

COPY src/ .

RUN pip install .

FROM python:3.12-slim

WORKDIR /attendance-bot

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/attendance-bot /usr/local/bin/

ENTRYPOINT ["attendance-bot"]