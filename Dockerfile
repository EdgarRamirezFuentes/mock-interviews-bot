FROM python:3.9-alpine3.13
LABEL key="Discord Mock Interviews Bot Environment"

ENV PYTHONUNBUFFERED 1

COPY ./requirements.txt /tmp/requirements.txt
WORKDIR /bot

COPY ./bot /bot

RUN python -m venv /py && \
    /py/bin/pip install --upgrade pip && \
    /py/bin/pip install -r /tmp/requirements.txt && \
    rm -rf /tmp/ && \
    adduser \
    --disabled-password \
    mock-interviews-bot-user && \
    chown -R mock-interviews-bot-user /bot

ENV PATH="/py/bin:$PATH"
USER mock-interviews-bot-user



