FROM python:3.12-slim

ENV PYTHONUNBUFFERED 1

WORKDIR /attendance-bot

COPY . .

RUN pip install -e "src/[dev]"

CMD ["sleep", "infinity"]